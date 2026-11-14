"""Why are orders late? Usage: python -m lab.diagnose <world_id> [...]  (needs a run saved with --reveal)"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
M = json.load(open(ROOT / "data/map.json")); ROAD = {(r["from"], r["to"]): r["minutes"] for r in M["roads"]}
DAYS = "Mon Tue Wed Thu Fri Sat Sun Mon2 Tue2 Wed2".split()

def analyse(W):
    d = ROOT / "data/runs" / W
    rv, ev = json.load(open(d / "reveal.json")), json.load(open(d / "events.json"))
    req = {r["request"]["id"]: r for r in rv["requests"]}
    truth = {o["orderId"]: o for o in rv["orders"]}
    won, gigs_of, booked_at, warn, fails, posted, fee = {}, collections.defaultdict(set), {}, collections.Counter(), collections.Counter(), {}, {}
    gig_order = {}
    for e in ev:
        k = e["kind"]
        if k == "order_won": won[e["order"]["id"]] = e["order"] | {"wonAt": e["at"]}
        elif k == "deadline_close": warn[e["orderId"]] += 1
        elif k == "visit_failed": fails[(e["orderId"], e.get("reason"))] += 1
        elif k == "gig_booked":
            o = gig_order.get(e["gigId"])
            if o and o not in booked_at: booked_at[o] = e["at"]
        elif k == "delivered": gig_order.setdefault(e["gigId"], e["orderId"])
        elif k == "order_cancelled": won.pop(e["orderId"], None)
    # map gig->order from views/bookings needs posts: use ledger lines with orderId+gigId
    for e in ev:
        if e["kind"] == "ledger" and e.get("line", {}).get("gigId") and e["line"].get("orderId"):
            gig_order.setdefault(e["line"]["gigId"], e["line"]["orderId"])
    for e in ev:
        if e["kind"] == "gig_booked":
            o = gig_order.get(e["gigId"])
            if o: booked_at.setdefault(o, e["at"])
    rows = []
    for oid, o in won.items():
        t = truth.get(oid); 
        if not t: continue
        dl = [l["deliveredAt"] for l in t["legs"]]
        late = any(x is None or x > o["deadline"] for x in dl)
        a = o["legs"][0]["pickup"]["placeId"]; b = o["legs"][0]["delivery"]["placeId"]
        r = req[oid]["request"]
        rows.append(dict(oid=oid, late=late, undeliv=any(x is None for x in dl), opt=o["option"], a=a, b=b,
            drive=ROAD[(a, b)], day=DAYS[r["arrivedAt"] // 1440], hour=(r["arrivedAt"] % 1440) // 60,
            slack=o["deadline"] - max(l["pickup"]["window"]["from"] for l in o["legs"]) - ROAD[(a, b)],
            warned=warn[oid] > 0, booked=oid in booked_at, book_delay=(booked_at.get(oid, 10**6) - o["wonAt"]),
            note=bool(r.get("note")), notedl=any(l.get("noteDeadline") for l in t["legs"]),
            failed=any(f[0] == oid for f in fails), price=o["priceCents"] / 100, legs=len(o["legs"])))
    return rows

rows = [r for W in sys.argv[1:] for r in analyse(W)]
n = len(rows); L = [r for r in rows if r["late"]]
print(f"orders {n}, late {len(L)} ({len(L)/n:.1%}), undelivered {sum(r['undeliv'] for r in rows)}")
def share(key, rs=rows):
    c, l = collections.Counter(), collections.Counter()
    for r in rs: c[r[key]] += 1; l[r[key]] += r["late"]
    return sorted(((round(l[k]/c[k],2), c[k], k) for k in c), reverse=True)
for key in ("opt", "day", "a", "b", "warned", "note", "notedl", "failed", "legs"):
    print(f"\nlate rate by {key} (rate, n, value):", share(key)[:12])
print("\nlate rate by slack bucket:")
for lo, hi in [(-1e9,0),(0,120),(120,300),(300,600),(600,1440),(1440,1e9)]:
    rs=[r for r in rows if lo<=r["slack"]<hi]
    if rs: print(f"  slack {lo:>6}..{hi:<6} n={len(rs):3} late={sum(r['late'] for r in rs)/len(rs):.2f}")
print("\nlate rate by drive minutes:")
for lo, hi in [(0,60),(60,150),(150,300),(300,2000)]:
    rs=[r for r in rows if lo<=r["drive"]<hi]
    if rs: print(f"  drive {lo:>4}..{hi:<4} n={len(rs):3} late={sum(r['late'] for r in rs)/len(rs):.2f}")
print("\nlate orders: booked?", collections.Counter(r["booked"] for r in L), " warned?", collections.Counter(r["warned"] for r in L))
