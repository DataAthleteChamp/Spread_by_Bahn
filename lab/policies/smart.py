"""Smart: one policy, every idea behind a switch, so presets = strategies and switching = ablation.

Ideas (flags in DEFAULTS):
  gate    Staffability gate: only offer options whose deadline is reachable (ready/respond + lead + drive),
          and decline when few drivers live within reach of pickup and delivery (exp-weighted by road minutes).
  scarce  Price uplift where drivers are scarce: mult * (1 + scarce_k / (1 + reach_pickup)).
  track   Robbins-Monro target tracking of the price level: on win m *= 1+a, on loss m *= 1-b
          -> converges to the price where P(win) = b/(a+b) (= win_target). Global + per pickup town.
  cap     Capacity budget per pickup town per day (top-down from reach), over budget -> premium price only.
  hire    Fee schedule: opening fee lowered where many drivers live near the delivery (cheap trip home),
          flat until a single late step before lastPickupAt (no ramp -> drivers don't learn to wait).
  offers  Direct offers on deadline_close / late expiry: drivers who viewed the order, finished near the
          pickup, or live there; max 3/driver/day, 3 open/gig.
  safety  On-time controller: EMA of deadline warnings per won order; above target -> tighten gate and
          raise prices (one dual variable mu).
"""
from __future__ import annotations

import math
from collections import defaultdict

from ..desk import DAY, HOUR, Desk, undelivered


