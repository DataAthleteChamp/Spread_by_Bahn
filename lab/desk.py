"""Base dispatcher ("desk") for experiments.

This is the kit's starter (spread/starter.py) refactored into overridable hooks, so a new
algorithm is a small subclass. With default hooks it behaves exactly like the starter
(verified: level 8, seed spread-1 -> -72,612.51).

Hooks to override in a policy (see lab/policies/):
    price_quote(request)          -> dict option_kind -> cents   (what to quote)
    fee_schedule(order, cars, urgent) -> list[FeeStep]            (how to pay drivers)
    audience_for(order, legs, retry)  -> Audience
    on_event(event)               -> called for every event first (for learning)
    on_start()                    -> called once with self.ctx ready
"""
from __future__ import annotations

import re
from typing import Any, NamedTuple, Optional

from spread.client import World
from spread.types import (
    Action, ActionResult, Audience, DeskEvent, DeskEventKind, DeskSnapshot, FeeStep, Gig, Note, Order, PostAction,
    PriceRequest, StopRef, TimeWindow,
)

HOUR, DAY = 60, 24 * 60
DECLINE_MULT = 10  # a quote this many times the list price loses, and a losing quote costs nothing

# The events that need an answer. Others (views, ledger, bookings...) arrive with the next one.
WAKE_ON: list[DeskEventKind] = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed",
                                "gig_expired", "deadline_close"]


class Retry(NamedTuple):
    pickup_from: int = 0
    manual_licence: bool = False
    plates: bool = False


class Context:
    """Static facts about the world, loaded once per run: map and driver list."""

    def __init__(self, world_map: dict, roster: list[dict]):
        self.places = {p["id"]: p for p in world_map["places"]}
        self.road = {(r["from"], r["to"]): r for r in world_map["roads"]}
        self.roster = roster
        self.drivers_in: dict[str, int] = {}
        for d in roster:
            self.drivers_in[d["homePlaceId"]] = self.drivers_in.get(d["homePlaceId"], 0) + 1

    def minutes(self, a: str, b: str) -> int:
        return self.road[(a, b)]["minutes"]

    def km(self, a: str, b: str) -> float:
        return self.road[(a, b)]["km"]


