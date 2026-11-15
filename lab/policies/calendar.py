"""Experimental pickup-window capacity pricing; not part of FINAL.

Reserve expected driver-hours in two-hour pickup slots, including future-ready
orders and unresolved quotes. Localise the existing safety surcharge where supply
is healthy, retaining the global surcharge as projected weekly OT approaches 90%.
The supply prior and uniform allocation of flexible jobs are hypotheses, not a
driver assignment or a guarantee of feasible capacity.
"""
from __future__ import annotations

import math
from collections import defaultdict
from copy import deepcopy

from ..desk import DAY, HOUR
from ..notes import ready_time
from .econ import Econ

SLOT = 2 * HOUR


class Calendar(Econ):
    NAME = "calendar"
    DEFAULTS = {
        **Econ.DEFAULTS,
        "cal_cost_k": 0.5,
        "cal_global_share": 0.25,
        "cal_hours_per_driver": 1.0,
        "cal_radius_min": 30.0,
        "cal_reach_share": 0.05,
        "cal_overhead_min": 60,
        "cal_target": 0.8,
        "cal_reserve_ot": 0.94,
    }

    def on_start(self):
        super().on_start()
        P = self.p
        if (P["cal_cost_k"] < 0 or not 0 <= P["cal_global_share"] <= 1
                or P["cal_hours_per_driver"] <= 0 or P["cal_radius_min"] <= 0
                or P["cal_reach_share"] < 0 or P["cal_overhead_min"] <= 0
                or not 0 < P["cal_target"] < 1 or not 0.90 < P["cal_reserve_ot"] <= 1):
            raise ValueError("Invalid calendar capacity parameters")
        self.calendar_orders = {}
        self.calendar_pending = {}
        self.calendar_load = defaultdict(float)
        self.calendar_note_ready = {}
        self.calendar_overlap = {
            (a, b): 1.0 if a == b else math.exp(-self.ctx.minutes(a, b) / P["cal_radius_min"])
            for a in self.ctx.places for b in self.ctx.places
        }
        self.calendar_supply = {
            a: self.cov30[a] + P["cal_reach_share"] * self.reach[a]
            for a in self.ctx.places
        }

    def on_event(self, event):
        super().on_event(event)
        kind = event["kind"]
        if kind in ("order_won", "order_changed"):
            order = event["order"]
            self.calendar_orders[order["id"]] = deepcopy(order)
            self.calendar_pending.pop(order["id"], None)
        elif kind == "order_cancelled":
            self.calendar_orders.pop(event["orderId"], None)
            self.calendar_pending.pop(event["orderId"], None)
        elif kind == "order_lost":
            self.calendar_pending.pop(event.get("requestId") or event.get("orderId"), None)
        elif kind == "delivered":
            order = self.calendar_orders.get(event["orderId"])
            if order is not None:
                order["deliveredAt"][event["leg"]] = event["at"]
                if None not in order["deliveredAt"]:
                    del self.calendar_orders[order["id"]]

    @staticmethod
    def opening(hours, day):
        if hours is None:
            return 0, DAY
        if day % 7 in hours["weekdays"]:
            return hours["opens"], hours["closes"]
        saturday = hours.get("saturday")
        if day % 7 == 5 and saturday is not None:
            return saturday["opens"], saturday["closes"]
        return None

    def slot_weights(self, start, end, hours, carry_overdue=False):
        """Weights sum to one; an overdue obligation reserves the next open slot."""
        start = max(self.now, start)
        available = defaultdict(float)
        for day in range(start // DAY, end // DAY + 1):
            opening = self.opening(hours, day)
            if opening is None:
                continue
            lo = max(start, day * DAY + opening[0])
            hi = min(end + 1, day * DAY + opening[1])
            if hi <= lo:
                continue
            for slot in range(lo // SLOT, (hi - 1) // SLOT + 1):
                available[slot] += min(hi, (slot + 1) * SLOT) - max(lo, slot * SLOT)
        if not available and carry_overdue:
            for day in range(start // DAY, start // DAY + 8):
                opening = self.opening(hours, day)
                if opening is not None:
                    lo = max(start, day * DAY + opening[0])
                    if lo < day * DAY + opening[1]:
                        return {lo // SLOT: 1.0}
        total = sum(available.values())
        return {slot: minutes / total for slot, minutes in available.items()} if total else {}

    def allocations(self, record, deadline, carry_overdue=False):
        request = self.requests.get(record["id"], record)
        note = request.get("note")
        note_at = None
        if self.p["notes3"] and note:
            key = (note["text"], request["arrivedAt"])
            if key not in self.calendar_note_ready:
                self.calendar_note_ready[key] = ready_time(*key)
            note_at = self.calendar_note_ready[key]
        allocations = defaultdict(float)
        delivered = record.get("deliveredAt", [None] * len(record["legs"]))
        for i, leg in enumerate(record["legs"]):
            if delivered[i] is not None:
                continue
            a, b = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
            drive = self.ctx.minutes(a, b)
            start = max(leg["pickup"]["window"]["from"], note_at or 0)
            end = min(deadline - drive, leg["delivery"]["window"]["to"] - drive,
                      leg["pickup"]["window"]["to"], record.get("lastPickupAt", deadline))
            slots = self.slot_weights(start, end, leg["pickup"]["hours"], carry_overdue)
            if not slots:
                return {}
            work = (drive + self.p["cal_overhead_min"]) / HOUR
            for slot, share in slots.items():
                allocations[(a, slot)] += work * share
        return dict(allocations)

    def build_load(self, request_id):
        self.calendar_load.clear()
        self.calendar_pending = {
            rid: reservation for rid, reservation in self.calendar_pending.items()
            if reservation[0]["respondBy"] >= self.now and rid != request_id
        }
        for order in self.calendar_orders.values():
            allocation = self.allocations(order, order["deadline"], carry_overdue=True)
            if not allocation:
                raise ValueError(f"No future pickup opening for committed order {order['id']}")
            for cell, work in allocation.items():
                self.calendar_load[cell] += work
        for request, deadline, probability in self.calendar_pending.values():
            for cell, work in self.allocations(request, deadline).items():
                self.calendar_load[cell] += probability * work

    def local_booking_pressure(self, town):
        weight = booked = 0.0
        for gig, at in self.posted_at.items():
            if not self.now - 4 * HOUR <= at <= self.now - HOUR:
                continue
            oid = self.gig_order.get(gig)
            request = self.requests.get(oid)
            if request is None:
                continue
            other = request["legs"][0]["pickup"]["placeId"]
            w = self.calendar_overlap[(town, other)]
            weight += w
            accepted = self.booked_at.get(gig)
            booked += w * (accepted is not None and accepted <= at + HOUR)
        base = self.p["flu_base"]
        rate = (8 * base + booked) / (8 + weight)
        return max(0.0, min(1.0, (base - rate) / max(0.01, base * 0.5)))

    def quote_risk_terms(self, request, option):
        if self.p["cal_cost_k"] == 0 and self.p["cal_global_share"] == 1:
            return super().quote_risk_terms(request, option)
        allocation = self.allocations(request, option["deadline"])
        if not allocation:
            self.count("cal_infeasible")
            return 1 + 2 * self.mu, math.inf
        weighted_pressure = weighted_excess = total = 0.0
        for (town, slot), work in allocation.items():
            load = sum(other_work * self.calendar_overlap[(town, other)]
                       for (other, other_slot), other_work in self.calendar_load.items() if other_slot == slot)
            remaining = min(SLOT, (slot + 1) * SLOT - self.now) / SLOT
            capacity = self.calendar_supply[town] * self.p["cal_hours_per_driver"] * remaining / (12 * HOUR / SLOT)
            utilisation = (load + work) / max(0.01, capacity)
            excess = max(0.0, utilisation - self.p["cal_target"])
            weighted_excess += work * excess
            weighted_pressure += work * min(1.0, excess / (1 - self.p["cal_target"]))
            total += work
        excess, pressure = weighted_excess / total, weighted_pressure / total
        town = request["legs"][0]["pickup"]["placeId"]
        ready = max(self.now, min(slot for _, slot in allocation) * SLOT)
        pressure = max(pressure, self.local_booking_pressure(town) * math.exp(-(ready - self.now) / DAY))
        reserve = self.p["cal_reserve_ot"]
        danger = max(0.0, min(1.0, (reserve - getattr(self, "proj_ot", 1.0)) / (reserve - 0.90)))
        floor = self.p["cal_global_share"] + (1 - self.p["cal_global_share"]) * danger
        local_mu = self.mu * (floor + (1 - floor) * pressure)
        cost = self.p["cal_cost_k"] * request["referenceFeeCents"] * excess
        if cost > 0:
            self.count("cal_capacity_cost")
        if local_mu < self.mu - 1e-9:
            self.count("cal_local_relief")
        return 1 + 2 * local_mu, cost

    def price_quote(self, request):
        if self.p["cal_cost_k"] == 0 and self.p["cal_global_share"] == 1:
            return super().price_quote(request)
        self.build_load(request["id"])
        prices = super().price_quote(request)
        offered = [o for o in request["options"]
                   if o["kind"] in prices and prices[o["kind"]] < 5 * o["listPriceCents"]]
        if offered:
            town = request["legs"][0]["pickup"]["placeId"]
            probability = max(self.pwin(request["dealerId"], o["kind"],
                                       math.log(prices[o["kind"]] / o["listPriceCents"]),
                                       self.lane(request, o["kind"]) + self.theta_a[town]) for o in offered)
            # One request can win only one option; reserve against its tightest offered window.
            self.calendar_pending[request["id"]] = (request, min(o["deadline"] for o in offered), probability)
        return prices
