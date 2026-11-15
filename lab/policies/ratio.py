"""Experimental Lagrangian pricing for a delivery-share constraint.

For a won order, expected constraint consumption is P(late) - allowed_miss_rate.
The safety controller sets the value of this consumption; refunds remain a
separate price-dependent cost. This expected-risk relaxation is not a chance
constraint and does not account for correlated shocks or guarantee qualification.
"""
from __future__ import annotations

from .econ import Econ


class Ratio(Econ):
    NAME = "ratio"
    DEFAULTS = {
        **Econ.DEFAULTS,
        "ratio_allowance": 0.05,
        "ratio_value_min": 50.0,
        "ratio_value_max": 300.0,
    }

    def on_start(self):
        super().on_start()
        if (not 0 <= self.p["ratio_allowance"] <= 0.1
                or not 0 <= self.p["ratio_value_min"] <= self.p["ratio_value_max"]
                or self.p["mu_max"] <= 0):
            raise ValueError("Invalid ratio-policy allowance or safety value")
        if self.p["dilute"]:
            raise ValueError("Disable dilute: the ratio credit replaces the emergency win bonus")

    def quote_risk_terms(self, request, option):
        return 1.0, 0.0

    def quote_sla_cost(self, request, option, pl, risk_mult, relief):
        pressure = min(1.0, max(0.0, self.mu / self.p["mu_max"]))
        value = self.p["ratio_value_min"] + pressure * (self.p["ratio_value_max"] - self.p["ratio_value_min"])
        cost = 100 * value * (pl - self.p["ratio_allowance"])
        self.count("ratio_credit" if cost < 0 else "ratio_penalty")
        return cost
