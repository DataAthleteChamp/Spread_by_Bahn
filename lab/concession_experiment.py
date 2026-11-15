"""Level-8 practice-only comparison: FINAL and two selective-concession profiles.

    python -m lab.concession_experiment --run
    python -m lab.concession_experiment --report

Runs at most 108 worlds: 12 known stress seeds and 24 previously unseen seeds
for each of three policies. Thresholds are fixed before the experiment; no
fitting, ranking submissions, automatic reruns or promotion are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

from spread.client import Client

from .bench import parse_variant
from .calendar_experiment import STRESS as PRIOR_STRESS, journal_rows
from .ratio_experiment import source_fingerprints as prior_fingerprints, stage_report
from .runner import ROOT, load_env

TAG = "concession1"
VARIANTS = ("CONC1_BASE", "CONC1_TIGHT", "CONC1_WIDE")
STRESS = PRIOR_STRESS[:-1] + ("ratio1-20261115-16",)
FRESH = tuple(f"concession1-20261115-{i}" for i in range(24))
SEEDS = STRESS + FRESH
MAX_WEEKS = 108
MARKER = ROOT / "results" / f"{TAG}.started.json"


def source_fingerprints():
    paths = ("lab/policies/concession.py", "lab/concession_experiment.py", "lab/final_config.json")
    return {**prior_fingerprints(), **{p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}


def report():
    result = stage_report(TAG, VARIANTS, SEEDS, FRESH)
    result["promoted"] = False
    with (ROOT / "results" / f"{TAG}_report.json").open("w") as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result), flush=True)
    if result["errors"]:
        raise RuntimeError("Some L8 runs failed; successful pairs are not a complete comparison")
    return result


def run():
    if len(SEEDS) * len(VARIANTS) != MAX_WEEKS:
        raise RuntimeError("The experiment exceeds its run limit")
    rows = journal_rows()
    if any(r.get("tag") == TAG for r in rows) or MARKER.exists():
        raise RuntimeError("Campaign already started; use --report, not --run")
    if set(FRESH) & {r.get("seed") for r in rows}:
        raise RuntimeError("A supposedly fresh seed has already been used")
    baseline = json.loads((ROOT / "lab/final_config.json").read_text())["overrides"]
    if parse_variant("FINAL")[2] != baseline or parse_variant(VARIANTS[0])[2] != baseline:
        raise RuntimeError("Baseline is not the frozen FINAL")
    load_env()
    client = Client()
    final = client.final()
    snapshot = client.world(final["worldId"]).snapshot()
    if snapshot["now"] < snapshot["endsAt"]:
        raise RuntimeError("A live final/test is scheduled or running; practice comparison not started")
    before = source_fingerprints()
    variants = [parse_variant(v) for v in VARIANTS]
    manifest = {
        "tag": TAG, "level": 8, "max_weeks": MAX_WEEKS, "fit_window": None,
        "stress": STRESS, "fresh": FRESH, "source_and_model_sha256": before,
        "variants": {name: {"policy": cls.NAME, "params": params} for name, cls, params in variants},
    }
    with MARKER.open("x") as output:
        json.dump(manifest, output, indent=2)
    print(json.dumps(manifest), flush=True)
    subprocess.run([
        sys.executable, "-u", "-m", "lab.bench", *VARIANTS,
        "--seed-list", ",".join(SEEDS), "--level", "8", "--workers", "4", "--tag", TAG,
        "--why", "Selective concessions on low-risk marginal opportunities. Preserve predicted likely-win "
        "menus; require positive execution margin and expected incremental value after charging discounts "
        "to already-expected wins. Tight versus wide profiles; 12 stress + 24 unseen seeds. FINAL unchanged.",
    ], cwd=ROOT, env={**os.environ, "SPREAD_BATCH_MIN": "12"}, check=True)
    if source_fingerprints() != before:
        raise RuntimeError("Code/models changed during the campaign; this is not a frozen-policy comparison")
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
