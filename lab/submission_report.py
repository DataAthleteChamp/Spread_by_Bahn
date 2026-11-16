"""Generate submission evidence from recorded results; no fitting or simulator actions."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import numpy as np

from .calendar_experiment import FRESH as CALENDAR_FRESH, SEEDS as CALENDAR_SEEDS, VARIANTS as CALENDAR_VARIANTS
from .calendar_experiment import journal_rows
from .concession_experiment import FRESH as CONCESSION_FRESH, SEEDS as CONCESSION_SEEDS, VARIANTS as CONCESSION_VARIANTS
from .ratio_experiment import FRESH as RATIO_FRESH, SCREEN as RATIO_SEEDS, VARIANTS as RATIO_VARIANTS, stage_report
from .runner import ROOT


def main():
    rows = journal_rows()
    frozen = json.loads((ROOT / "lab/final_config.json").read_text())
    rehearsal = json.loads((ROOT / "results/quote_audit-final0100.json").read_text())
    final_path = ROOT / "results/final-outcome.json"
    final_result = json.loads(final_path.read_text()) if final_path.exists() else None
    groups = defaultdict(dict)
    for row in rows:
        if row.get("board") and row.get("ok") and row["level"] == 8:
            groups[row["tag"]][row["world"]] = row
    boards = []
    for tag, group in groups.items():
        runs = list(group.values())
        if len(runs) == 5 and all(r["ranked"] for r in runs):
            boards.append({
                "tag": tag, "margin_eur": sum(r["margin"] for r in runs),
                "won_orders": sum(r["won"] for r in runs),
                "min_on_time": min(r["on_time"] for r in runs),
                "worlds": sorted(group),
            })
    if not boards:
        raise ValueError("No fully qualifying five-week ranking round in the journal")
    hazard = {v: {r["seed"]: r for r in rows if r.get("tag") == "sweep40" and r.get("ok") and r["variant"] == v}
              for v in ("CANDIDATE8", "CANDIDATE8:haz=1")}
    seeds = sorted(hazard["CANDIDATE8"].keys() & hazard["CANDIDATE8:haz=1"].keys())
    if not seeds:
        raise ValueError("Missing paired hazard-policy evidence")
    delta = np.array([hazard["CANDIDATE8:haz=1"][s]["margin"] - hazard["CANDIDATE8"][s]["margin"] for s in seeds])
    rng = np.random.default_rng(20261115)
    boot = delta[rng.integers(len(delta), size=(50000, len(delta)))].mean(axis=1)
    campaigns = [
        stage_report("calendar1", CALENDAR_VARIANTS, CALENDAR_SEEDS, CALENDAR_FRESH),
        stage_report("ratio1", RATIO_VARIANTS, RATIO_SEEDS, RATIO_FRESH),
        stage_report("concession1", CONCESSION_VARIANTS, CONCESSION_SEEDS, CONCESSION_FRESH),
    ]
    result = {
        "fit_window": None, "final_policy": frozen["spec"],
        "final_params_sha256": hashlib.sha256(json.dumps(frozen["overrides"], sort_keys=True).encode()).hexdigest(),
        "final_result": final_result,
        "rehearsal_0100": {"world": rehearsal["world"], "score": rehearsal["score"],
                           "exact_replayed_quotes": rehearsal["exact_quote_count"]},
        "highest_recorded_qualifying_round": max(boards, key=lambda r: r["margin_eur"]),
        "hazard_ablation": {"tag": "sweep40", "paired_development_weeks": len(seeds),
                            "profit_delta_eur": float(delta.mean()),
                            "bootstrap_95": np.quantile(boot, [.025, .975]).tolist()},
        "recent_screen_worlds": sum(r.get("tag") in ("calendar1", "ratio1", "concession1") for r in rows),
        "recent_campaigns": campaigns,
        "journal_sha256": hashlib.sha256((ROOT / "results/runs.jsonl").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256((ROOT / "lab/submission_report.py").read_bytes()).hexdigest(),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
