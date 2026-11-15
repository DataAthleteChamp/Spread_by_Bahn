"""Reconstruct quotes from an ended world's own history, without sending actions.

    python -m lab.quote_audit --world WORLD_ID --variant FINAL

Only an exact match to all recorded quotes validates this reconstruction. Gigs
are introduced at their actual posting times; the final replacement schedule is
not treated as the opening schedule. No counterfactual profit is estimated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy

from spread.client import Client

from .bench import parse_variant
from .desk import DAY, Context
from .runner import ROOT, load_env, world_map


class NoActions:
    def __getattr__(self, name):
        raise AssertionError(f"Read-only quote reconstruction attempted world access: {name}")


def audit(world_id, variant):
    load_env()
    client = Client()
    metadata = next((w for w in client.worlds() if w["worldId"] == world_id), None)
    if metadata is None or not metadata["ended"] or metadata["season"] is not None or metadata["boardRun"] is not None:
        raise ValueError("Quote audit requires an ended, non-ranking world owned by this team")
    world = client.world(world_id)
    snapshot, events = world.snapshot(), world.events()
    if snapshot["now"] < snapshot["endsAt"]:
        raise ValueError("World has not ended")
    if events and [e["seq"] for e in events] != list(range(events[-1]["seq"] + 1)):
        raise ValueError("Incomplete event history")
    reveal, score = world.reveal(), world.score()
    recorded = {r["request"]["id"]: r for r in reveal["requests"]}
    _, cls, params = parse_variant(variant)
    trace = []

    class Audit(cls):
        def send(self):
            self.outbox.clear()

        def post(self, *args, **kwargs):
            pass

        def price_quote(self, request):
            prices = super().price_quote(request)
            actual = recorded[request["id"]]
            rounded = {k: max(1, int(round(v))) for k, v in prices.items()}
            options = []
            for option in request["options"]:
                kind = option["kind"]
                if kind not in prices or prices[kind] >= 5 * option["listPriceCents"]:
                    continue
                town = request["legs"][0]["pickup"]["placeId"]
                probability = self.pwin(request["dealerId"], kind,
                                        math.log(prices[kind] / option["listPriceCents"]),
                                        self.lane(request, kind) + self.theta_a[town])
                options.append({"kind": kind, "p_late": self.pl_of[(request["id"], kind)], "p_win": probability})
            trace.append({
                "request": request["id"], "day": request["arrivedAt"] // DAY,
                "mu": self.mu, "projected_ot": getattr(self, "proj_ot", 1.0),
                "match": rounded == actual["quote"], "outcome": actual["outcome"], "options": options,
            })
            return prices

    desk = Audit(NoActions(), 8, 0, Context(world_map(client), world.roster()), params)
    desk.on_start()
    gigs = sorted(snapshot["gigs"], key=lambda g: (g["postedAt"], int(g["id"][1:])))
    index = 0
    for event in events:
        desk.now = event["at"]
        while index < len(gigs) and gigs[index]["postedAt"] <= event["at"]:
            gig = gigs[index]
            desk.carry({"type": "post", "stops": gig["stops"], "audience": gig["audience"],
                        "schedule": gig["schedule"]}, gig["id"])
            desk.posted_at[gig["id"]] = gig["postedAt"]
            index += 1
        desk.handle(deepcopy(event))
        desk.tick()
        desk.outbox.clear()
    mismatches = [r["request"] for r in trace if not r["match"]]
    if len(trace) != len(recorded) or mismatches:
        raise RuntimeError(f"Quote reconstruction is not exact: {len(trace)}/{len(recorded)} requests, "
                           f"mismatches {mismatches[:10]}; do not use reconstructed policy state")
    days = []
    for day in sorted({r["day"] for r in trace}):
        rows = [r for r in trace if r["day"] == day]
        offered = [r for r in rows if r["options"]]
        days.append({
            "day": day, "requests": len(rows), "real_quotes": len(offered),
            "gross_wins": sum(r["outcome"] == "won" for r in rows),
            "mean_mu": sum(r["mu"] for r in rows) / len(rows),
            "saturated_share": sum(r["mu"] >= desk.p["mu_max"] - 0.01 for r in rows) / len(rows),
            "mean_projected_ot": sum(r["projected_ot"] for r in rows) / len(rows),
            "sum_max_option_pwin": sum(max(o["p_win"] for o in r["options"]) for r in offered),
        })
    return {
        "world": world_id, "variant": variant, "params": params,
        "params_sha256": hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest(),
        "source_and_model_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ("lab/quote_audit.py", "lab/policies/econ.py", "lab/policies/smart.py",
                         "lab/desk.py", "lab/notes.py", "lab/train_risk.py", "lab/models/risk_v3.json",
                         "lab/models/win.json", "lab/models/hazard.json", "lab/models/ref.json")
        },
        "fit_window": None, "events_sha256": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(),
        "exact_quote_count": len(trace), "score": score, "days": days,
        "dilution_bonus_count": desk.stats.get("dil_bonus", 0),
        "counterfactual_profit": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--variant", default="FINAL")
    args = parser.parse_args()
    print(json.dumps(audit(args.world, args.variant), indent=2))


if __name__ == "__main__":
    main()
