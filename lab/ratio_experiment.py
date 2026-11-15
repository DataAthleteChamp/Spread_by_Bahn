"""Bounded ratio-policy screen and conditional independent confirmation.

    python -m lab.ratio_experiment --run
    python -m lab.ratio_experiment --report

At most 240 practice weeks: four variants x 36 screening seeds, then two x 48
untouched confirmation seeds only after a promising, fully qualifying screen.
No policy is promoted. No model is fitted on either evaluation cohort.
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

from .bench import parse_variant
from .calendar_experiment import STRESS, fingerprints, journal_rows
from .runner import ROOT, load_env

TAG = "ratio1"
CONFIRM_TAG = "ratio1-confirm"
VARIANTS = ("RATIO1_BASE", "RATIO1_NO_CREDIT", "RATIO1_95", "RATIO1_925")
FRESH = tuple(f"ratio1-20261115-{i}" for i in range(24))
CONFIRM = tuple(f"ratio1v-20261115-{i}" for i in range(48))
SCREEN = STRESS + FRESH
MAX_WEEKS = 240
MIN_SCREEN_GAIN = 750.0
MARKER = ROOT / "results" / f"{TAG}.started.json"


def source_fingerprints():
    paths = ("lab/policies/ratio.py", "lab/ratio_experiment.py", "lab/quote_audit.py", "lab/bench.py")
    return {**fingerprints(), **{p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}


def stage_report(tag, variants, seeds, fresh):
    rows = [r for r in journal_rows() if r.get("tag") == tag]
    expected = {(v, s) for v in variants for s in seeds}
    actual = {(r["variant"], r["seed"]) for r in rows}
    if actual != expected or len(rows) != len(expected):
        raise RuntimeError(f"{tag}: expected {len(expected)} unique results, received {len(rows)}")
    errors = [{"variant": r["variant"], "seed": r["seed"], "error": r.get("error")}
              for r in rows if not r.get("ok")]
    by = {v: {r["seed"]: r for r in rows if r["variant"] == v and r.get("ok")} for v in variants}
    rng, output = np.random.default_rng(151102), []
    for cohort, selected in (("all", seeds), ("fresh", fresh)):
        for variant in variants:
            common = [s for s in selected if s in by[variants[0]] and s in by[variant]]
            if not common:
                raise RuntimeError(f"No paired observations for {variant}")
            base, alt = [by[variants[0]][s] for s in common], [by[variant][s] for s in common]
            delta = np.array([b["margin"] - a["margin"] for a, b in zip(base, alt)])
            bootstrap = delta[rng.integers(len(delta), size=(50000, len(delta)))].mean(axis=1)
            output.append({
                "cohort": cohort, "variant": variant, "paired_weeks": len(common),
                "mean_margin": float(np.mean([r["margin"] for r in alt])),
                "delta_margin": float(delta.mean()),
                "bootstrap_95": np.quantile(bootstrap, [.025, .975]).tolist(),
                "mean_wins": float(np.mean([r["won"] for r in alt])),
                "delta_wins": float(np.mean([b["won"] - a["won"] for a, b in zip(base, alt)])),
                "net_per_won": sum(r["margin"] for r in alt) / max(1, sum(r["won"] for r in alt)),
                "min_on_time": min(r["on_time"] for r in alt),
                "unranked": [{"seed": r["seed"], "on_time": r["on_time"], "world": r["world"]}
                             for r in alt if not r["ranked"]],
            })
    return {"tag": tag, "errors": errors, "comparisons": output}


def screen_winner(screen):
    if screen["errors"]:
        return None
    all_rows = {r["variant"]: r for r in screen["comparisons"] if r["cohort"] == "all"}
    candidates = [r for r in screen["comparisons"] if r["cohort"] == "fresh"
                  and r["variant"] != VARIANTS[0]
                  and r["paired_weeks"] == len(FRESH)
                  and r["delta_margin"] >= MIN_SCREEN_GAIN and r["bootstrap_95"][0] > 0
                  and not all_rows[r["variant"]]["unranked"]]
    return max(candidates, key=lambda r: r["delta_margin"])["variant"] if candidates else None


def run_stage(tag, variants, seeds, why, before):
    if source_fingerprints() != before:
        raise RuntimeError("Code or models changed; refusing to mix policy versions")
    final = Client().final()
    snapshot = Client().world(final["worldId"]).snapshot()
    if snapshot["now"] < snapshot["endsAt"]:
        raise RuntimeError("A live final/test is scheduled or running; campaign not started")
    subprocess.run([
        sys.executable, "-u", "-m", "lab.bench", *variants,
        "--seed-list", ",".join(seeds), "--workers", "4", "--level", "8",
        "--tag", tag, "--why", why,
    ], cwd=ROOT, env={**os.environ, "SPREAD_BATCH_MIN": "12"}, check=True)
    if source_fingerprints() != before:
        raise RuntimeError("Code or models changed during this stage; results are not frozen-policy evidence")


def report():
    screen = stage_report(TAG, VARIANTS, SCREEN, FRESH)
    winner = screen_winner(screen)
    confirmation = None
    if any(r.get("tag") == CONFIRM_TAG for r in journal_rows()):
        if winner is None:
            raise RuntimeError("Confirmation exists without a candidate passing the predefined screen")
        confirmation = stage_report(CONFIRM_TAG, (VARIANTS[0], winner), CONFIRM, CONFIRM)
    result = {"screen": screen, "screen_winner": winner, "confirmation": confirmation, "promoted": False}
    with (ROOT / "results" / f"{TAG}_report.json").open("w") as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result), flush=True)
    return result


def run():
    if len(VARIANTS) * len(SCREEN) + 2 * len(CONFIRM) != MAX_WEEKS:
        raise RuntimeError("Campaign exceeds the approved limit")
    rows = journal_rows()
    if any(r.get("tag") in (TAG, CONFIRM_TAG) for r in rows):
        raise RuntimeError("Campaign already started; use --report, not another --run")
    if set(FRESH + CONFIRM) & {r.get("seed") for r in rows}:
        raise RuntimeError("An evaluation seed has already been used")
    baseline = json.loads((ROOT / "lab/final_config.json").read_text())["overrides"]
    if parse_variant(VARIANTS[0])[2] != baseline or parse_variant("FINAL")[2] != baseline:
        raise RuntimeError("Baseline is not the frozen FINAL")
    variants = [parse_variant(v) for v in VARIANTS]
    before = source_fingerprints()
    manifest = {
        "tag": TAG, "max_weeks": MAX_WEEKS, "screen_stress": STRESS, "screen_fresh": FRESH,
        "confirmation_seeds": CONFIRM, "fit_window": None,
        "screen_gate": {"min_fresh_delta_eur": MIN_SCREEN_GAIN, "positive_bootstrap_lower_bound": True,
                        "max_qualification_failures": 0},
        "source_and_model_sha256": before,
        "variants": {name: {"policy": cls.NAME, "params": params} for name, cls, params in variants},
    }
    with MARKER.open("x") as output:
        json.dump(manifest, output, indent=2)
    print(json.dumps(manifest), flush=True)
    load_env()
    run_stage(TAG, VARIANTS, SCREEN,
              "Ratio-aware SLA objective versus frozen FINAL and a no-credit control. Fixed economic "
              "late-cost 0.6 and safety value 50..300 EUR/miss; credits 0/5/7.5 percentage points. "
              "12 stress + 24 unseen screening weeks; not a qualification guarantee.", before)
    screen = stage_report(TAG, VARIANTS, SCREEN, FRESH)
    print(json.dumps(screen), flush=True)
    winner = screen_winner(screen)
    if winner:
        run_stage(CONFIRM_TAG, (VARIANTS[0], winner), CONFIRM,
                  "Untouched confirmation of the preselected ratio-policy winner versus frozen FINAL. "
                  "No fitting or retuning after screening; no automatic promotion.", before)
    else:
        print("Screen failed the predefined gain/safety gate; stopping after 144 weeks.", flush=True)
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
