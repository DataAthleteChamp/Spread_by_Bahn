"""Plays the FINAL (or a test final) live with a lab policy. Survives restarts: rebuilds from snapshot + events.

    .venv/bin/python -m lab.live "<variant spec>"            # waits for the final, then plays it
    .venv/bin/python -m lab.live "<variant spec>" --world <id> # rejoin a specific world (e.g. after a crash)

Run it under a loop that restarts it if it dies:  while true; do .venv/bin/python -m lab.live "..."; sleep 2; done
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime

from spread.client import Client, SpreadError, Unreachable

from .bench import parse_variant
from .desk import DAY, Context
from .runner import load_env, world_map
from .readiness import identity, preflight, single_runner, verify_files, write_record

WEEKDAYS = "Mon Tue Wed Thu Fri Sat Sun Mon2 Tue2 Wed2".split()


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def wait_for_final(client: Client):
    last_report = -float("inf")
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
            if isinstance(e, Unreachable):
                log("Final announcement temporarily unreachable:", e)
        if time.monotonic() - last_report >= 60:
            log("WAITING for an upcoming final; ended test worlds are ignored. Sunday final: 09:00 Helsinki.")
            write_record("state.json", {"status": "waiting", "updated_at": datetime.now().astimezone().isoformat()})
            last_report = time.monotonic()
        time.sleep(10)


def finish(world, startup):
    score = world.score()
    if startup is not None:
        result = {**startup, "world": world.id, "score": score,
                  "completed_at": datetime.now().astimezone().isoformat()}
        write_record("result.json", result)
        write_record("state.json", {"status": "ended", "world": world.id, "score": score,
                                   "updated_at": result["completed_at"]})
    log(f"END margin €{score['marginCents']/100:,.0f} won {score['wonOrders']} "
        f"on-time {score['onTimeShare']:.1%} ranked {score['ranked']}")


def play(world, cls, params, client, startup=None):
    if startup is not None:
        verify_files(startup)
    history = world.events()
    snap = world.snapshot()
    if snap["now"] >= snap["endsAt"]:
        finish(world, startup)
        return True
    ctx = Context(world_map(client), world.roster())
    desk = cls(world, 8, snap["now"], ctx, params)
    desk.on_start()
    if startup is not None:
        write_record("active.json", {**startup, "world": world.id, "resolved_params": desk.p})
        log("ACTIVE", json.dumps({"world": world.id, "variant": startup["variant"],
                                 "git": startup["git"], "params_sha256": startup["params_sha256"]}))
    desk.rejoin(snap, history)
    desk.send()
    log(f"joined {world.id} at {WEEKDAYS[snap['now'] // DAY]} {snap['now'] % DAY // 60:02d}:{snap['now'] % 60:02d}; "
        f"{len(desk.orders)} orders, {len(history)} past events")
    last_report = time.time()
    after = history[-1]["seq"] if history else -1
    for event in world.stream(after=after, idle=1.0):
        if event is None:
            try:
                final = client.final()
                if final["worldId"] == world.id:
                    desk.now = max(desk.now, final["now"])
                else:
                    log("Announcement changed; retaining the active world's clock", world.id)
            except SpreadError as error:
                log("Clock read failed; continuing from streamed events:", error)
        else:
            desk.now = max(desk.now, event["at"])
            desk.handle(event)
        desk.tick()
        desk.send()
        if time.time() - last_report > 60:
            sc = world.score()
            import statistics as _st
            qr = list(desk.q_ratio.values())[-60:]
            rej = {k: v for k, v in desk.stats.items() if k.startswith("rejected") or k.startswith("batch")}
            log(f"{WEEKDAYS[desk.now // DAY]} {desk.now % DAY // 60:02d}:00 margin €{sc['marginCents']/100:,.0f} won {sc['wonOrders']} "
                f"on-time {sc['onTimeShare']:.1%} | quotes {len(desk.q_ratio)} q/list(med last60) {(_st.median(qr) if qr else 0):.3f} "
                f"theta_w {getattr(desk, 'theta_w', 0):.3f} mu {getattr(desk, 'mu', 0):.2f} rejected {rej} | {dict(list(desk.stats.items())[:8])}")
            if startup is not None:
                write_record("state.json", {"status": "running", "world": world.id, "now": desk.now, "score": sc,
                                           "updated_at": datetime.now().astimezone().isoformat()})
            last_report = time.time()
        if desk.now >= snap["endsAt"]:
            break
    if desk.now < snap["endsAt"] and world.snapshot()["now"] < snap["endsAt"]:
        log("Stream closed before the week ended; rebuilding the same world in 1 s", world.id)
        time.sleep(1)
        return False
    finish(world, startup)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("--world")
    ap.add_argument("--check", action="store_true", help="Verify frozen files and API access; send no game actions.")
    a = ap.parse_args()
    load_env()
    client = Client()
    _, cls, params = parse_variant(a.variant)
    startup = identity(a.variant, cls, params)
    readiness = preflight(client)
    if a.check:
        log("CHECK OK", json.dumps({"identity": startup, "readiness": readiness}))
        return
    with single_runner():
        write_record("startup.json", {**startup, "readiness": readiness})
        log("STARTUP", json.dumps(startup))
        run(client, cls, params, a.world, startup)


def run(client, cls, params, world_id, startup):
    world = client.world(world_id) if world_id else None
    while True:
        try:
            if world is None:
                world = wait_for_final(client)
                log("final world", world.id)
            if play(world, cls, params, client, startup):
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
