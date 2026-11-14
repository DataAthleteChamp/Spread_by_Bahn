"""First simple improvement over the starter, mainly to exercise the bench.

Ideas (each one switchable by a parameter, so the bench can measure it):
  1. Quote above list: every offered option at `mult` x list (option-specific bonus for same_day).
  2. Decline where we can't staff: pickup towns with fewer than `min_drivers` drivers living there.
  3. Fees: open at `fee_open` x typical fee, hold flat (don't teach drivers to wait), then step up
     only in the last hours before lastPickupAt.
"""
from __future__ import annotations

from ..desk import HOUR, Desk


class Markup(Desk):
    NAME = "markup"
    DEFAULTS = {
        "mult": 1.30,            # quote = mult x list price
        "same_day_mult": 1.0,    # extra factor for same_day
        "min_drivers": 3,        # decline if fewer drivers live in the pickup town (0 = never decline)
        "fee_open": 1.10,        # opening fee / typical fee
        "fee_late": 1.6,         # fee / typical fee in the last `late_h` hours before lastPickupAt
        "late_h": 5,
        "urgent_open": 1.8,      # after deadline_close
        "urgent_max": 2.6,
        "flat": 1,               # 1 = flat-then-late schedule, 0 = starter's rising ramp
    }

    def price_quote(self, request):
        pick = request["legs"][0]["pickup"]["placeId"]
        if self.ctx and self.p["min_drivers"] and self.ctx.drivers_in.get(pick, 0) < self.p["min_drivers"]:
            self.count("declined_supply")
            return self.decline(request)
        prices = {}
        for opt in request["options"]:
            m = self.p["mult"] * (self.p["same_day_mult"] if opt["kind"] == "same_day" else 1.0)
            prices[opt["kind"]] = opt["listPriceCents"] * m
        return prices

    def fee_schedule(self, order, cars, urgent):
        fee = self.requests[order["id"]]["referenceFeeCents"] * cars / len(order["legs"])
        now = self.now
        if urgent:
            lo, hi = self.p["urgent_open"], self.p["urgent_max"]
            return [{"at": now + k * 30, "feeCents": fee * (lo + (hi - lo) * k / 4)} for k in range(5)]
        if not self.p["flat"]:
            return super().fee_schedule(order, cars, urgent)
        steps = [{"at": now, "feeCents": fee * self.p["fee_open"]}]
        late_at = order["lastPickupAt"] - self.p["late_h"] * HOUR
        if late_at > now:
            steps.append({"at": late_at, "feeCents": fee * self.p["fee_late"]})
        else:
            steps[0]["feeCents"] = fee * self.p["fee_late"]
        return steps
