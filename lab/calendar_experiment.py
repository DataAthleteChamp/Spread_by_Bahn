"""Bounded, reproducible calendar-policy experiment. Does not promote a policy.

    python -m lab.calendar_experiment --run
    python -m lab.calendar_experiment --report

No model is fitted here. The capacity prior is fixed before these 24 unseen seeds;
the 12 named stress seeds are development cases, not an unbiased reliability set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from spread.client import Client

from .bench import RESULTS, parse_variant
from .runner import ROOT, load_env

TAG = "calendar1"
VARIANTS = ("CAL1_BASE", "CAL1_WINDOWS", "CAL1_LOCAL", "CAL1_BOTH")
STRESS = ("c15-25", "c17-52", "lr40-4", "s22-7", "s23-3", "s25-2",
          "s26-3", "s28-9", "s30-4", "s35-6", "val-8", "val-9")
FRESH = tuple(f"cal1-20261115-{i}" for i in range(24))
SEEDS = STRESS + FRESH
MAX_WEEKS = 144


def journal_rows():
    return [json.loads(line) for line in RESULTS.read_text().splitlines()]


def fingerprints():
    paths = [
        "lab/calendar_experiment.py", "lab/policies/__init__.py",
        "lab/policies/calendar.py", "lab/policies/econ.py", "lab/policies/smart.py",
        "lab/desk.py", "lab/notes.py", "lab/train_risk.py", "lab/runner.py",
        "lab/models/risk_v3.json", "lab/models/win.json",
        "lab/models/hazard.json", "lab/models/ref.json", "data/map.json",
    ]
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def report():
    rows = [r for r in journal_rows() if r.get("tag") == TAG]
    if len(rows) != MAX_WEEKS or len({(r["variant"], r["seed"]) for r in rows}) != MAX_WEEKS:
        raise RuntimeError(f"Expected exactly {MAX_WEEKS} distinct results, found {len(rows)}; do not rerun the campaign")
    failed = [r for r in rows if not r.get("ok")]
    for r in failed:
        print("RUN ERROR", r["variant"], r["seed"], r.get("error"))
    by = {v: {r["seed"]: r for r in rows if r["variant"] == v and r.get("ok")} for v in VARIANTS}
    rng = np.random.default_rng(151101)
    for cohort, seeds in (("all", SEEDS), ("fresh", FRESH)):
        for variant in VARIANTS:
            common = [s for s in seeds if s in by[VARIANTS[0]] and s in by[variant]]
            if not common:
                raise RuntimeError(f"No paired results for {variant}, {cohort}")
            base = [by[VARIANTS[0]][s] for s in common]
            alt = [by[variant][s] for s in common]
            delta = np.array([b["margin"] - a["margin"] for a, b in zip(base, alt)])
            boot = delta[rng.integers(len(delta), size=(50000, len(delta)))].mean(axis=1)
            print(json.dumps({
                "cohort": cohort, "variant": variant, "paired_weeks": len(common),
                "mean_margin": float(np.mean([r["margin"] for r in alt])),
                "delta_margin": float(delta.mean()),
                "paired_bootstrap_95": np.quantile(boot, [.025, .975]).tolist(),
                "mean_wins": float(np.mean([r["won"] for r in alt])),
                "delta_wins": float(np.mean([b["won"] - a["won"] for a, b in zip(base, alt)])),
                "min_on_time": min(r["on_time"] for r in alt),
                "unranked": [{"seed": r["seed"], "on_time": r["on_time"], "world": r["world"]}
                             for r in alt if not r["ranked"]],
            }), flush=True)
    if failed:
        raise RuntimeError(f"{len(failed)} simulator runs failed; the paired subsets are not a complete validation")


def run():
    if len(SEEDS) * len(VARIANTS) != MAX_WEEKS:
        raise RuntimeError("Experiment exceeds the approved run count")
    rows = journal_rows()
    if any(r.get("tag") == TAG for r in rows):
        raise RuntimeError("This campaign has already started; use --report, not another --run")
    if set(FRESH) & {r.get("seed") for r in rows}:
        raise RuntimeError("A supposedly unseen seed has already been used")
    baseline = json.loads((ROOT / "lab/final_config.json").read_text())["overrides"]
    variants = [parse_variant(v) for v in VARIANTS]
    if variants[0][2] != baseline:
        raise RuntimeError("Baseline no longer matches the frozen FINAL configuration")
    load_env()
    client = Client()
    final = client.final()
    snapshot = client.world(final["worldId"]).snapshot()
    if snapshot["now"] < snapshot["endsAt"]:
        raise RuntimeError("The live final/test has not ended; practice campaign was not started")
    before = fingerprints()
    manifest = {
        "tag": TAG, "max_weeks": MAX_WEEKS, "stress": STRESS, "fresh": FRESH,
        "fitted_on": None, "source_and_model_sha256": before,
        "variants": {label: {"policy": cls.NAME, "params": params} for label, cls, params in variants},
    }
    marker = ROOT / "results" / f"{TAG}.started.json"
    with marker.open("x") as output:
        json.dump(manifest, output, indent=2)
    print(json.dumps(manifest), flush=True)
    subprocess.run([
        sys.executable, "-m", "lab.bench", *VARIANTS,
        "--seed-list", ",".join(SEEDS), "--level", "8", "--workers", "4",
        "--tag", TAG, "--why",
        "2x2 ablation: future pickup-window capacity cost and localised safety throttle. "
        "Frozen FINAL baseline; 12 development stress seeds + 24 untouched seeds; "
        "no promotion, max 144 practice worlds. Supply prior is a hypothesis, not fitted.",
    ], cwd=ROOT, env={**os.environ, "SPREAD_BATCH_MIN": "12"}, check=True)
    if fingerprints() != before:
        raise RuntimeError("Code/models changed during the campaign; do not treat results as a frozen-policy comparison")
    report()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    run() if args.run else report()


if __name__ == "__main__":
    main()