class Desk:
    """Defaults = the kit starter. Subclass and override hooks; tune with `params`."""

    DEFAULTS: dict[str, Any] = {}

    def __init__(self, world: World, level: int, now: int, ctx: Optional[Context] = None, params: Optional[dict] = None):
        self.world, self.level, self.now, self.ctx = world, level, now, ctx
        self.p = {**self.DEFAULTS, **(params or {})}
        self.outbox: list[Action] = []
        self.requests: dict[str, PriceRequest] = {}
        self.orders: dict[str, Order] = {}
        self.leg_gigs: dict[str, dict[int, str]] = {}
        self.booked: set[str] = set()
        self.posts: dict[str, PostAction] = {}
        self.urgent: set[str] = set()
        self.stats: dict[str, int] = {}
        # --- metrics (filled by the engine for every policy; summarised by metrics()) ---
        self.ev_count: dict[str, int] = {}
        self.money: dict[str, float] = {}
        self.q_ratio: dict[str, float] = {}      # request -> min quoted price / list (real quotes only)
        self.won_ratio: list[float] = []
        self.won_opt: dict[str, int] = {}
        self.wins_by_day: dict[int, int] = {}
        self.quotes_by_day: dict[int, int] = {}
        self.fee_paid: dict[str, float] = {}     # order -> driver fees (cents)
        self.late_orders = 0
        self.deferred: dict[str, int] = {}       # order id -> minute to post (just-in-time posting)

    def count(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    # ------------------------------------------------------------------ hooks
    def on_start(self) -> None:
        pass

    def on_event(self, event: DeskEvent) -> None:
        pass

    def price_quote(self, request: PriceRequest) -> dict[str, int]:
        """Starter: list price of the first option only."""
        first = request["options"][0]
        return {first["kind"]: first["listPriceCents"]}

    def fee_schedule(self, order: Order, cars: int, urgent: bool) -> list[FeeStep]:
        fee = self.requests[order["id"]]["referenceFeeCents"] * cars / len(order["legs"])
        return steep(self.now, fee, self.level) if urgent else rising(self.now, fee, self.level)

    def audience_for(self, order: Order, legs: list[int], retry: Retry) -> Audience:
        return {"experienced": any(leg["car"]["premium"] for leg in order["legs"]), "manualLicence": retry.manual_licence}

    def metrics(self) -> dict:
        """One flat dict per run for analysis (lab/report.py)."""
        import statistics as st
        n_req = sum(1 for _ in self.requests)
        n_q = len(self.q_ratio)
        won = self.ev_count.get("order_won", 0)
        fee_ratio = [self.fee_paid[o] / self.requests[o]["referenceFeeCents"] for o in self.fee_paid if o in self.requests]
        m = {
            "requests": n_req, "quoted": n_q, "declined": n_req - n_q, "won": won, "lost": self.ev_count.get("order_lost", 0),
            "win_rate_quoted": round(won / n_q, 3) if n_q else 0,
            "q_ratio_med": round(st.median(self.q_ratio.values()), 3) if self.q_ratio else None,
            "won_ratio_med": round(st.median(self.won_ratio), 3) if self.won_ratio else None,
            "fee_ratio_med": round(st.median(fee_ratio), 3) if fee_ratio else None,
            "fee_ratio_mean": round(st.mean(fee_ratio), 3) if fee_ratio else None,
            "late_orders": self.late_orders,
            "drops": self.ev_count.get("gig_dropped", 0), "expired": self.ev_count.get("gig_expired", 0),
            "warnings": self.ev_count.get("deadline_close", 0), "failed_visits": self.ev_count.get("visit_failed", 0),
            "cancelled": self.ev_count.get("order_cancelled", 0),
        }
        m.update({f"eur_{k}": round(v) for k, v in self.money.items()})
        m.update({f"won_{k}": v for k, v in self.won_opt.items()})
        m["wins_by_day"] = [self.wins_by_day.get(d, 0) for d in range(5)]
        m["quotes_by_day"] = [self.quotes_by_day.get(d, 0) for d in range(5)]
        if won:
            m["eur_per_order"] = round(sum(self.money.values()) / won, 1)
        return m

    # helper for policies
    def decline(self, request: PriceRequest) -> dict[str, int]:
        first = request["options"][0]
        return {first["kind"]: first["listPriceCents"] * DECLINE_MULT}

    # ------------------------------------------------------------------ restart (from the kit starter)
    def rejoin(self, snapshot: DeskSnapshot, history: list[DeskEvent]) -> None:
        """Rebuilds the books from the world after a (re)start, then answers what was missed:
        open requests, orders without a gig, failed visits without a new gig. Learning state is
        replayed from the history through on_event (no actions are taken during the replay)."""
        posted: dict[str, list[Gig]] = {}
        self.booked = {g["id"] for g in snapshot["gigs"] if g["status"] in ("booked", "working", "done")}
        for gig in snapshot["gigs"]:
            for oid in dict.fromkeys(st["orderId"] for st in gig["stops"]):
                posted.setdefault(oid, []).append(gig)
            if gig["status"] in ("open", "booked", "working"):
                self.carry({"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": gig["schedule"]}, gig["id"])
        self.requests = {e["request"]["id"]: self.adjust_request(e["request"]) for e in history if e["kind"] == "price_request"}
        self.urgent = {e["orderId"] for e in history if e["kind"] == "deadline_close"}
        # replay learning (trust, price level, viewers...) without acting; orders known first so trust counts work
        self.orders = {e["order"]["id"]: e["order"] for e in history if e["kind"] == "order_won"}
        saved, now = self.outbox, self.now
        # Only replay learning if we took part (orders or gigs exist). A world joined mid-week (test finals start on
        # Thursday) has history we never quoted: its order_lost events are not our losses.
        took_part = bool(snapshot["orders"]) or bool(snapshot["gigs"])
        for e in (history if took_part else []):
            try:
                self.now = e["at"]
                if e["kind"] == "price_request":   # rebuild what we quoted (pending) so learning replays
                    self.price_quote(self.requests[e["request"]["id"]])
                self.on_event(e)
            except Exception:  # noqa: BLE001 - learning replay must never stop a restart
                pass
        self.outbox, self.now = saved, now
        self.orders = {o["id"]: o for o in snapshot["orders"] if o["id"] in self.requests and o["status"] != "cancelled"}
        for order in self.orders.values():
            if order["status"] == "waiting" and not self.gigs_of(order["id"]):
                at = self.defer_until(order)
                if at > self.now:
                    self.deferred[order["id"]] = at
                else:
                    self.post(order, undelivered(order))
        for event in history:
            order = self.orders.get(event.get("orderId", ""))
            if order is None:
                continue
            if event["kind"] == "visit_failed" and order["deliveredAt"][event["leg"]] is None:
                later = [g for g in posted.get(order["id"], []) if g["postedAt"] >= event["at"] and g["id"] != event["gigId"]]
                if not any(st["leg"] == event["leg"] and st["orderId"] == order["id"] for g in later for st in g["stops"]):
                    self.retry(order["id"], event["leg"], event["reason"])
        for request in snapshot["openRequests"]:
            self.quote(request)

    # ------------------------------------------------------------------ engine (starter logic)
    def handle(self, event: DeskEvent) -> None:
        k = event["kind"]
        self.ev_count[k] = self.ev_count.get(k, 0) + 1
        if k == "ledger":
            line = event["line"]
            self.money[line["kind"]] = self.money.get(line["kind"], 0) + line["cents"] / 100
            if line["kind"] == "driver_fee" and line.get("orderId"):
                self.fee_paid[line["orderId"]] = self.fee_paid.get(line["orderId"], 0) - line["cents"]
            if line["kind"] == "late_refund":
                self.late_orders += 1
        elif k == "order_won":
            o = event["order"]
            r = self.requests.get(o["id"])
            if r:
                lp = next((x["listPriceCents"] for x in r["options"] if x["kind"] == o["option"]), None)
                if lp:
                    self.won_ratio.append(o["priceCents"] / lp)
            self.won_opt[o["option"]] = self.won_opt.get(o["option"], 0) + 1
            d = event["at"] // DAY
            self.wins_by_day[d] = self.wins_by_day.get(d, 0) + 1
        self.on_event(event)
        if k == "price_request":
            self.quote(event["request"])
        elif k == "order_won":
            self.win(event["order"])
        elif k == "order_changed":
            self.change(event["order"])
        elif k == "order_cancelled":
            self.deferred.pop(event["orderId"], None)
            for books in (self.orders, self.leg_gigs):
                books.pop(event["orderId"], None)
        elif k == "visit_failed":
            self.retry(event["orderId"], event["leg"], event["reason"])
        elif k == "gig_expired":
            self.repost(event["gigId"])
        elif k == "deadline_close":
            self.raise_fees(event["orderId"])
        elif k == "gig_booked":
            self.booked.add(event["gigId"])
        elif k in ("gig_dropped", "no_show"):
            self.booked.discard(event["gigId"])
        elif k == "delivered":
            self.leg_gigs.get(event["orderId"], {}).pop(event["leg"], None)
            if event["orderId"] in self.orders:
                self.orders[event["orderId"]]["deliveredAt"][event["leg"]] = event["at"]

    def adjust_request(self, request: PriceRequest) -> PriceRequest:
        """Hook: a policy may return a corrected copy (e.g. a de-noised typical fee)."""
        return request

    def quote(self, request: PriceRequest) -> None:
        request = self.adjust_request(request)
        self.requests[request["id"]] = request
        prices = self.price_quote(request)
        if not prices:  # never leave a request unquoted (costs goodwill): decline instead
            prices = self.decline(request)
        prices = {k: max(1, int(round(v))) for k, v in prices.items()}
        if self.level <= 3:
            # no competitor up to level 3: every quote wins the first option at list price, so a "decline" quote
            # would win. Decline by not quoting (free at these levels).
            first = request["options"][0]
            if min(prices.values()) >= 3 * first["listPriceCents"]:
                self.count("l3_noquote")
                return
        lists = {o["kind"]: o["listPriceCents"] for o in request["options"]}
        ratio = min(v / lists[k] for k, v in prices.items() if k in lists) if prices else 99
        if ratio < 5:
            self.q_ratio[request["id"]] = ratio
            d = request["arrivedAt"] // DAY
            self.quotes_by_day[d] = self.quotes_by_day.get(d, 0) + 1
        self.outbox.append({"type": "quote", "requestId": request["id"], "prices": prices})

    def win(self, order: Order) -> None:
        if order["id"] in self.requests and order["id"] not in self.orders:
            self.orders[order["id"]] = order
            at = self.defer_until(order)
            if at > self.now:
                self.deferred[order["id"]] = at
                self.count("deferred")
            else:
                self.post(order, undelivered(order))

    def defer_until(self, order: Order) -> int:
        """Just-in-time posting (param defer=1): post on the day before the pickup day at defer_hour,
        but at least defer_lead_h hours before lastPickupAt, and never in the 22:00-07:00 blackout."""
        if not self.p.get("defer"):
            return 0
        ready = min(l["pickup"]["window"]["from"] for l in order["legs"])
        pickup_day = max(ready, self.now) // DAY
        at = (pickup_day - 1) * DAY + int(self.p.get("defer_hour", 8) * 60)
        at = min(at, order["lastPickupAt"] - int(self.p.get("defer_lead_h", 18) * 60))
        h = (at % DAY) / 60
        if h >= 22:
            at = at // DAY * DAY + 22 * 60 - 1
        elif h < 7:
            at = at // DAY * DAY - 2 * 60 - 1  # 21:59 the evening before
        return at if at > self.now + 30 else 0

    def next_wake(self) -> Optional[int]:
        return min(self.deferred.values()) if self.deferred else None

    def tick(self) -> None:
        """Called by the runner after each step: posts the deferred orders that are due."""
        due = [o for o, at in self.deferred.items() if at <= self.now]
        for oid in due:
            del self.deferred[oid]
            order = self.orders.get(oid)
            if order and not self.gigs_of(oid) and None in order["deliveredAt"]:
                self.post(order, undelivered(order))

    def change(self, order: Order) -> None:
        if order["id"] in self.deferred:
            self.orders[order["id"]] = order
            self.deferred[order["id"]] = self.defer_until(order) or self.now
            return
        if order["id"] in self.orders:
            self.orders[order["id"]] = order
            if self.withdraw(order["id"]):
                self.post(order, undelivered(order))

    def repost(self, gig_id: str) -> None:
        action = self.posts.get(gig_id)
        if action is None or not any(self.leg_gigs.get(s["orderId"], {}).get(s["leg"]) == gig_id for s in action["stops"]):
            return
        for stop in action["stops"]:
            self.leg_gigs.get(stop["orderId"], {}).pop(stop["leg"], None)
        order = self.orders.get(action["stops"][0]["orderId"])
        if order is None:
            return
        stops = without_windows(action["stops"], float("inf"))
        self.outbox.append({**action, "stops": stops, "schedule": self.fees_for(order, pickups(action))})

    def raise_fees(self, order_id: str) -> None:
        order = self.orders.get(order_id)
        if order is None:
            return
        if self.deferred.pop(order_id, None) is not None:  # warned while deferred: post now (urgent)
            self.urgent.add(order_id)
            self.post(order, undelivered(order))
            return
        self.urgent.add(order_id)
        self.send_post_of(order_id)
        for gig_id in self.gigs_of(order_id):
            if gig_id not in self.booked:
                self.outbox.append({"type": "reprice", "gigId": gig_id, "schedule": self.fees_for(order, pickups(self.posts[gig_id]))})

    def fees_for(self, order: Order, cars: int) -> list[FeeStep]:
        sched = clean_schedule(self.fee_schedule(order, cars, order["id"] in self.urgent))
        return sched[:1] if self.level == 1 else sched   # level 1: one fee only

    def retry(self, order_id: str, leg: int, reason: str) -> None:
        if order_id in self.orders:
            order = self.orders[order_id]
            self.leg_gigs.get(order_id, {}).pop(leg, None)
            car_not_there = reason in ("not_ready", "closed")
            pickup_from = retry_from(order, self.requests[order_id], leg, self.now) if car_not_there else 0
            self.post(order, [leg], Retry(pickup_from, manual_licence=reason == "licence", plates=reason == "no_plates"))

    def post(self, order: Order, legs: list[int], retry: Retry = Retry()) -> None:
        note = self.requests[order["id"]]["note"]
        if self.p.get("notes2") and note:
            t = note["text"].lower()
            retry = Retry(retry.pickup_from,
                          manual_licence=retry.manual_licence or bool(MANUAL.search(t)),
                          plates=retry.plates or bool(PLATES.search(t)))
        if self.p.get("notes3") and note and retry.pickup_from == 0:
            from .notes import ready_time
            rt = ready_time(note["text"], self.requests[order["id"]]["arrivedAt"])
            if rt is not None:
                first_from = min(order["legs"][l]["pickup"]["window"]["from"] for l in legs)
                if first_from < rt <= order["deadline"] - 60:
                    retry = Retry(rt, retry.manual_licence, retry.plates)
                    self.count("notes3_delay")
        audience = self.audience_for(order, legs, retry)
        km_of = (lambda a, b: self.ctx.km(a, b)) if (self.p.get("charge_fix") and self.ctx) else None
        stops = without_windows(stops_for(order, legs, note, retry, km_of), self.now)
        self.outbox.append({"type": "post", "stops": stops, "audience": audience, "schedule": self.fees_for(order, len(legs))})
        if len(legs) == 1:
            return
        self.send()
        if not self.gigs_of(order["id"]):
            for leg in legs:
                self.post(order, [leg], retry)

    def gigs_of(self, order_id: str) -> list[str]:
        return list(dict.fromkeys(self.leg_gigs.get(order_id, {}).values()))

    def carry(self, action: PostAction, gig_id: str) -> None:
        for stop in action["stops"]:
            self.leg_gigs.setdefault(stop["orderId"], {})[stop["leg"]] = gig_id
        self.posts[gig_id] = action

    def withdraw(self, order_id: str) -> bool:
        self.send_post_of(order_id)
        gigs = self.gigs_of(order_id)
        if any(gig_id in self.booked for gig_id in gigs):
            return False
        self.leg_gigs.pop(order_id, None)
        self.outbox += [{"type": "withdraw", "gigId": gig_id} for gig_id in gigs]
        return True

    def send_post_of(self, order_id: str) -> None:
        if any(a["type"] == "post" and a["stops"][0]["orderId"] == order_id for a in self.outbox):
            self.send()

    def send(self) -> None:
        actions, self.outbox = self.outbox, []
        actions.sort(key=lambda a: a["type"] != "quote")  # quotes first: they expire
        if actions:
            self.read_results(actions, safe_act(self.world, actions, self))

    def read_results(self, actions: list[Action], results: list[ActionResult]) -> None:
        for action, result in zip(actions, results):
            if not result.get("ok", False):
                self.count(f"rejected_{action['type']}")
            if action["type"] == "post" and result["ok"] is True:
                self.carry(action, result["id"])


# ---------------------------------------------------------------------- robustness helpers
def clean_schedule(sched) -> list:
    """Whole minutes, strictly increasing times, non-decreasing fees, 1..48 steps (the server rejects anything else)."""
    out = []
    for st in sorted(sched, key=lambda x: x["at"]):
        at, fee = int(st["at"]), max(1, int(st["feeCents"]))
        if out and fee < out[-1]["feeCents"]:
            fee = out[-1]["feeCents"]
        if out and at <= out[-1]["at"]:
            out[-1]["feeCents"] = max(out[-1]["feeCents"], fee)
            continue
        out.append({"at": at, "feeCents": fee})
    return out[:48] or [{"at": 0, "feeCents": 1}]


def safe_act(world, actions, desk=None):
    """world.act, but a 400 on a batch (one bad action) must not drop the others (e.g. quotes): retry one by one."""
    from spread.client import SpreadError
    try:
        return world.act(actions)
    except SpreadError as e:
        if e.status != 400:
            raise
        if desk is not None:
            desk.count("batch_400")
        res = []
        for a in actions:
            try:
                res += world.act([a])
            except SpreadError as e2:
                if e2.status != 400:
                    raise
                res.append({"ok": False, "reason": str(e2)})
        return res


# ---------------------------------------------------------------------- helpers (from the starter)
def retry_from(order: Order, request: PriceRequest, leg: int, now: int) -> int:
    promised = next((o["deadline"] for o in request["options"] if o["kind"] == order["option"]), order["deadline"])
    delay = max(0, order["deadline"] - promised)
    return max(now + 2 * HOUR, order["legs"][leg]["pickup"]["window"]["from"] + delay)


def undelivered(order: Order) -> list[int]:
    return [leg for leg in range(len(order["legs"])) if order["deliveredAt"][leg] is None]


def pickups(action: PostAction) -> int:
    return sum(1 for stop in action["stops"] if stop["kind"] == "pickup")


def without_windows(stops: list[StopRef], before: float) -> list[StopRef]:
    return [{k: v for k, v in stop.items() if k != "window"} if "window" in stop and stop["window"]["to"] < before else stop for stop in stops]


def rising(now: int, fee: float, level: int) -> list[FeeStep]:
    return [{"at": now + k * HOUR, "feeCents": max(1, int(fee * (1 + k / 10) + 0.5))} for k in range(1 if level == 1 else 6)]


def steep(now: int, fee: float, level: int) -> list[FeeStep]:
    return [{"at": now + k * 30, "feeCents": max(1, int(fee * (1.5 + k / 4) + 0.5))} for k in range(1 if level == 1 else 5)]


MANUAL = re.compile(r"manuaali|manuell|manual|käsivaihte|vaihdekepp|stick", re.IGNORECASE)
PLATES = re.compile(r"kilv|plates?\b|skylt|rekisterikilv|ei kilpiä|no plates|utan skyltar", re.IGNORECASE)


def stops_for(order: Order, legs: list[int], note: Optional[Note], retry: Retry, km_of=None) -> list[StopRef]:
    stops: list[StopRef] = []
    for leg in legs:
        car, pickup, delivery = order["legs"][leg]["car"], order["legs"][leg]["pickup"], order["legs"][leg]["delivery"]
        noted = window_from_note(note, pickup["window"], "pickup")
        start = max(noted["from"], retry.pickup_from)
        pickup_window: TimeWindow = {"from": start, "to": max(noted["to"], start)}
        delivery_base: TimeWindow = {"from": delivery["window"]["from"], "to": max(delivery["window"]["from"], order["deadline"])}
        delivery_window = window_from_note(note, delivery_base, "delivery")
        low_battery = car["electric"] and car["chargePercent"] is not None and car["chargePercent"] < 30
        if low_battery and km_of is not None and km_of(pickup["placeId"], delivery["placeId"]) <= 200:
            low_battery = False  # rule 3: a charging stop is needed only on a route over 200 km
        first: StopRef = {"orderId": order["id"], "leg": leg, "kind": "pickup", "withPlates": retry.plates, "withCharging": low_battery}
        second: StopRef = {"orderId": order["id"], "leg": leg, "kind": "delivery"}
        stops += [narrower(first, pickup_window, pickup["window"]), narrower(second, delivery_window, delivery_base)]
    return stops


def narrower(stop: StopRef, window: TimeWindow, base: TimeWindow) -> StopRef:
    return {**stop, "window": window} if window["from"] > base["from"] or window["to"] < base["to"] else stop


AFTER = re.compile(r"jälkeen|alkaen|aikaisintaan|\bafter\b|\bfrom\b|earliest|not before|ei ennen|valmis|\bready\b|efter|tidigast|inte före|klar", re.ASCII)
BEFORE = re.compile(r"ennen|mennessä|viim|\bbefore\b|\bby\b|latest|före|senast", re.ASCII)
DELIVERY = re.compile(r"toimit|perillä|perille|vastaanot|kohde|deliver|arrive|destination|receiv|leverera|leverans|framme|mottag", re.ASCII)
CLOCK = re.compile(r"(?:klo|kl\.?)\s*(\d{1,2})(?:[.:](\d{2}))?|\b(\d{1,2})[.:](\d{2})\b", re.ASCII)
RANGE = re.compile(r"\b(\d{1,2})(?:[.:](\d{2}))?\s*[-–]\s*(\d{1,2})(?:[.:](\d{2}))?\b", re.ASCII)


def window_from_note(note: Optional[Note], window: TimeWindow, stop: str) -> TimeWindow:
    if not note:
        return window
    text = note["text"].lower()
    if bool(DELIVERY.search(text)) != (stop == "delivery"):
        return window

    def minutes(hour: int, minute: int) -> Optional[int]:
        return None if hour > 24 or minute > 59 else hour * HOUR + minute

    start, end = window["from"], window["to"]
    for match in RANGE.finditer(text):
        opens, closes = minutes(int(match[1]), int(match[2] or 0)), minutes(int(match[3]), int(match[4] or 0))
        if opens is None or closes is None or opens >= closes:
            continue
        start = max(start, start // DAY * DAY + opens)
        end = min(end, end // DAY * DAY + closes)
    text = RANGE.sub(" ", text)
    for match in CLOCK.finditer(text):
        m = minutes(int(match[1] or match[3]), int(match[2] or match[4] or 0))
        if m is None:
            continue
        time = window["from"] // DAY * DAY + m
        around = text[max(0, match.start() - 16): match.end() + 16]
        if AFTER.search(around):
            start = max(start, time)
        elif BEFORE.search(around):
            end = min(end, time)
    return {"from": start, "to": end} if start <= end else window
