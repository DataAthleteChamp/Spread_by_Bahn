"""Lane table for the typical fee (referenceFeeCents) -> lab/models/ref.json.

HANDBOOK: typical fee = cost to a typical pickup-town driver x one world factor x per-request noise.
We fit log ref = lane + world + noise over all saved worlds, so the bot can shrink the noise away:
    log ref_hat = w * log ref + (1 - w) * (lane + world_offset_online).
"""
from __future__ import annotations

import collections
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "lab" / "models" / "ref.json"


def lane_key(req: dict) -> str | None:
    if len(req["legs"]) != 1:
        return None
    l = req["legs"][0]
    return f'{l["pickup"]["placeId"]}|{l["delivery"]["placeId"]}|{int(l["pickup"]["privateAddress"])}{int(l["delivery"]["privateAddress"])}'


def main():
    rows = []   # (world, lane, log ref)
    for d in sorted((ROOT / "data/runs").iterdir()):
        f = d / "reveal.json"
        if not f.exists():
            continue
        for q in json.load(open(f))["requests"]:
            k = lane_key(q["request"])
            if k:
                rows.append((d.name, k, math.log(q["request"]["referenceFeeCents"])))
    worlds = sorted({w for w, _, _ in rows})
    off = {w: 0.0 for w in worlds}
    for _ in range(5):   # alternate lane means and world offsets
        lane = collections.defaultdict(list)
        for w, k, y in rows:
            lane[k].append(y - off[w])
        mean = {k: sum(v) / len(v) for k, v in lane.items()}
        byw = collections.defaultdict(list)
        for w, k, y in rows:
            byw[w].append(y - mean[k])
        off = {w: sum(v) / len(v) for w, v in byw.items()}
        c = sum(off.values()) / len(off)
        off = {w: o - c for w, o in off.items()}
    res = [y - mean[k] - off[w] for w, k, y in rows]
    n = collections.Counter(k for _, k, _ in rows)
    print(f"{len(worlds)} worlds, {len(rows)} single-leg requests, {len(mean)} lanes")
    print(f"world offset sd {st.pstdev(off.values()):.3f}; residual (noise) sd {st.pstdev(res):.3f}")
    OUT.write_text(json.dumps({"lane": {k: round(v, 4) for k, v in mean.items()}, "n": dict(n), "noise_sd": st.pstdev(res)}))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
