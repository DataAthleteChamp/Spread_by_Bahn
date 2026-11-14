"""Optuna tuning of a policy on paired seeds (practice worlds only).

    .venv/bin/python -m lab.tune --base "<variant spec>" --trials 40 --seeds 4 --study econ1

Objective J (per trial, over its seeds):
    mean margin  - 3000 * mean(max(0, 0.93 - on_time) * 100)  - 5000 * (#weeks under 90%)
Each batch runs `parallel` trials x `seeds` weeks at once (<= 8 practice slots). All trials of a study use the
same seeds (paired); results go to results/tune_<study>.jsonl and the journal.
"""
import argparse, json, statistics as st, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import optuna
from .bench import parse_variant, JOURNAL
from .runner import ROOT, run_week

SPACE = {  # name: (low, high, log?)
    "risk_max": (0.30, 0.50, False), "hard_k": (0.5, 3.0, False), "late_cost": (0.2, 0.8, False),
    "fee_hat": (0.9, 1.15, False), "fee_late": (1.0, 1.4, False), "urgent_open": (1.1, 1.6, False),
    "late_h": (2.0, 7.0, False), "trust_k": (0.0, 1.0, False), "eta_w": (0.005, 0.05, True),
    "eta_d": (0.01, 0.1, True), "lead_min": (60, 180, False), "mu_eur": (0.0, 40.0, False),
}


def J(rs):
    ms = [r["margin"] for r in rs]; ot = [r["on_time"] for r in rs]
    return st.mean(ms) - 3000 * st.mean(max(0, 0.93 - o) * 100 for o in ot) - 5000 * sum(o < 0.90 for o in ot)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seeds", type=int, default=4); ap.add_argument("--seed-prefix", default="tune-")
    ap.add_argument("--parallel", type=int, default=2); ap.add_argument("--study", default="econ1")
    ap.add_argument("--params", default=",".join(SPACE))
    a = ap.parse_args()
    label, cls, base = parse_variant(a.base)
    names = a.params.split(",")
    seeds = [f"{a.seed_prefix}{i}" for i in range(a.seeds)]
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(multivariate=True, n_startup_trials=8, seed=1),
                                study_name=a.study, storage=f"sqlite:///{ROOT}/results/optuna.db", load_if_exists=True)
    if len(study.trials) == 0:
        study.enqueue_trial({k: base[k] for k in names if k in base})   # the base config first
    out = ROOT / "results" / f"tune_{a.study}.jsonl"
    t0 = time.time()
    done = 0
    while done < a.trials:
        trials = [study.ask() for _ in range(a.parallel)]
        params = []
        for t in trials:
            p = dict(base)
            for k in names:
                lo, hi, lg = SPACE[k]
                p[k] = t.suggest_int(k, int(lo), int(hi)) if isinstance(lo, int) and isinstance(hi, int) else t.suggest_float(k, lo, hi, log=lg)
            params.append(p)
        with ThreadPoolExecutor(max_workers=a.parallel * a.seeds) as pool:
            futs = {(i, s): pool.submit(run_week, cls, p, 8, s) for i, p in enumerate(params) for s in seeds}
            res = {k: f.result() for k, f in futs.items()}
        for i, t in enumerate(trials):
            rs = [res[(i, s)] for s in seeds]
            if not all(r.get("ok") for r in rs):
                study.tell(t, state=optuna.trial.TrialState.FAIL); continue
            j = J(rs)
            study.tell(t, j)
            rec = {"trial": t.number, "J": round(j), "margin": round(st.mean(r["margin"] for r in rs)), "ot": round(st.mean(r["on_time"] for r in rs), 4),
                   "min_ot": round(min(r["on_time"] for r in rs), 4), "won": round(st.mean(r["won"] for r in rs)), "params": {k: params[i][k] for k in names}}
            with out.open("a") as f: f.write(json.dumps(rec) + "\n")
            print(f"[{time.time()-t0:5.0f}s] trial {t.number:3} J {j:8,.0f} margin {rec['margin']:7,} OT {rec['ot']:.1%} min {rec['min_ot']:.1%} won {rec['won']}", flush=True)
        done += a.parallel
    b = study.best_trial
    print("BEST", b.number, round(b.value), b.params)
    with JOURNAL.open("a") as f:
        f.write(f"\n## {datetime.now():%a %H:%M}: Optuna study `{a.study}`, {len(study.trials)} trials × {a.seeds} seeds ({seeds[0]}..)\n"
                f"Base: `{label}`. Best trial {b.number}: J={b.value:,.0f}, params `{json.dumps({k: round(v, 3) for k, v in b.params.items()})}`\n")


if __name__ == "__main__":
    main()
