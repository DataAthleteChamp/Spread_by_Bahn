"""Reproduce test-final conditions in practice: skip to --start (default Thu 00:00) without acting, then join with
rejoin() like lab.live does and play to the end. Prints quote/list per day and the score.
    .venv/bin/python -m lab.midweek_test CANDIDATE --seed s24-0
"""
import argparse, statistics as st
from spread.client import Client
from .bench import parse_variant
from .desk import DAY, Context
from .runner import create_practice, load_env, world_map
from .restart_test import loop


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("variant"); ap.add_argument("--seed", default="s24-0"); ap.add_argument("--start", type=int, default=3 * DAY)
    a = ap.parse_args(); load_env(); c = Client(); _, cls, params = parse_variant(a.variant)
    w = create_practice(c, 8, a.seed)
    try:
        w.advance(to=a.start)
        snap, hist = w.snapshot(), w.events()
        d = cls(w, 8, snap["now"], Context(world_map(c), w.roster()), params); d.on_start(); d.rejoin(snap, hist); d.send()
        loop(w, d, snap["endsAt"])
        sc = w.score()
        byday = {}
        for rid, q in d.q_ratio.items():
            day = d.requests[rid]["arrivedAt"] // DAY
            byday.setdefault(day, []).append(q)
        print({k: (len(v), round(st.median(v), 2)) for k, v in sorted(byday.items())})
        print(f"RESULT margin €{sc['marginCents']/100:,.0f} on-time {sc['onTimeShare']:.1%} won {sc['wonOrders']} | stats {dict(list(d.stats.items())[:8])}")
    finally:
        try: w.delete()
        except Exception: pass


if __name__ == "__main__":
    main()
