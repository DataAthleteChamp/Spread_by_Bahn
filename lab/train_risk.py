"""Train the staffability model P(late | request features at quote time) from saved runs (--reveal).

Usage: python -m lab.train_risk [--tag datagen1 ...]   -> writes lab/models/risk.json
Features use only what the desk knows when it quotes (see features()).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
MAP = json.load(open(ROOT / "data/map.json"))
ROAD = {(r["from"], r["to"]): r["minutes"] for r in MAP["roads"]}
OUT = ROOT / "lab" / "models" / "risk.json"


def reach_of(roster, tau=60.0):
    towns = [p["id"] for p in MAP["places"]]
    return {t: sum(math.exp(-ROAD[(d["homePlaceId"], t)] / tau) for d in roster) for t in towns}


FEATURES = ["drive_h", "drive_h2", "log_reach_a", "log_reach_b", "opt_same", "opt_w3", "hour", "late_day",
            "slack_h", "note", "legs2", "premium", "electric", "private", "weekday", "won_today_town", "won_today"]


def features(req: dict, option: dict, reach: dict, load=(0, 0)) -> list[float]:
    legs = req["legs"]
    a, b = legs[0]["pickup"]["placeId"], legs[0]["delivery"]["placeId"]
    drive = sum(ROAD[(l["pickup"]["placeId"], l["delivery"]["placeId"])] for l in legs)
    ready = max(l["pickup"]["window"]["from"] for l in legs)
    start = max(ready, req["respondBy"])
    hour = (req["arrivedAt"] % 1440) / 60
    return [drive / 60, (drive / 60) ** 2, math.log1p(reach[a]), math.log1p(reach[b]),
            float(option["kind"] == "same_day"), float(option["kind"] == "within_3_days"), hour, float(hour >= 14),
            (option["deadline"] - start - drive) / 60, float(bool(req.get("note"))), float(len(legs) == 2),
            float(any(l["car"]["premium"] for l in legs)), float(any(l["car"]["electric"] for l in legs)),
            float(any(l["pickup"]["privateAddress"] or l["delivery"]["privateAddress"] for l in legs)),
            float(req["arrivedAt"] // 1440), float(load[0]), float(load[1])]


def rows_from_run(world: str):
    d = ROOT / "data/runs" / world
    rv, ev = json.load(open(d / "reveal.json")), json.load(open(d / "events.json"))
    roster = json.load(open(d / "roster.json")) if (d / "roster.json").exists() else None
    req = {r["request"]["id"]: r["request"] for r in rv["requests"]}
    truth = {o["orderId"]: o for o in rv["orders"]}
    won = {e["order"]["id"]: e["order"] for e in ev if e["kind"] == "order_won"}
    for e in ev:
        if e["kind"] == "order_cancelled":
            won.pop(e["orderId"], None)
    return req, truth, won, roster


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", default=None)
    a = ap.parse_args()
    tags = a.tag or ["datagen1"]
    runs = [json.loads(l) for l in open(ROOT / "results/runs.jsonl")]
    runs = [r for r in runs if r.get("tag") in tags and r.get("ok") and (ROOT / "data/runs" / r["world"]).exists()]
    X, y, groups = [], [], []
    for i, r in enumerate(runs):
        req, truth, won, roster = rows_from_run(r["world"])
        if roster is None:
            print("skip (no roster saved)", r["world"]); continue
        reach = reach_of(roster)
        # load at quote time: orders won earlier the same day (per pickup town and in total)
        wins = sorted((o_["legs"][0]["pickup"]["placeId"], req[k]["arrivedAt"]) for k, o_ in won.items() if k in req)
        def load_at(r):
            day, a = r["arrivedAt"] // 1440, r["legs"][0]["pickup"]["placeId"]
            same = [t for (aa, t) in wins if t // 1440 == day and t < r["arrivedAt"]]
            return (sum(1 for (aa, t) in wins if aa == a and t // 1440 == day and t < r["arrivedAt"]), len(same))
        for oid, o in won.items():
            t = truth.get(oid)
            if not t:
                continue
            opt = next(x for x in req[oid]["options"] if x["kind"] == o["option"])
            opt = {**opt, "deadline": o["deadline"]}
            late = any(l["deliveredAt"] is None or l["deliveredAt"] > o["deadline"] for l in t["legs"])
            X.append(features(req[oid], opt, reach, load_at(req[oid]))); y.append(int(late)); groups.append(i)
    X, y, groups = np.array(X), np.array(y), np.array(groups)
    print(f"{len(runs)} runs, {len(y)} orders, late rate {y.mean():.3f}")
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    # leave-runs-out validation (worlds differ): train on 3/4 of runs, test on 1/4
    test = groups % 4 == 0
    m = LogisticRegression(C=0.5, max_iter=2000).fit(Z[~test], y[~test])
    print(f"held-out-world AUC {roc_auc_score(y[test], m.predict_proba(Z[test])[:, 1]):.3f}  (n_test={test.sum()})")
    m = LogisticRegression(C=0.5, max_iter=2000).fit(Z, y)
    coef = dict(zip(FEATURES, m.coef_[0].round(3)))
    print("standardised coefficients (+ = more late):", dict(sorted(coef.items(), key=lambda kv: -abs(kv[1]))))
    p = m.predict_proba(Z)[:, 1]
    for q in (0.05, 0.1, 0.2, 0.3):
        keep = p < q
        print(f"  keep orders with P(late)<{q:.2f}: keep {keep.mean():.0%} of orders, their late rate {y[keep].mean():.3f}")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"features": FEATURES, "mu": mu.tolist(), "sd": sd.tolist(),
                               "coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0]), "tags": tags, "n": int(len(y))}))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
