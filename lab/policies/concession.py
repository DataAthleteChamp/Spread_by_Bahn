"""Experimental concessions on feasible marginal opportunities, not likely wins.

Start from the unchanged Econ menu. A concession must improve estimated cash
contribution after charging for margin lost on already-expected wins. Only one
offered option can change; risk exclusions and the other quoted prices remain.
Win probabilities and execution costs are estimates, not counterfactual truth.
"""
from __future__ import annotations

import math

from .econ import GRID, Econ


class Concession(Econ):
    NAME = "concession"
    DEFAULTS = {
        **Econ.DEFAULTS,
        "concession_max_discount": 0.075,
        "concession_min_pwin": 0.1,
        "concession_max_pwin": 0.45,
        "concession_max_late": 0.04,
        "concession_min_ot": 0.955,
        "concession_loss": 0.6,
        "concession_min_margin": 8.0,
        "concession_min_gain": 0.5,
    }

    def on_start(self):
        super().on_start()
        P = self.p
        values = [v for k, v in P.items() if k.startswith("concession_")]
        if (not all(math.isfinite(v) for v in values)
                or not 0 <= P["concession_max_discount"] <= 0.25
                or not 0 <= P["concession_min_pwin"] < P["concession_max_pwin"] <= 1
                or not 0 < P["concession_max_late"] <= 0.1
                or not 0.90 < P["concession_min_ot"] <= 1
                or min(P["concession_loss"], P["concession_min_margin"], P["concession_min_gain"]) < 0):
            raise ValueError("Invalid selective-concession parameters")
        incompatible = ("adaptive", "pulse", "seg_fee", "opt_fee", "long_relief", "outage",
                        "snow", "sd_prem", "fri_sd", "protect", "peak", "inv_k", "adapt_k")
        enabled = [k for k in incompatible if P[k]]
        if enabled or self.risk_model is None:
            raise ValueError(f"Concessions require a risk model and unmodified base pricing terms; incompatible: {enabled}")

    @staticmethod
    def incremental_value(old_probability, new_probability, old_margin, new_margin):
        # Charge all already-expected wins for any reduction in per-order margin.
        return (new_probability - old_probability) * new_margin - old_probability * max(0.0, old_margin - new_margin)

    def price_quote(self, request):
        prices = super().price_quote(request)
        P = self.p
        if not P["concession_max_discount"]:
            return prices
        if getattr(self, "proj_ot", 1.0) < P["concession_min_ot"]:
            self.count("concession_sla_skip")
            return prices
        offered = [o for o in request["options"]
                   if o["kind"] in prices and prices[o["kind"]] < 5 * o["listPriceCents"]]
        if not offered:
            return prices
        town, dealer = request["legs"][0]["pickup"]["placeId"], request["dealerId"]
        probabilities, margins, risks, lanes, fees = {}, {}, {}, {}, {}
        base_fee = self.quote_base_fee(request)
        for option in offered:
            kind = option["kind"]
            price = max(1, int(round(prices[kind])))
            pl = self.pl_of[(request["id"], kind)]
            lane = self.lane(request, kind) + self.theta_a[town]
            fee = self.quote_execution_fee(base_fee, pl, 1.0)
            probabilities[kind] = self.pwin(dealer, kind, math.log(price / option["listPriceCents"]), lane)
            margins[kind] = price * (1 - pl * P["concession_loss"]) - fee
            risks[kind], lanes[kind], fees[kind] = pl, lane, fee
        old_probability = max(probabilities.values())
        if not P["concession_min_pwin"] <= old_probability < P["concession_max_pwin"]:
            self.count("concession_probability_skip")
            return prices
        # The best existing option's contribution is a conservative hurdle for changing the menu.
        old_margin = max(margins.values())
        best_gain, best = P["concession_min_gain"] * 100, None
        for option in offered:
            kind, listed = option["kind"], option["listPriceCents"]
            if risks[kind] > P["concession_max_late"]:
                self.count("concession_risk_skip")
                continue
            original = max(1, int(round(prices[kind])))
            for ratio in GRID:
                price = max(1, int(round(ratio * listed)))
                if not original * (1 - P["concession_max_discount"]) <= price < original:
                    continue
                margin = price * (1 - risks[kind] * P["concession_loss"]) - fees[kind]
                if margin < 100 * P["concession_min_margin"]:
                    continue
                probability = self.pwin(dealer, kind, math.log(price / listed), lanes[kind])
                if probability <= old_probability:
                    continue
                gain = self.incremental_value(old_probability, probability, old_margin, margin)
                if gain > best_gain:
                    best_gain, best = gain, (kind, price, original)
        if best is None:
            self.count("concession_no_gain")
            return prices
        kind, price, original = best
        prices[kind] = price
        # Learning must use the submitted menu, not the baseline menu that was just amended.
        saved_dealer, _, saved_lanes, saved_town = self.pending[request["id"]]
        listed = {o["kind"]: o["listPriceCents"] for o in offered}
        quotes = [(k, math.log(max(1, int(round(v))) / listed[k])) for k, v in prices.items()]
        self.pending[request["id"]] = saved_dealer, quotes, saved_lanes, saved_town
        self.count("concession_changed")
        self.count("concession_quote_cut_cents", original - price)
        self.count("concession_predicted_gain_cents", int(round(best_gain)))
        return prices
