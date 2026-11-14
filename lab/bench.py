"""Parallel A/B bench: runs policy variants x seeds on PRACTICE worlds and compares them on the same seeds.

Examples
    python -m lab.bench starter markup --seeds 8
    python -m lab.bench markup markup:mult=1.4 markup:mult=1.4,min_drivers=0 --seeds 16 --level 8
    python -m lab.bench markup --seed-list spread-1 --reveal        # also save reveal for analysis
    python -m lab.bench --cleanup                                   # delete unfinished worlds this bench created

A variant is  policy[:key=value,key=value]. Seeds are `bench-0 ... bench-N` (same for every variant -> paired
comparison). The first variant is the baseline for the paired difference. Every run is appended to
results/runs.jsonl. Ranking runs are never created.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .policies import PRESETS, get
from .runner import CREATED_LOG, ROOT, load_env, run_week

RESULTS = ROOT / "results" / "runs.jsonl"


def parse_variant(spec: str):
    label = spec
    while spec.split(":")[0] in PRESETS:  # preset[:overrides] (presets may alias presets)
        base, _, extra = spec.partition(":")
        target = PRESETS[base]
        if target in PRESETS:
            spec = target + (":" + extra if extra else "")
            continue
        spec = target + ("," + extra if extra else "")
    name, _, rest = spec.partition(":")
    params = {}
    for kv in filter(None, rest.split(",")):
        k, v = kv.split("=", 1)
        try:
            params[k] = int(v)
        except ValueError:
            try:
                params[k] = float(v)
            except ValueError:
                params[k] = v
    cls = get(name)
    unknown = set(params) - set(cls.DEFAULTS)
    if unknown:
        raise SystemExit(f"{name}: unknown params {sorted(unknown)}. Known: {sorted(cls.DEFAULTS)}")
    return label, cls, params


def fmt_eur(x: float) -> str:
    return f"€{x:,.0f}"


def summarize(variants, seeds, results) -> str:
    out = []
    print = lambda *a, **k: out.append(" ".join(str(x) for x in a))  # noqa: E731
    by = {(r["variant"], r["seed"]): r for r in results if r.get("ok")}
    base = variants[0][0]
    print()
    hdr = f"{'variant':<44} {'n':>3} {'margin/wk':>11} {'±sd':>8} {'on-time':>8} {'min OT':>7} {'ranked':>7} {'won':>5} {'Δ vs base':>11} {'t':>6}"
    print(hdr)
    print("-" * len(hdr))
    for spec, _, _ in variants:
        rs = [by[(spec, s)] for s in seeds if (spec, s) in by]
        if not rs:
            print(f"{spec:<44}   0   (all runs failed)")
            continue
        m = [r["margin"] for r in rs]
        ot = [r["on_time"] for r in rs]
        sd = st.stdev(m) if len(m) > 1 else 0.0
        diffs = [by[(spec, s)]["margin"] - by[(base, s)]["margin"] for s in seeds if (spec, s) in by and (base, s) in by]
        if spec != base and len(diffs) > 1 and st.stdev(diffs) > 0:
            d, t = st.mean(diffs), st.mean(diffs) / (st.stdev(diffs) / math.sqrt(len(diffs)))
            dtxt, ttxt = fmt_eur(d), f"{t:5.1f}"
        else:
            dtxt, ttxt = "—", ""
        ranked = sum(r["ranked"] for r in rs)
        print(f"{spec[:44]:<44} {len(rs):>3} {fmt_eur(st.mean(m)):>11} {fmt_eur(sd):>8} {st.mean(ot):>7.1%} {min(ot):>6.1%} "
              f"{ranked:>3}/{len(rs):<3} {st.mean(r['won'] for r in rs):>5.0f} {dtxt:>11} {ttxt:>6}")
    # key diagnostics per variant
    print()
    print(f"{'variant':<44} {'won/q':>6} {'q/list':>7} {'won/list':>8} {'fee/typ':>8} {'€/order':>8} {'late':>5} {'drops':>6} {'warn':>5} {'fails':>6}")
    for spec, _, _ in variants:
        ms = [by[(spec, s)].get("metrics") or {} for s in seeds if (spec, s) in by]
        def avg(k):
            v = [m[k] for m in ms if m.get(k) is not None]
            return st.mean(v) if v else float("nan")
        print(f"{spec[:44]:<44} {avg('win_rate_quoted'):>6.2f} {avg('q_ratio_med'):>7.2f} {avg('won_ratio_med'):>8.2f} {avg('fee_ratio_mean'):>8.2f} "
              f"{avg('eur_per_order'):>8.1f} {avg('late_orders'):>5.0f} {avg('drops'):>6.0f} {avg('warnings'):>5.0f} {avg('failed_visits'):>6.0f}")
    print("\nΔ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.")
    text = "\n".join(out)
    __builtins__["print"](text) if isinstance(__builtins__, dict) else __builtins__.print(text)
    return text


JOURNAL = ROOT / "EXPERIMENTS.md"


def journal(a, variants, seeds, table: str) -> None:
    """Appends the experiment (hypothesis + full table) to EXPERIMENTS.md. Decisions are added by hand below it."""
    new = not JOURNAL.exists()
    with JOURNAL.open("a") as f:
        if new:
            f.write("# Experiment journal\n\nAuto-appended by `lab.bench` (hypothesis + results). The **Decision** lines are written after reading the results.\n")
        f.write(f"\n## {datetime.now():%a %H:%M} — tag `{a.tag or '-'}` — level {a.level}, {len(seeds)} seeds ({seeds[0]}..)\n")
        f.write(f"**Why:** {a.why or '(not given)'}\n\n")
        f.write("**Variants:** " + "; ".join(f"`{v[0]}`" for v in variants) + "\n\n```\n" + table + "\n```\n")


def board_runs(variant, a) -> None:
    """Ranking runs: the next worlds of the current ranking round, one after another (the server allows one open at a time)."""
    spec, cls, params = variant
    print(f"RANKING RUNS with {spec} at level {a.level} (they count on the public practice leaderboard)")
    rows = []
    with RESULTS.open("a") as log:
        for i in range(5):
            r = run_week(cls, params, a.level, "board", False, board=True)
            r.update(variant=spec, tag=a.tag or "board", at=datetime.now().isoformat(timespec="seconds"), board=True)
            log.write(json.dumps(r) + "\n"); log.flush()
            if not r.get("ok"):
                print("stopped:", r.get("error", "")[:200]); break
            rows.append(r)
            print(f"run {i + 1}: margin {fmt_eur(r['margin'])} on-time {r['on_time']:.1%} won {r['won']} ranked {r['ranked']} ({r['seconds']}s)", flush=True)
    if rows:
        tot = sum(r["margin"] for r in rows)
        text = f"{len(rows)} ranking runs: total {fmt_eur(tot)} ({fmt_eur(tot / len(rows))}/week), min on-time {min(r['on_time'] for r in rows):.1%}"
        print(text)
        with JOURNAL.open("a") as f:
            f.write(f"\n## {datetime.now():%a %H:%M} — RANKING RUNS — `{spec}`\n**Why:** {a.why or '-'}\n\n" +
                    "\n".join(f"- run {i+1}: {fmt_eur(r['margin'])}, on-time {r['on_time']:.1%}, won {r['won']}" for i, r in enumerate(rows)) + f"\n- **{text}**\n")


def cleanup() -> None:
    from spread.client import Client, SpreadError
    load_env()
    c = Client()
    mine = set(CREATED_LOG.read_text().split()) if CREATED_LOG.exists() else set()
    open_worlds = [w for w in c.worlds() if not w["ended"] and w["kind"] == "practice" and not w.get("season")]
    n = 0
    for w in open_worlds:
        if w["worldId"] in mine:
            try:
                c.world(w["worldId"]).delete()
                n += 1
            except SpreadError as e:
                print("could not delete", w["worldId"], e)
    print(f"deleted {n} unfinished bench worlds; {len(open_worlds) - n} other open practice worlds left alone (teammates?)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variants", nargs="*", help="policy[:k=v,...]")
    ap.add_argument("--seeds", type=int, default=8, help="number of seeds bench-0..N-1 (default 8)")
    ap.add_argument("--seed-prefix", default="bench-")
    ap.add_argument("--seed-list", help="comma-separated explicit seeds (overrides --seeds)")
    ap.add_argument("--level", type=int, default=8)
    ap.add_argument("--workers", type=int, default=8, help="parallel worlds (max 8 practice slots per team, shared with teammates)")
    ap.add_argument("--reveal", action="store_true", help="save reveal + events of each run under data/runs/")
    ap.add_argument("--tag", default="", help="free text stored with the runs")
    ap.add_argument("--cleanup", action="store_true")
    ap.add_argument("--why", default="", help="hypothesis: logged to EXPERIMENTS.md with the result table")
    ap.add_argument("--board", action="store_true", help="play RANKING runs (counts on the public practice leaderboard!) with the first variant, sequentially")
    a = ap.parse_args()
    if a.cleanup:
        return cleanup()
    if not a.variants:
        ap.error("give at least one variant, e.g. starter markup")
    variants = [parse_variant(v) for v in a.variants]
    if a.board:
        return board_runs(variants[0], a)
    seeds = a.seed_list.split(",") if a.seed_list else [f"{a.seed_prefix}{i}" for i in range(a.seeds)]
    jobs = [(spec, cls, params, s) for s in seeds for spec, cls, params in variants]  # interleave -> early paired data
    print(f"{len(jobs)} weeks: {len(variants)} variants x {len(seeds)} seeds, level {a.level}, {a.workers} parallel")
    t0, results = time.time(), []
    RESULTS.parent.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=min(a.workers, 8)) as pool, RESULTS.open("a") as log:
        futs = {pool.submit(run_week, cls, params, a.level, s, a.reveal): (spec, s) for spec, cls, params, s in jobs}
        try:
            for i, f in enumerate(as_completed(futs), 1):
                spec, s = futs[f]
                r = f.result()
                r.update(variant=spec, tag=a.tag, at=datetime.now().isoformat(timespec="seconds"))
                results.append(r)
                log.write(json.dumps(r) + "\n")
                log.flush()
                if r.get("ok"):
                    msg = f"margin {fmt_eur(r['margin']):>10}  on-time {r['on_time']:.1%}  won {r['won']}"
                else:
                    msg = "FAILED " + r["error"][:120]
                print(f"[{i:>3}/{len(jobs)} {time.time() - t0:5.0f}s] {spec[:40]:<40} {s:<10} {msg}  ({r['seconds']}s)", flush=True)
        except KeyboardInterrupt:
            print("\nInterrupted: cancelling queued runs (running worlds are deleted).", file=sys.stderr)
            for f in futs:
                f.cancel()
            raise
    table = summarize(variants, seeds, results)
    print(f"\n{len(jobs)} weeks in {time.time() - t0:.0f}s. Log: {RESULTS.relative_to(ROOT)}")
    journal(a, variants, seeds, table)


if __name__ == "__main__":
    main()
