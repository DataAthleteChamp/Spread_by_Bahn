"""Robustness test: play a practice week, kill the desk at --kill-at (minute), rebuild it with rejoin(), finish.
Compare with the uninterrupted bench result on the same seed.
    .venv/bin/python -m lab.restart_test "<variant>" --seed bench-0 --kill-at 3600
"""
import argparse
from spread.client import Client
from .bench import parse_variant
from .desk import WAKE_ON, Context
from .runner import create_practice, load_env, world_map


def loop(world, desk, until):
    while desk.now < until:
        actions, desk.outbox = desk.outbox, []
        wake = desk.next_wake()
        step = world.advance(until=WAKE_ON, max=min(until, wake) if wake and wake > desk.now else until, actions=actions)
        desk.read_results(actions, step.get("results") or [])
        desk.now = step["now"]
        for e in step["events"]:
            desk.handle(e)
        desk.tick()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("variant"); ap.add_argument("--seed", default="bench-0"); ap.add_argument("--kill-at", type=int, default=3600)
    a = ap.parse_args(); load_env(); c = Client(); _, cls, params = parse_variant(a.variant)
    w = create_practice(c, 8, a.seed)
    try:
        snap = w.snapshot(); ctx = Context(world_map(c), w.roster())
        d = cls(w, 8, snap["now"], ctx, params); d.on_start()
        loop(w, d, a.kill_at)
        if d.outbox:
            w.act(d.outbox)   # what was decided before the crash may or may not have been sent; send it
        print("killed at", d.now, "orders", len(d.orders), "deferred", len(d.deferred))
        snap = w.snapshot(); hist = w.events()
        d2 = cls(w, 8, snap["now"], ctx, params); d2.on_start(); d2.rejoin(snap, hist); d2.send()
        print("rejoined: orders", len(d2.orders), "deferred", len(d2.deferred), "trust", sum(getattr(d2, "trust_n", {}).values()))
        loop(w, d2, snap["endsAt"])
        sc = w.score(); print(f"RESULT margin €{sc['marginCents']/100:,.0f} on-time {sc['onTimeShare']:.1%} won {sc['wonOrders']}")
    finally:
        try: w.delete()
        except Exception: pass


if __name__ == "__main__":
    main()
