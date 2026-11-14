"""Plays the FINAL (or a test final) live with a lab policy. Survives restarts: rebuilds from snapshot + events.

    .venv/bin/python -m lab.live "<variant spec>"            # waits for the final, then plays it
    .venv/bin/python -m lab.live "<variant spec>" --world <id> # rejoin a specific world (e.g. after a crash)

Run it under a loop that restarts it if it dies:  while true; do .venv/bin/python -m lab.live "..."; sleep 2; done
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime

from spread.client import Client, SpreadError, Unreachable

from .bench import parse_variant
from .desk import DAY, Context
from .runner import load_env, world_map

WEEKDAYS = "Mon Tue Wed Thu Fri Sat Sun Mon2 Tue2 Wed2".split()


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def wait_for_final(client: Client):
    said = False
    while True:
        try:
            f = client.final()
            w = client.world(f["worldId"])
            snap = w.snapshot()
            if snap["now"] < snap["endsAt"]:
                return w
        except SpreadError as e:
            if e.status not in (404,) and not isinstance(e, Unreachable):
                raise
        if not said:
            log("No live final yet; waiting (test finals Sat 14:00/20:00, final Sun 08:00 Helsinki; set 15/30 min before).")
            said = True
        time.sleep(10)


def play(world, cls, params, client):
    history = world.events()
    snap = world.snapshot()
    if snap["now"] >= snap["endsAt"]:
        log("world has ended"); return True
    ctx = Context(world_map(client), world.roster())
    desk = cls(world, 8, snap["now"], ctx, params)
    desk.on_start()
    desk.rejoin(snap, history)
    desk.send()
    log(f"joined {world.id} at {WEEKDAYS[snap['now'] // DAY]} {snap['now'] % DAY // 60:02d}:{snap['now'] % 60:02d}; "
        f"{len(desk.orders)} orders, {len(history)} past events")
    last_report = time.time()
    after = history[-1]["seq"] if history else -1
    for event in world.stream(after=after, idle=1.0):
        if event is None:
            try:
                desk.now = max(desk.now, client.final()["now"])
            except SpreadError:
                pass
        else:
            desk.now = max(desk.now, event["at"])
            desk.handle(event)
        desk.tick()
        desk.send()
        if time.time() - last_report > 60:
            sc = world.score()
            log(f"{WEEKDAYS[desk.now // DAY]} {desk.now % DAY // 60:02d}:00 margin €{sc['marginCents']/100:,.0f} won {sc['wonOrders']} "
                f"on-time {sc['onTimeShare']:.1%} stats {dict(list(desk.stats.items())[:6])}")
            last_report = time.time()
        if desk.now >= snap["endsAt"]:
            break
    sc = world.score()
    log(f"END margin €{sc['marginCents']/100:,.0f} won {sc['wonOrders']} on-time {sc['onTimeShare']:.1%} ranked {sc['ranked']}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("--world")
    a = ap.parse_args()
    load_env()
    client = Client()
    _, cls, params = parse_variant(a.variant)
    world = client.world(a.world) if a.world else None
    while True:
        try:
            if world is None:
                world = wait_for_final(client)
                log("final world", world.id)
            if play(world, cls, params, client):
                return
        except (Unreachable, ConnectionError, TimeoutError) as e:
            log("connection problem:", e, "- rebuilding in 5 s")
            time.sleep(5)
        except KeyboardInterrupt:
            log("stopped by hand; the world keeps running. Restart to rejoin."); sys.exit(1)
        except Exception as e:  # noqa: BLE001 - never die in the final: rebuild and continue
            log("ERROR", type(e).__name__, e); traceback.print_exc()
            time.sleep(3)


if __name__ == "__main__":
    main()
