"""Archive the official ended final using reads only; never replay or submit actions."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from spread.client import Client

from .runner import ROOT, load_env

EXPECTED_WORLD = "fbcee268ddd35efae2244"
EXPECTED_START = "2026-11-15T07:00:00.000Z"


def collect():
    load_env()
    client = Client()
    final = client.final()
    if final["worldId"] != EXPECTED_WORLD or final["startsAt"] != EXPECTED_START:
        raise ValueError("The announcement no longer identifies the 15 November official final")
    metadata = next(w for w in client.worlds() if w["worldId"] == final["worldId"])
    if metadata["kind"] != "final" or not metadata["ended"]:
        raise ValueError("The official final has not ended")
    world = client.world(final["worldId"])
    snapshot, score, events, reveal = world.snapshot(), world.score(), world.events(), world.reveal()
    if snapshot["now"] < snapshot["endsAt"]:
        raise ValueError("Final clock has not reached its end")
    if events and [e["seq"] for e in events] != list(range(events[-1]["seq"] + 1)):
        raise ValueError("Final event history is incomplete")
    ledger = sum(e["line"]["cents"] for e in events if e["kind"] == "ledger")
    orders = [o for o in snapshot["orders"] if o["status"] != "cancelled"]
    if ledger != score["marginCents"] or len(orders) != score["wonOrders"]:
        raise ValueError("Official final ledger and score disagree")
    with urlopen("https://spread.bahnexpress.com/v1/leaderboard", timeout=15) as response:
        for raw in response:
            line = raw.decode().strip()
            if line.startswith("data:"):
                board = json.loads(line[5:])
                break
        else:
            raise ValueError("No leaderboard frame received")
    if board["status"] != "ended" or board["startsAt"] != final["startsAt"]:
        raise ValueError("Leaderboard does not describe the same ended final")
    team = next(t for t in board["teams"] if t["team"] == "the-delusionals")
    for field in ("marginCents", "wonOrders", "ranked"):
        if team[field] != score[field]:
            raise ValueError(f"Leaderboard and own-world score disagree: {field}")
    quoted = sum(r["quote"] is not None for r in reveal["requests"])
    ended_at = datetime.fromtimestamp(board["clock"]["endsAtWall"] / 1000, timezone.utc).isoformat()
    result = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "Official Spread final, snapshot, score, events, reveal and public leaderboard; read-only",
        "world": final["worldId"], "starts_at": final["startsAt"], "completed_at": ended_at,
        "score": score, "official_rank": team["rank"],
        "requests": len(reveal["requests"]), "requests_with_quotes": quoted,
        "request_outcomes": dict(Counter(r["outcome"] for r in reveal["requests"])),
        "gigs": len(snapshot["gigs"]), "event_counts": dict(Counter(e["kind"] for e in events)),
        "participation": "no_quotes_submitted" if quoted == 0 else "quotes_submitted",
        "display_on_time_share": score["onTimeShare"] if score["wonOrders"] else None,
        "display_note": "With no won orders, the API's raw onTimeShare=1 is not a meaningful delivery rate.",
        "events_sha256": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(),
        "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    target = ROOT / "results/final-outcome.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    collect()
