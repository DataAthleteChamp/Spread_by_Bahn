"""Decompose realised paired-week profit into retained, lost and additional orders.

    python -m lab.paired_economics --tag ratio1 --baseline RATIO1_BASE \
        --variant RATIO1_95 --seed-prefix ratio1-20261115-

Reads only ended non-ranking practice worlds. This is an accounting identity,
not a causal estimate of changing one price with everything else held fixed:
the competitor, drivers, chosen options and execution timing can all change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter

from spread.client import Client

from .calendar_experiment import journal_rows
from .runner import ROOT, load_env


def read_world(client, world_id, metadata):
    meta = metadata[world_id]
    if meta["kind"] != "practice" or not meta["ended"] or meta["season"] is not None or meta["boardRun"] is not None:
        raise ValueError(f"{world_id} is not an ended non-ranking practice world")
    world = client.world(world_id)
    snapshot, events, score = world.snapshot(), world.events(), world.score()
    if snapshot["now"] < snapshot["endsAt"]:
        raise ValueError(f"{world_id} has not ended")
    if events and [e["seq"] for e in events] != list(range(events[-1]["seq"] + 1)):
        raise ValueError(f"Incomplete events in {world_id}")
    orders = {o["id"]: o for o in snapshot["orders"] if o["status"] != "cancelled"}
    ledger, net, revenue, fees = Counter(), Counter(), Counter(), Counter()
    for event in events:
        if event["kind"] != "ledger":
            continue
        line = event["line"]
        ledger[line["kind"]] += line["cents"]
        oid = line.get("orderId")
        if oid:
            net[oid] += line["cents"]
            if line["kind"] == "revenue":
                revenue[oid] += line["cents"]
            elif line["kind"] == "driver_fee":
                fees[oid] -= line["cents"]
    if sum(ledger.values()) != score["marginCents"] or len(orders) != score["wonOrders"]:
        raise ValueError(f"Ledger/score mismatch in {world_id}")
    return {
        "orders": orders, "net": net, "revenue": revenue, "fees": fees,
        "margin": score["marginCents"],
        "other": score["marginCents"] - sum(net[oid] for oid in orders),
    }


def analyse(tag, baseline, variant, prefix):
    rows = [r for r in journal_rows() if r.get("tag") == tag and r.get("ok") and r["seed"].startswith(prefix)]
    a = {r["seed"]: r for r in rows if r["variant"] == baseline}
    b = {r["seed"]: r for r in rows if r["variant"] == variant}
    if not a or a.keys() != b.keys():
        raise ValueError("Both policies need the same non-empty completed seed set")
    load_env()
    client = Client()
    metadata = {w["worldId"]: w for w in client.worlds()}
    totals, worlds = Counter(), []
    for seed in sorted(a):
        left, right = read_world(client, a[seed]["world"], metadata), read_world(client, b[seed]["world"], metadata)
        common = left["orders"].keys() & right["orders"].keys()
        removed = left["orders"].keys() - right["orders"].keys()
        added = right["orders"].keys() - left["orders"].keys()
        same_option = [oid for oid in common if left["orders"][oid]["option"] == right["orders"][oid]["option"]]
        row = {
            "common_orders": len(common), "removed_orders": len(removed), "added_orders": len(added),
            "common_option_changes": len(common) - len(same_option),
            "common_revenue_delta": sum(right["revenue"][o] - left["revenue"][o] for o in common),
            "common_fee_delta": sum(right["fees"][o] - left["fees"][o] for o in common),
            "common_net_delta": sum(right["net"][o] - left["net"][o] for o in common),
            "same_option_quote_delta": sum(right["orders"][o]["priceCents"] - left["orders"][o]["priceCents"] for o in same_option),
            "removed_net": sum(left["net"][o] for o in removed),
            "added_net": sum(right["net"][o] for o in added),
            "added_revenue": sum(right["revenue"][o] for o in added),
            "added_fees": sum(right["fees"][o] for o in added),
            "other_net_delta": right["other"] - left["other"],
            "total_net_delta": right["margin"] - left["margin"],
        }
        expected = row["common_net_delta"] - row["removed_net"] + row["added_net"] + row["other_net_delta"]
        if expected != row["total_net_delta"]:
            raise ValueError(f"Accounting decomposition failed on {seed}")
        totals.update(row)
        worlds.append({"seed": seed, "baseline_world": a[seed]["world"], "variant_world": b[seed]["world"]})
    counts = {"common_orders", "removed_orders", "added_orders", "common_option_changes"}
    averages = {k: v / len(a) / (1 if k in counts else 100) for k, v in totals.items()}
    return {
        "tag": tag, "baseline": baseline, "variant": variant, "fit_window": None,
        "paired_weeks": len(a), "worlds": worlds, "average_per_week_counts_or_euros": averages,
        "script_sha256": hashlib.sha256((ROOT / "lab/paired_economics.py").read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--seed-prefix", required=True)
    args = parser.parse_args()
    print(json.dumps(analyse(args.tag, args.baseline, args.variant, args.seed_prefix), indent=2))


if __name__ == "__main__":
    main()