class Smart(Desk):
    NAME = "smart"
    DEFAULTS = {
        # quote
        "mult": 1.45, "same_day_mult": 1.0, "w3_mult": 1.0,
        "gate": 1, "lead_min": 120, "slack_min": 30, "tau": 60.0, "min_reach": 20.0, "drop_w": 0.5,
        "scarce": 1, "scarce_k": 0.3,
        "track": 0, "win_target": 0.45, "rm_step": 0.03, "town_step": 0.02, "m_lo": 1.0, "m_hi": 2.2,
        "cap": 0, "cap_k": 1.0, "cap_mult": 1.35,
        # hire
        "hire": 1, "fee_open": 1.15, "drop_disc": 0.08, "fee_floor": 0.9, "fee_late": 1.7, "late_h": 4,
        "urgent_open": 1.9, "urgent_max": 2.8,
        "offers": 0, "offer_mult": 1.7, "offer_n": 3,
        # risk-based hiring: higher opening fee for long drives / remote delivery towns
        "fee_long_k": 0.0, "fee_remote_k": 0.0,
        # early time-based escalation: unbooked after step1_min -> step1_f x typical, after step2_min -> step2_f
        "step1_min": 0, "step1_f": 1.3, "step2_min": 0, "step2_f": 1.6,
        # quote uplift for remote delivery towns (expensive trip home) and long drives
        "scarce_b_k": 0.0, "long_k": 0.0, "max_drive": 10000,
        # market-maker backlog skew (Avellaneda-Stoikov): uplift per unstaffed order in pickup town
        "skew": 0, "skew_k": 0.04, "skew_max": 0.5,
        # price-war guard: freeze tracker & hold price when loss rate spikes (CUSUM)
        "warguard": 0, "cusum_k": 0.25, "cusum_h": 6.0,
        # learned staffability model (lab/models/risk.json): decline options with P(late) > risk_max,
        # otherwise price uplift risk_k * P(late)
        "risk": 0, "risk_max": 0.25, "risk_k": 1.0, "risk_file": "risk.json",
        # just-in-time posting, notes at first post, charging-stop fix (desk.py)
        "defer": 0, "defer_hour": 8, "defer_lead_h": 18, "notes2": 0, "notes3": 0, "charge_fix": 0,
        # pairing: when deferred orders come due, chain A(a->b)+B(b'->c) into one gig if b' is within pair_gap min of b
        "trust": 0, "trust_k": 1.0,
        # risk-targeted opening fee: open = base + hard_k * max(0, P(late) - hard_thr)
        "hard_k": 0.0, "hard_thr": 0.15,
        "easy_f": 0.0, "easy_pl": 0.10, "easy_cov": 10,
        "pm_sd_open": 0.0,   # same_day gigs posted after 14:00 open at least at this fee/typical (afternoon waits are 20+ min)
        # trust protection: value at stake if late = 0.01*n/2 * remaining expected revenue from the dealer
        "protect": 0, "protect_k": 1.0, "protect_fee_k": 0.0, "protect_cap": 0.6, "protect_cap_eur": 20,
        # offers v2: on delivered, offer our now-free driver an unbooked gig near them (daytime) at offer2_f x app fee
        "offers2": 0, "offer2_f": 1.0, "offer2_gap": 45,
        "pair": 0, "batch_min": 0, "batch_slack_h": 6, "pair_gap": 45, "pair_disc": 0.85, "pair_horizon_h": 30, "pair_max_drive": 600,
        # safety2: projected on-time controller; mu = clip(s2_k*(s2_target - projected OT), 0, mu_max)
        "safety2": 0, "s2_target": 0.94, "s2_k": 8.0, "s2_warn_p": 0.6, "s2_base_p": 0.03, "s2_min_orders": 40,
        # safety
        "safety": 0, "warn_target": 0.25, "mu_step": 0.05, "mu_max": 0.6,
    }

    # ------------------------------------------------------------------ setup
    def on_start(self):
        c = self.ctx
        self.risk_model = None
        if self.p["risk"]:
            import json
            from pathlib import Path
            self.risk_model = json.loads((Path(__file__).resolve().parent.parent / "models" / self.p["risk_file"]).read_text())
        towns = list(c.places)
        tau = float(self.p["tau"])
        self.reach = {t: sum(math.exp(-c.minutes(d["homePlaceId"], t) / tau) for d in c.roster) for t in towns}
        def hav(p1, p2):
            R = 6371.0
            la1, lo1, la2, lo2 = map(math.radians, (p1["lat"], p1["lon"], p2["lat"], p2["lon"]))
            h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
            return 2 * R * math.asin(math.sqrt(h))
        self.cov30 = {t: sum(1 for d in c.roster if hav(c.places[d["homePlaceId"]], c.places[t]) <= 30) for t in towns}
        self.homes = defaultdict(list)
        for d in c.roster:
            self.homes[d["homePlaceId"]].append(d)
        self.m = self.p["mult"]                 # tracked global price level
        self.m_town = defaultdict(lambda: 1.0)  # tracked per pickup-town offset
        self.quoted: dict[str, tuple[str, bool]] = {}   # request -> (pickup town, real quote?)
        self.won_by_town_day = defaultdict(int)
        self.gig_driver: dict[str, str] = {}
        self.driver_at: dict[str, tuple[str, int]] = {}  # driver -> (place, minute) where our gig ended
        self.viewers = defaultdict(set)         # order -> drivers who viewed its gigs
        self.offers_today = defaultdict(int)    # (driver, day) -> offers
        self.open_offers = defaultdict(int)     # gig -> open offers
        self.gig_order: dict[str, str] = {}
        self.mu = 0.0
        self.pair_of: dict[str, str] = {}
        self.pl_of: dict = {}
        self.open_f_of: dict = {}
        self.trust_n = defaultdict(int)
        self.snow = []   # (places, from, to) from forecast events
        self.dealer_req = defaultdict(int)       # requests seen per dealer
        self.dealer_rev = defaultdict(float)     # revenue (cents) of orders won per dealer   # dealer -> on-time orders counted (rules: +1% accepted price each, cap 25; late halves)
        self.cusum = 0.0
        self.war_day = -1
        self.loss_ema = 0.5
        self.warn_ema = self.p["warn_target"]

    # ------------------------------------------------------------------ learning from events
    def on_event(self, e):
        k = e["kind"]
        if k == "forecast":
            self.snow.append((set(e.get("placeIds") or []), e.get("from", 0), e.get("to", 0)))
        if k == "price_request":
            self.dealer_req[e["request"]["dealerId"]] += 1
        if k in ("order_won", "order_lost"):
            rid = e["order"]["id"] if k == "order_won" else e.get("requestId") or e.get("orderId")
            town, real = self.quoted.get(rid, (None, False))
            if real and self.p["warguard"]:
                lost = 1.0 if k == "order_lost" else 0.0
                # CUSUM on losses above the running loss level
                self.cusum = max(0.0, self.cusum + lost - self.loss_ema - self.p["cusum_k"])
                self.loss_ema = 0.97 * self.loss_ema + 0.03 * lost
                if self.cusum > self.p["cusum_h"] and self.war_day != e["at"] // DAY:
                    self.war_day = e["at"] // DAY
                    self.count("war_alarm")
            frozen = self.p["warguard"] and self.war_day == e["at"] // DAY
            if real and self.p["track"] and not frozen:
                a = self.p["rm_step"]
                w = self.p["win_target"]
                # win -> raise (step a*(1-w)), loss -> lower (step a*w): stationary where P(win)=w
                f = 1 + a * (1 - w) if k == "order_won" else 1 - a * w
                self.m = min(self.p["m_hi"], max(self.p["m_lo"], self.m * f))
                if town:
                    a2 = self.p["town_step"]
                    self.m_town[town] *= (1 + a2 * (1 - w)) if k == "order_won" else (1 - a2 * w)
                    self.m_town[town] = min(1.3, max(0.8, self.m_town[town]))
            if k == "order_won":
                o = e["order"]
                self.dealer_rev[o["dealerId"]] += o["priceCents"]
                self.won_by_town_day[(o["legs"][0]["pickup"]["placeId"], e["at"] // DAY)] += 1
                self.warn_ema = 0.98 * self.warn_ema  # one more won order without warning (so far)
        elif k == "order_cancelled" and self.p.get("pair"):
            for g in e.get("gigs", []):
                if g.get("outcome") == "withdrawn":
                    for st in self.posts.get(g["gigId"], {}).get("stops", []):
                        oid = st["orderId"]
                        if oid != e["orderId"] and oid in self.orders:
                            self.leg_gigs.get(oid, {}).pop(st["leg"], None)
                            o = self.orders[oid]
                            if None in o["deliveredAt"] and not self.gigs_of(oid):
                                self.post(o, undelivered(o))
        elif k == "deadline_close":
            self.warn_ema = 0.98 * self.warn_ema + 0.02
            if self.p["offers"]:
                self.send_offers(e["orderId"])
        elif k == "gig_viewed":
            o = self.gig_order.get(e["gigId"])
            if o:
                self.viewers[o].add(e["driverId"])
        elif k == "gig_booked":
            self.gig_driver[e["gigId"]] = e.get("driverId")
        elif k == "delivered":
            o = self.orders.get(e["orderId"])
            if o is not None:
                legs_done = [x if i != e["leg"] else e["at"] for i, x in enumerate(o["deliveredAt"])]
                if None not in legs_done:  # the order's last car: dealer trust update
                    dl = o["dealerId"]
                    if max(legs_done) <= o["deadline"]:
                        self.trust_n[dl] = min(25, self.trust_n[dl] + 1)
                    else:
                        self.trust_n[dl] //= 2
            d = self.gig_driver.get(e.get("gigId"))
            if d:
                self.driver_at[d] = (e["placeId"], e["at"])
                if self.p["offers2"]:
                    self.offer_to_free_driver(d, e["placeId"], e["at"], e.get("gigId"))
        elif k == "offer_answered":
            self.open_offers[e.get("gigId")] = max(0, self.open_offers[e.get("gigId")] - 1)
            ans = e.get("answer") or e.get("status") or e.get("result")
            self.count(f"offer_{ans}")
        if self.p["safety2"] and k in ("order_won", "deadline_close", "delivered"):
            self.update_safety2()
        if self.p["safety"] and k in ("order_won", "deadline_close"):
            err = self.warn_ema - self.p["warn_target"]
            self.mu = min(self.p["mu_max"], max(0.0, self.mu + self.p["mu_step"] * err))

    def carry(self, action, gig_id):
        super().carry(action, gig_id)
        self.gig_order[gig_id] = action["stops"][0]["orderId"]

    def snow_at(self, a, b, t):
        return any((a in pl or b in pl) and fr - 12 * 60 <= t <= to for pl, fr, to in self.snow)

    def update_safety2(self):
        P = self.p
        n = len(self.orders)
        if n < P["s2_min_orders"]:
            return
        late = exp = 0.0
        for o in self.orders.values():
            if None not in o["deliveredAt"]:
                late += max(o["deliveredAt"]) > o["deadline"]
            else:
                exp += P["s2_warn_p"] if o["id"] in self.urgent else P["s2_base_p"]
                if self.now > o["deadline"]:
                    late += 1; exp -= P["s2_warn_p"] if o["id"] in self.urgent else P["s2_base_p"]
        proj = 1 - (late + exp) / n
        self.proj_ot = proj
        self.mu = min(P["mu_max"], max(0.0, P["s2_k"] * (P["s2_target"] - proj)))

    def trust_at_stake(self, dealer, now):
        """Cents of future revenue lost if this dealer's next order is late: half its trust count x 1% x the
        revenue we still expect from it this week (its request rate so far x days left x our revenue per request)."""
        n = self.trust_n[dealer]
        if n <= 1:
            return 0.0
        # v2: half the counts are lost, but they are re-earned at the dealer's on-time delivery rate; the loss is the
        # margin-weighted 1%/count over the rebuild period only, capped.
        elapsed = max(0.25, (now - 8 * 60) / DAY)
        rev_per_day = self.dealer_rev[dealer] / elapsed
        orders_per_day = max(1.0, sum(1 for o in self.orders.values() if o["dealerId"] == dealer) / elapsed)
        rebuild_days = (n / 2) / orders_per_day
        stake = 0.01 * (n / 2) * 0.5 * rev_per_day * rebuild_days   # avg half the counts missing during the rebuild
        return min(self.p["protect_cap_eur"] * 100, stake)

    # ------------------------------------------------------------------ quoting
    def price_quote(self, r):
        legs = r["legs"]
        a, b = legs[0]["pickup"]["placeId"], legs[0]["delivery"]["placeId"]
        P = self.p
        tighten = 1 + self.mu
        if P["gate"]:
            supply = self.reach[a] + P["drop_w"] * self.reach[b]
            if supply < P["min_reach"] * tighten:
                self.count("decl_supply")
                self.quoted[r["id"]] = (a, False)
                return self.decline(r)
        level = self.m if P["track"] else P["mult"]
        level *= self.m_town[a] if P["track"] else 1.0
        if P["scarce"]:
            level *= 1 + P["scarce_k"] * 30 / (30 + self.reach[a])  # Rovaniemi +25%, Helsinki +3% at k=0.3
        level *= 1 + 0.5 * self.mu
        if P["trust"]:
            level *= 1 + P["trust_k"] * 0.01 * self.trust_n[r["dealerId"]]
        if P["skew"]:
            q = sum(1 for o in self.orders.values() if o["legs"][0]["pickup"]["placeId"] == a
                    and not any(g in self.booked for g in self.gigs_of(o["id"])) and None in o["deliveredAt"])
            level *= 1 + min(P["skew_max"], P["skew_k"] * q * 30 / (30 + self.reach[a]) * 3)
        if P["cap"]:
            day = r["arrivedAt"] // DAY
            budget = P["cap_k"] * self.reach[a] / 10  # ~orders/day a town can staff (Vantaa ~32, Oulu ~3)
            if self.won_by_town_day[(a, day)] >= budget:
                level *= P["cap_mult"]
                self.count("over_cap")
        drive = sum(self.ctx.minutes(l["pickup"]["placeId"], l["delivery"]["placeId"]) for l in legs)
        if drive > P["max_drive"]:
            self.count("decl_long")
            self.quoted[r["id"]] = (a, False)
            return self.decline(r)
        level *= 1 + P["scarce_b_k"] * 30 / (30 + self.reach[b]) + P["long_k"] * max(0, drive - 150) / 60
        ready = max(l["pickup"]["window"]["from"] for l in legs)
        start = max(ready, r["respondBy"] + P["lead_min"] * tighten)
        prices = {}
        for o in r["options"]:
            if P["gate"] and start + drive + P["slack_min"] > o["deadline"]:
                self.count(f"gate_{o['kind']}")
                continue
            if self.risk_model is not None:
                pl = self.p_late(r, o)
                if pl > P["risk_max"] * (1 - 0.5 * self.mu):
                    self.count(f"risk_decl_{o['kind']}")
                    continue
                risk_up = 1 + P["risk_k"] * pl
            else:
                risk_up = 1.0
            m = risk_up * level * (P["same_day_mult"] if o["kind"] == "same_day" else P["w3_mult"] if o["kind"] == "within_3_days" else 1.0)
            prices[o["kind"]] = o["listPriceCents"] * m
        if not prices:
            self.quoted[r["id"]] = (a, False)
            return self.decline(r)
        self.quoted[r["id"]] = (a, True)
        return prices

    def p_late(self, r, o):
        from ..train_risk import features
        rm = self.risk_model
        day, a = r["arrivedAt"] // DAY, r["legs"][0]["pickup"]["placeId"]
        x = features(r, o, self.reach, (self.won_by_town_day[(a, day)], self.wins_by_day.get(day, 0)))
        z = rm["intercept"] + sum(c * (v - m) / s for c, v, m, s in zip(rm["coef"], x, rm["mu"], rm["sd"]))
        pl = 1 / (1 + math.exp(-z))
        self.pl_of[(r["id"], o["kind"])] = pl
        return pl

    # ------------------------------------------------------------------ hiring
    def fee_schedule(self, order, cars, urgent):
        P = self.p
        fee = self.requests[order["id"]]["referenceFeeCents"] * cars / len(order["legs"])
        now = self.now
        if urgent:
            lo, hi = P["urgent_open"], P["urgent_max"]
            base = self.open_f_of.get(order["id"], 0.0)   # never reprice below the fee the gig opened at
            lo, hi = max(lo, base + 0.1), max(hi, base + 0.3)
            return [{"at": now + k * 30, "feeCents": fee * (lo + (hi - lo) * k / 4)} for k in range(5)]
        if not P["hire"]:
            return super().fee_schedule(order, cars, urgent)
        b = order["legs"][-1]["delivery"]["placeId"]
        drive = sum(self.ctx.minutes(l["pickup"]["placeId"], l["delivery"]["placeId"]) for l in order["legs"])
        open_f = max(P["fee_floor"], P["fee_open"] - P["drop_disc"] * math.log1p(self.reach[b]))
        open_f += P["fee_long_k"] * max(0, drive - 150) / 60 + P["fee_remote_k"] * 30 / (30 + self.reach[b])
        if P["protect"]:
            stake = self.trust_at_stake(order["dealerId"], now)
            if stake > 0:
                open_f += min(P["protect_cap"], P["protect_fee_k"] * stake / max(1.0, fee))
                self.count("protect_open")
        if P["hard_k"]:
            pl = self.pl_of.get((order["id"], order["option"]), 0.0)
            bump = P["hard_k"] * max(0.0, pl - P["hard_thr"])
            if bump > 0:
                open_f += bump
                self.count("hard_open")
        # (2) cheap opening for easy, well-covered gigs (notified drivers near the pickup book in ~1 min)
        if P["easy_f"]:
            pl = self.pl_of.get((order["id"], order["option"]), 1.0)
            a0 = order["legs"][0]["pickup"]["placeId"]
            if pl < P["easy_pl"] and self.cov30[a0] >= P["easy_cov"] and not order["legs"][0]["pickup"]["privateAddress"]:
                open_f = P["easy_f"]
                self.count("easy_open")
        if P["pm_sd_open"] and order["option"] == "same_day" and (now % DAY) >= 14 * 60:
            open_f = max(open_f, P["pm_sd_open"])
            self.count("pm_sd_open")
        self.open_f_of[order["id"]] = open_f
        late = max(open_f, P["fee_late"])
        late_at = order["lastPickupAt"] - P["late_h"] * HOUR
        if late_at <= now:
            return [{"at": now, "feeCents": fee * late}]
        steps = [(now, open_f)]
        for mins, f in ((P["step1_min"], P["step1_f"]), (P["step2_min"], P["step2_f"])):
            if mins and now + mins < late_at:
                steps.append((now + mins, max(f, steps[-1][1])))
        steps.append((late_at, max(late, steps[-1][1])))
        return [{"at": int(t), "feeCents": fee * f} for t, f in steps]

    def defer_until(self, order):
        at = super().defer_until(order)
        bm = self.p.get("batch_min", 0)
        if self.p.get("pair") and bm and at <= self.now and order["lastPickupAt"] - self.now > bm + self.p["batch_slack_h"] * 60:
            h = (self.now % DAY) / 60
            if 7 <= h < 21:
                return self.now + bm   # hold briefly so we can pair it with orders won in the same window
        return at

    # ------------------------------------------------------------------ pairing (multi-order gigs)
    def tick(self):
        if not self.p.get("pair"):
            return super().tick()
        due = [o for o, at in self.deferred.items() if at <= self.now]
        if not due:
            return
        horizon = self.now + self.p["pair_horizon_h"] * 60
        pool = [o for o, at in self.deferred.items() if at <= horizon]   # may pull later orders forward
        used = set()
        for oid in sorted(due, key=lambda o: self.deferred[o]):
            if oid in used:
                continue
            partner = self.find_partner(oid, [o for o in pool if o != oid and o not in used])
            if partner:
                used |= {oid, partner}
                self.post_pair(self.orders[oid], self.orders[partner])
            else:
                used.add(oid)
                order = self.orders.get(oid)
                if order and not self.gigs_of(oid) and None in order["deliveredAt"]:
                    self.post(order, undelivered(order))
        for o in used:
            self.deferred.pop(o, None)

    def _single(self, oid):
        o = self.orders.get(oid)
        if not o or len(o["legs"]) != 1 or o["deliveredAt"][0] is not None or self.gigs_of(oid):
            return None
        return o

    def find_partner(self, oid, cands):
        A = self._single(oid)
        if not A:
            return None
        P, mins = self.p, self.ctx.minutes
        la = A["legs"][0]
        a, b = la["pickup"]["placeId"], la["delivery"]["placeId"]
        dA = mins(a, b)
        startA = max(la["pickup"]["window"]["from"], self.now + 60)
        best, best_gap = None, P["pair_gap"] + 1
        for c in cands:
            B = self._single(c)
            if not B:
                continue
            lb = B["legs"][0]
            a2, b2 = lb["pickup"]["placeId"], lb["delivery"]["placeId"]
            gap = mins(b, a2)
            if gap >= best_gap:
                continue
            dB = mins(a2, b2)
            if dA + gap + dB > P["pair_max_drive"]:
                continue
            arriveA = startA + dA
            if arriveA + 30 > A["deadline"]:
                continue
            atB = max(arriveA + gap, lb["pickup"]["window"]["from"])
            if atB > lb["pickup"]["window"]["to"] or atB + dB + 60 > B["deadline"]:
                continue
            if lb["pickup"]["privateAddress"] or la["delivery"]["privateAddress"] or la["pickup"]["privateAddress"]:
                continue
            best, best_gap = c, gap
        return best

    def post_pair(self, A, B):
        from ..desk import stops_for, without_windows, Retry
        km_of = (lambda x, y: self.ctx.km(x, y)) if self.p.get("charge_fix") else None
        stops = []
        for o in (A, B):
            stops += stops_for(o, [0], self.requests[o["id"]]["note"], Retry(), km_of)
        stops = without_windows(stops, self.now)
        aud = {"experienced": any(o["legs"][0]["car"]["premium"] for o in (A, B)), "manualLicence": False}
        fa = self.requests[A["id"]]["referenceFeeCents"]
        fb = self.requests[B["id"]]["referenceFeeCents"]
        sched = self.fee_schedule(A, 1, False)
        k = self.p["pair_disc"] * (fa + fb) / fa
        sched = [{"at": int(st["at"]), "feeCents": max(1, int(st["feeCents"] * k))} for st in sched]
        self.outbox.append({"type": "post", "stops": stops, "audience": aud, "schedule": sched})
        self.pair_of[A["id"]], self.pair_of[B["id"]] = B["id"], A["id"]
        self.count("paired")

    def repost(self, gig_id):
        """A paired gig that expired goes out again as singles."""
        action = self.posts.get(gig_id)
        orders = list(dict.fromkeys(s["orderId"] for s in action["stops"])) if action else []
        if len(orders) > 1:
            for s in action["stops"]:
                self.leg_gigs.get(s["orderId"], {}).pop(s["leg"], None)
            for oid in orders:
                o = self.orders.get(oid)
                if o and None in o["deliveredAt"]:
                    self.post(o, undelivered(o))
            self.count("pair_expired")
            return
        super().repost(gig_id)

    def withdraw(self, order_id):
        """Withdrawing a paired gig re-posts the partner order alone."""
        gigs = self.gigs_of(order_id)
        partners = {s["orderId"] for g in gigs for s in self.posts.get(g, {}).get("stops", []) if s["orderId"] != order_id}
        ok = super().withdraw(order_id)
        if ok:
            for pid in partners:
                for g in gigs:
                    for s in self.posts.get(g, {}).get("stops", []):
                        if s["orderId"] == pid:
                            self.leg_gigs.get(pid, {}).pop(s["leg"], None)
                po = self.orders.get(pid)
                if po and None in po["deliveredAt"]:
                    self.post(po, undelivered(po))
        return ok

    # ------------------------------------------------------------------ direct offers v2
    def offer_to_free_driver(self, did, place, at, gig_done):
        """Our driver just delivered at `place`. If they hold no other gig of ours, offer them the best unbooked gig
        whose first pickup is near, at the app fee (they work today, so they read offers; no raise to wait for)."""
        h = (at % DAY) / 60
        if not (7 <= h < 20):
            return
        if any(self.gig_driver.get(g) == did for g in self.booked if g != gig_done and g in self.posts):
            return
        day = at // DAY
        if self.offers_today[(did, day)] >= 3:
            return
        lic = next((x for x in self.ctx.roster if x["id"] == did), None)
        best, best_gap = None, self.p["offer2_gap"] + 1
        for gid, act in self.posts.items():
            if gid in self.booked or self.open_offers[gid] >= 3:
                continue
            st0 = act["stops"][0]
            o = self.orders.get(st0["orderId"])
            if not o or self.leg_gigs.get(o["id"], {}).get(st0["leg"]) != gid:
                continue
            if act["audience"].get("manualLicence") and (not lic or lic["licence"] != "manual"):
                continue
            if act["audience"].get("experienced") and (not lic or lic["rating"] < 4.8 or lic["completedGigs"] < 50):
                continue
            pick = o["legs"][st0["leg"]]["pickup"]["placeId"]
            gap = self.ctx.minutes(place, pick)
            if gap < best_gap and o["lastPickupAt"] > at + gap + 30:
                best, best_gap = (gid, act), gap
        if best:
            gid, act = best
            fee = max(s["feeCents"] for s in act["schedule"] if s["at"] <= at) if any(s["at"] <= at for s in act["schedule"]) else act["schedule"][0]["feeCents"]
            self.outbox.append({"type": "offer", "gigId": gid, "driverId": did, "feeCents": int(fee * self.p["offer2_f"])})
            self.offers_today[(did, day)] += 1
            self.open_offers[gid] += 1
            self.count("offer2_sent")

    # ------------------------------------------------------------------ direct offers
    def send_offers(self, order_id):
        order = self.orders.get(order_id)
        if not order:
            return
        self.send_post_of(order_id)
        gigs = [g for g in self.gigs_of(order_id) if g not in self.booked]
        if not gigs:
            return
        gig = gigs[0]
        a = order["legs"][0]["pickup"]["placeId"]
        day = self.now // DAY
        need_manual = self.posts.get(gig, {}).get("audience", {}).get("manualLicence")
        lic = {d["id"]: d for d in self.ctx.roster}

        def score(did):
            d = lic.get(did)
            if d is None or (need_manual and d["licence"] != "manual"):
                return None
            s = 0.0
            if did in self.viewers[order_id]:
                s += 3  # active today and saw it
            pos = self.driver_at.get(did)
            here = pos[0] if pos and self.now - pos[1] < 6 * HOUR else d["homePlaceId"]
            s += 2 * math.exp(-self.ctx.minutes(here, a) / 45)
            s -= 0.3 * d["drops"] / (1 + d["completedGigs"])
            return s

        cands = set(self.viewers[order_id]) | {d for d, (pl, t) in self.driver_at.items() if self.now - t < 6 * HOUR}
        cands |= {d["id"] for d in self.homes[a]}
        ranked = sorted((s, did) for did in cands if self.offers_today[(did, day)] < 3 and (s := score(did)) is not None)
        fee = int(self.requests[order_id]["referenceFeeCents"] * self.p["offer_mult"])
        n = 0
        for s, did in reversed(ranked):
            if n >= min(self.p["offer_n"], 3 - self.open_offers[gig]):
                break
            self.outbox.append({"type": "offer", "gigId": gig, "driverId": did, "feeCents": fee})
            self.offers_today[(did, day)] += 1
            self.open_offers[gig] += 1
            self.count("offers_sent")
            n += 1
