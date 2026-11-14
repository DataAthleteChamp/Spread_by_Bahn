"""Plays one practice week with a policy and returns its metrics. Never creates ranking runs."""
from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

from spread.client import Client, SpreadError

from .desk import WAKE_ON, Context, clean_schedule, safe_act

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "data" / "map.json"
CREATED_LOG = ROOT / "results" / ".created_worlds"
BATCH_MIN = int(os.environ.get("SPREAD_BATCH_MIN", "12"))   # 0 = old behaviour (one request per event)


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def world_map(client: Client) -> dict:
    if MAP_FILE.exists():
        return json.loads(MAP_FILE.read_text())
    m = client.map()
    MAP_FILE.parent.mkdir(exist_ok=True)
    MAP_FILE.write_text(json.dumps(m))
    return m


def create_practice(client: Client, level: int, seed: str, wait_s: float = 600):
    """Creates a PRACTICE world (board=False, always). Waits while all 8 slots are taken."""
    t0 = time.time()
    while True:
        try:
            world = client.create(level=level, seed=seed, board=False)
            CREATED_LOG.parent.mkdir(exist_ok=True)
            with CREATED_LOG.open("a") as f:
                f.write(world.id + "\n")
            return world
        except SpreadError as e:
            if e.status == 409 and time.time() - t0 < wait_s:  # all practice slots taken: wait for one
                time.sleep(2)
                continue
            raise


def run_week(policy_cls, params: dict, level: int, seed: str, save_reveal: bool = False, board: bool = False) -> dict:
    load_env()
    client = Client()  # one client (= one HTTP connection) per thread
    t0 = time.time()
    result = {"policy": policy_cls.NAME, "params": params, "level": level, "seed": seed}
    world = None
    try:
        world = client.create(level=level, board=True) if board else create_practice(client, level, seed)
        result["world"] = world.id
        snap = world.snapshot()
        ctx = Context(world_map(client), world.roster())
        desk = policy_cls(world, level, snap["now"], ctx, params)
        desk.on_start()
        ends_at = snap["endsAt"]
        steps = 0
        extend = False   # request batching: after the first new request, jump BATCH_MIN minutes in one call
        while desk.now < ends_at:
            actions, desk.outbox = desk.outbox, []
            for act in actions:
                if "schedule" in act:
                    act["schedule"] = clean_schedule(act["schedule"])[: 1 if level == 1 else 48]
            wake = desk.next_wake()
            mx = min(ends_at, wake) if wake and wake > desk.now else ends_at
            kw = {"to": min(ends_at, desk.now + BATCH_MIN)} if extend else {"until": WAKE_ON, "max": mx}
            try:
                step = world.advance(actions=actions, **kw)
            except SpreadError as e:   # one bad action must not lose the others: send them one by one, then move on
                if e.status != 400 or not actions:
                    raise
                res = safe_act(world, actions, desk)
                step = world.advance(**kw)
                step["results"] = res
            steps += 1
            desk.read_results(actions, step.get("results") or [])
            desk.now = step["now"]
            new_req = False
            for event in step["events"]:
                desk.handle(event)
                new_req |= event["kind"] == "price_request"
            desk.tick()
            # Every request gives 15 minutes: after stopping at a new request, collect the next BATCH_MIN minutes in one
            # call; their quotes go out with the following call, still inside their windows (arrival + 15 > now + BATCH_MIN).
            extend = BATCH_MIN > 0 and new_req and not extend
        score = world.score()
        result.update(
            ok=True,
            margin=score["marginCents"] / 100,
            revenue=score["revenueCents"] / 100,
            on_time=score["onTimeShare"],
            won=score["wonOrders"],
            undelivered=score["undeliveredShare"],
            ranked=score["ranked"],
            stats=desk.stats,
            metrics=desk.metrics(),
            steps=steps,
        )
        if save_reveal:
            out = ROOT / "data" / "runs" / world.id
            out.mkdir(parents=True, exist_ok=True)
            (out / "reveal.json").write_text(json.dumps(world.reveal()))
            (out / "events.json").write_text(json.dumps(world.events()))
            (out / "roster.json").write_text(json.dumps(ctx.roster))
            (out / "meta.json").write_text(json.dumps(result))
    except BaseException as e:  # noqa: BLE001 - always free the slot
        result.update(ok=False, error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])
        if world is not None and not board:  # a ranking run plays on without us anyway
            try:
                world.delete()
            except SpreadError:
                pass
        if isinstance(e, KeyboardInterrupt):
            raise
    result["seconds"] = round(time.time() - t0, 1)
    return result
