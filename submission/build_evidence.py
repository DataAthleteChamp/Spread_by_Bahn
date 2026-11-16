"""Build slide evidence from recorded paired L8 runs. No fitting or API actions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "results/runs.jsonl"


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(rows):
    return {
        "weeks": len(rows),
        "margin_eur_per_week": float(np.mean([r["margin"] for r in rows])),
        "mean_week_on_time": float(np.mean([r["on_time"] for r in rows])),
        "pooled_on_time": sum(round(r["on_time"] * r["won"]) for r in rows) / sum(r["won"] for r in rows),
        "min_on_time": min(r["on_time"] for r in rows),
        "wins_per_week": float(np.mean([r["won"] for r in rows])),
        "qualified_weeks": sum(r["ranked"] for r in rows),
    }


def paired(rows, identifier, tag, before, after, cohort, select=lambda seed: True):
    def index(variant):
        result = {}
        for row in rows:
            if row.get("tag") != tag or row.get("variant") != variant or not row.get("ok"):
                continue
            if row["level"] != 8:
                raise ValueError(f"{identifier}: non-L8 result")
            if row["seed"] in result:
                raise ValueError(f"{identifier}: duplicated seed {row['seed']}")
            result[row["seed"]] = row
        return result

    a, b = index(before), index(after)
    seeds = sorted(s for s in a.keys() & b.keys() if select(s))
    if not seeds:
        raise ValueError(f"{identifier}: no common completed seeds")
    left, right = [a[s] for s in seeds], [b[s] for s in seeds]
    delta_margin = np.array([b[s]["margin"] - a[s]["margin"] for s in seeds])
    delta_ot = np.array([100 * (b[s]["on_time"] - a[s]["on_time"]) for s in seeds])
    seed = int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(seeds), size=(50000, len(seeds))) if len(seeds) > 1 else None
    return {
        "id": identifier, "tag": tag, "cohort": cohort, "seeds": seeds,
        "before_variant": before, "after_variant": after,
        "before": summary(left), "after": summary(right),
        "margin_delta_eur": float(delta_margin.mean()),
        "margin_delta_95": np.quantile(delta_margin[indices].mean(axis=1), [.025, .975]).tolist() if indices is not None else None,
        "on_time_delta_pp": float(delta_ot.mean()),
        "on_time_delta_95": np.quantile(delta_ot[indices].mean(axis=1), [.025, .975]).tolist() if indices is not None else None,
        "world_pairs": [{"seed": s, "before": a[s]["world"], "after": b[s]["world"]} for s in seeds],
        "before_params": left[0]["params"], "after_params": right[0]["params"],
    }


def build():
    rows = [json.loads(line) for line in JOURNAL.read_text().splitlines()]
    experiments = [
        paired(rows, "pricing", "sweep40", "CANDIDATE8", "CANDIDATE8:mu_eur=25,risk_hard=0.6",
               "24 paired development weeks: 12 historical stress + 12 new"),
        paired(rows, "hiring", "sweep40", "CANDIDATE8", "CANDIDATE8:haz=1",
               "The same 24 paired development weeks as pricing"),
        paired(rows, "combined", "sweep40", "CANDIDATE8", "CANDIDATE8:mu_eur=25,risk_hard=0.6,haz=1",
               "Same 24 weeks; interaction check, not the sum of standalone effects"),
        paired(rows, "denoising", "c14val", "FINAL", "FINAL:ref_w=0",
               "53 paired weeks: 40 new + 13 historical stress; FINAL label here means the historical FINAL13"),
        paired(rows, "denoising_fresh", "c14val", "FINAL", "FINAL:ref_w=0",
               "40 new c14-* weeks, excluding the 13 stress weeks", lambda s: s.startswith("c14-")),
        paired(rows, "safety", "dil2", "FINAL", "FINAL:dilute=1",
               "63 common completed weeks; one baseline server failure excluded; historical FINAL14 baseline"),
        paired(rows, "safety_stress", "dil2", "FINAL", "FINAL:dilute=1",
               "One named development stress case; not a population estimate", lambda s: s == "c15-25"),
        paired(rows, "volume", "ratio1", "RATIO1_BASE", "RATIO1_95",
               "24 previously unseen screening weeks; failed confirmation gate", lambda s: s.startswith("ratio1-20261115-")),
        paired(rows, "pairing", "struct1", "FINAL", "FINAL:pair=1,batch_min=60,pair_gap=75",
               "24 paired stress/development weeks; historical FINAL13 baseline"),
    ]
    by_id = {item["id"]: item for item in experiments}
    assert by_id["denoising_fresh"]["before"]["weeks"] == 40
    assert by_id["safety"]["before"]["weeks"] == 63
    assert by_id["volume"]["before"]["weeks"] == 24
    prior = json.loads((ROOT / "results/submission-report.json").read_text())
    risk = json.loads((ROOT / "lab/models/risk_v3.json").read_text())
    hazard = json.loads((ROOT / "lab/models/hazard.json").read_text())
    ref = json.loads((ROOT / "lab/models/ref.json").read_text())
    practice = {r["world"]: r for r in rows if r.get("ok") and r.get("level") == 8
                and not r.get("board") and r.get("seed") != "board"}
    runtime_result = ROOT / "results/final-runtime/result.json"
    official_result = ROOT / "results/final-outcome.json"
    final_result = json.loads(official_result.read_text()) if official_result.exists() else None
    if final_result is None and runtime_result.exists():
        candidate = json.loads(runtime_result.read_text())
        if candidate["world"] == prior["rehearsal_0100"]["world"]:
            raise ValueError("The previous rehearsal cannot be relabelled as the final")
        final_result = {"world": candidate["world"], "score": candidate["score"],
                        "completed_at": candidate["completed_at"]}
    if final_result is not None and final_result["world"] == prior["rehearsal_0100"]["world"]:
        raise ValueError("A rehearsal cannot be presented as the official final")
    return {
        "fit_window": None, "models_fitted": False,
        "method": "Seed-matched, complete-world comparisons; 50,000 paired percentile-bootstrap samples. "
                  "On-time table values are unweighted means over matched weeks. Development CIs are not "
                  "independent production guarantees; historical runs do not all have per-run source fingerprints.",
        "experiments": by_id,
        "rehearsal": prior["rehearsal_0100"],
        "highest_qualifying_round": prior["highest_recorded_qualifying_round"],
        "final_result": final_result,
        "scale": {
            "recorded_completed_l8_practice_worlds": len(practice),
            "distinct_seed_labels": len({r["seed"] for r in practice.values()}),
            "risk_features": len(risk["features"]), "risk_training_orders": risk["n"],
            "risk_training_tags": risk["tags"],
            "hazard_exposure_rows": hazard["n"]["n_rows"],
            "hazard_spells": hazard["n"]["n_spells"],
            "hazard_period_minutes": hazard["period_min"],
            "reference_lane_cells": len(ref["lane"]),
            "reference_observations": sum(ref["n"].values()), "reference_log_noise_sd": ref["noise_sd"],
            "note": "Seed labels are reused across policies. Exposure intervals are not independent orders. "
                    "These are simulator/model scales, not Bahn's production throughput.",
        },
        "hashes": {str(path.relative_to(ROOT)): fingerprint(path) for path in (
            JOURNAL, ROOT / "results/submission-report.json",
            ROOT / "lab/models/risk_v3.json", ROOT / "lab/models/hazard.json",
            ROOT / "lab/models/ref.json", ROOT / "lab/models/win.json", Path(__file__),
        ) + ((official_result,) if official_result.exists() else ())},
    }


if __name__ == "__main__":
    output = ROOT / "submission/evidence.json"
    result = build()
    output.write_text(json.dumps(result, indent=2) + "\n")
    for key, item in result["experiments"].items():
        print(key, json.dumps({k: item[k] for k in ("before", "after", "margin_delta_eur",
                                                     "margin_delta_95", "on_time_delta_pp")}))
    print("Wrote", output.relative_to(ROOT))
