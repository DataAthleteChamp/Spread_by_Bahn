"""Driver-booking hazard + drop model, and a finite-horizon DP for the fee schedule (user's bet #1).

    .venv/bin/python -m lab.fit_hazard            # build data, fit, validate, solve DP, write lab/models/hazard.json

1. Hazard data. One row per (gig spell, 10-minute period) from posting (first view ~ posting) until booked / expired /
   withdrawn / dropped-back-open / world end. Single-order, single-leg gigs only. The visible fee is reconstructed from
   the fees drivers saw in views (+ the booked fee); a fee change between two observations is placed at the policy's
   known step anchors (post+60..240 min, lastPickupAt-4..10 h, deadline_close+30k) or else at the midpoint.
   y = 1 if an app booking happened in the period (bookings through direct offers are censored).
2. Models.  logit h = x'b (pooled, with controls)  and a within-gig conditional logit (gig fixed effects: which period
   did the booking happen in, given it happened) to check the fee effect against "high fees sit on hard gigs".
   Drop model: logit P(drop before start | booked fee ratio, hold hours, ...).
3. DP. State (period k, fee level i), levels LEVELS x typical, non-decreasing; per raise a learning penalty; booking at
   level i costs f_i + p_drop(f_i) * (V(k+d, i) - f_i); unbooked at the horizon costs `late_cost` x typical.
   The lookup table summarises the optimal schedule by (hours until lastPickupAt at posting, pickup coverage bucket).
"""
from __future__ import annotations

import json
import math
import os
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"
CACHE = Path(os.environ.get("HAZ_CACHE", "/tmp/haz/rows.pkl"))
PERIOD = 10
DAY = 1440
WORLD_END = 2 * 7 * DAY  # safety cap
LEVELS = [0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.6]


def hav(p1, p2):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (p1["lat"], p1["lon"], p2["lat"], p2["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


MAP = json.load(open(ROOT / "data" / "map.json"))
PLACES = {p["id"]: p for p in MAP["places"]}
ROAD = {(r["from"], r["to"]): r["minutes"] for r in MAP["roads"]}


def minutes(a, b):
    return 0 if a == b else ROAD.get((a, b), ROAD.get((b, a), 600))


def tag_of_worlds():
    out = {}
    for line in open(ROOT / "results" / "runs.jsonl"):
        r = json.loads(line)
        if r.get("world"):
            out[r["world"]] = r.get("tag")
    return out


FAMILY = {"reveal6": "cand6", "datagen3": "econ", "sweep7": "smart", "diag1": "smart", "diag2": "smart", "datagen1": "smart_old"}


# ---------------------------------------------------------------------------------------------- data
def load_world(w):
    d = RUNS / w
    ev = json.load(open(d / "events.json"))
    rv = json.load(open(d / "reveal.json"))
    roster = json.load(open(d / "roster.json"))
    return ev, rv, roster


def coverage(roster):
    cov30 = {t: sum(1 for x in roster if hav(PLACES[x["homePlaceId"]], PLACES[t]) <= 30) for t in PLACES}
    reach = {t: sum(math.exp(-minutes(x["homePlaceId"], t) / 60.0) for x in roster) for t in PLACES}
    return cov30, reach


def gig_order_map(ev, views):
    go = defaultdict(set)
    for e in ev:
        k = e["kind"]
        if k in ("picked_up", "delivered", "visit_failed"):
            go[e["gigId"]].add(e["orderId"])
        elif k == "ledger" and e["line"].get("gigId") and e["line"].get("orderId"):
            go[e["line"]["gigId"]].add(e["line"]["orderId"])
        elif k == "order_cancelled":
            for g in e.get("gigs", []):
                go[g["gigId"]].add(e["orderId"])
    # expired gigs: the desk reposts the order at once (same step) with the same schedule -> the repost is the next gig id
    # first viewed soon after the expiry whose first viewed fee equals a fee seen on the expired gig. Follow chains.
    fees, first = defaultdict(set), {}
    for v in views:
        fees[v["gigId"]].add(v["feeCents"])
        if v["gigId"] not in first or v["at"] < first[v["gigId"]][0]:
            first[v["gigId"]] = (v["at"], v["feeCents"])
    num = lambda g: int(g[1:])
    expired = [(e["at"], e["gigId"]) for e in ev if e["kind"] == "gig_expired"]
    for _ in range(4):
        for te, g in sorted(expired, reverse=True):
            if go.get(g) or g not in fees:
                continue
            c = sorted((num(y), y) for y, (t1, f1) in first.items()
                       if num(y) > num(g) and te <= t1 <= te + 240 and f1 in fees[g] and go.get(y))
            if c:
                go[g] |= go[c[0][1]]
    return go


def lpa_at(hist, t):
    v = hist[0][1]
    for at, x in hist:
        if at <= t:
            v = x
        else:
            break
    return v


def build_world(w, fam):
    ev, rv, roster = load_world(w)
    req = {r["request"]["id"]: r["request"] for r in rv["requests"]}
    cov30, reach = coverage(roster)
    drv = {x["id"]: x for x in roster}
    t_end = max(e["at"] for e in ev)
    orders = defaultdict(list)       # oid -> [(t, order snapshot)]
    lpa = defaultdict(list)          # oid -> [(t, lastPickupAt)]
    closes = defaultdict(list)       # oid -> deadline_close times
    cancelled, changed = {}, defaultdict(list)
    delivered_at = {}
    for e in ev:
        k = e["kind"]
        if k in ("order_won", "order_changed"):
            o = e["order"]
            orders[o["id"]].append((e["at"], o))
            lpa[o["id"]].append((e["at"], o["lastPickupAt"]))
            if k == "order_changed":
                changed[o["id"]].append(e["at"])
        elif k == "deadline_close":
            closes[e["orderId"]].append(e["at"])
            lpa[e["orderId"]].append((e["at"], e["lastPickupAt"]))
        elif k == "order_cancelled":
            cancelled[e["orderId"]] = e["at"]
        elif k == "delivered":
            delivered_at[e["orderId"]] = e["at"]
    for v in lpa.values():
        v.sort(key=lambda x: x[0])
    go = gig_order_map(ev, rv["views"])
    # per-gig event streams
    gv = defaultdict(list)
    for v in rv["views"]:
        gv[v["gigId"]].append((v["at"], v["driverId"], v["feeCents"]))
    gev = defaultdict(list)
    offer_yes = set()
    for e in ev:
        if e["kind"] == "offer_answered" and e.get("answer") == "accepted":
            offer_yes.add((e["gigId"], e["driverId"]))
    for e in ev:
        if e["kind"] in ("gig_booked", "gig_dropped", "no_show", "gig_expired", "gig_started", "picked_up"):
            gev[e["gigId"]].append(e)
    gigs = sorted(set(gv) | set(gev), key=lambda g: int(g[1:]))
    # order's first post, all gig starts per order, viewers per order (time-stamped)
    start_of = {}
    for g in gigs:
        ts = [x[0] for x in gv.get(g, [])] + [e["at"] for e in gev.get(g, []) if e["kind"] == "gig_booked"]
        if ts:
            start_of[g] = min(ts)
    order_gigs = defaultdict(list)
    for g, os_ in go.items():
        for o in os_:
            if g in start_of:
                order_gigs[o].append(g)
    first_post = {o: min(start_of[g] for g in gs) for o, gs in order_gigs.items()}
    order_views = defaultdict(list)
    for o, gs in order_gigs.items():
        for g in gs:
            order_views[o] += [(t, d, f) for t, d, f in gv.get(g, [])]
        order_views[o].sort()
    rows, drops = [], []
    n_skip = defaultdict(int)
    for g in gigs:
        os_ = go.get(g)
        if not os_ or len(os_) != 1 or g not in start_of:
            n_skip["unmapped_or_multi"] += 1
            continue
        oid = next(iter(os_))
        if oid not in orders or oid not in req:
            n_skip["no_order"] += 1
            continue
        o0 = orders[oid][0][1]
        if len(o0["legs"]) != 1:
            n_skip["multi_leg"] += 1
            continue
        r = req[oid]
        ref = r["referenceFeeCents"]
        leg = o0["legs"][0]
        a, b = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        s0 = start_of[g]
        # ----- fee path
        obs = [(t, f) for t, _, f in gv.get(g, [])] + [(e["at"], e["feeCents"]) for e in gev.get(g, []) if e["kind"] == "gig_booked"]
        obs.sort()
        anchors = [s0 + m for m in (60, 90, 120, 180, 240)]
        for _, x in lpa[oid]:
            anchors += [x - h * 60 for h in (3, 4, 6, 8, 10)]
        for c in closes.get(oid, []):
            anchors += [c + 30 * k for k in range(5)]
        path = [(s0, obs[0][1])]
        for (t1, f1), (t2, f2) in zip(obs, obs[1:]):
            if f2 != path[-1][1]:
                mid = (t1 + t2) / 2
                inside = [x for x in anchors if t1 < x <= t2]
                tc = min(inside, key=lambda x: abs(x - mid)) if inside else mid
                path.append((tc, f2))

        def fee_at(t):
            f = path[0][1]
            for tc, x in path:
                if tc <= t:
                    f = x
            return f

        def since_change(t):
            ch = [tc for tc, _ in path[1:] if tc <= t]
            return (t - max(ch)) / 60 if ch else 99.0
        first_fee_order = order_views[oid][0][2] if order_views[oid] else obs[0][1]
        # ----- spells
        evs = sorted(gev.get(g, []), key=lambda e: e["at"])
        ends = [t_end]
        if oid in cancelled:
            ends.append(cancelled[oid])
        ends += [t for t in changed.get(oid, []) if t > s0]
        later = [start_of[g2] for g2 in order_gigs[oid] if g2 != g and start_of[g2] > s0]
        if later:
            ends.append(min(later))
        hard_end = min(ends)
        spells = []
        cur, reopened = s0, False
        booked_by = None
        for e in evs:
            k = e["kind"]
            if k == "gig_booked" and cur is not None:
                via_offer = (g, e["driverId"]) in offer_yes
                spells.append((cur, e["at"], "offer" if via_offer else "booked", reopened))
                cur = None
                booked_by = (e["at"], e["driverId"], e["feeCents"], via_offer)
            elif k in ("gig_dropped", "no_show") and cur is None:
                if booked_by and k == "gig_dropped":
                    drops.append(drop_row(booked_by, e["at"], True, fam, w, g, oid, r, o0, lpa[oid], cov30, reach, drv))
                booked_by = None
                cur, reopened = e["at"], True
            elif k in ("gig_started", "picked_up") and booked_by:
                drops.append(drop_row(booked_by, e["at"], False, fam, w, g, oid, r, o0, lpa[oid], cov30, reach, drv))
                booked_by = None
            elif k == "gig_expired" and cur is not None:
                spells.append((cur, e["at"], "expired", reopened))
                cur = None
        if cur is not None:
            spells.append((cur, hard_end, "censored", reopened))
        urgent_t = min(closes[oid]) if closes.get(oid) else None
        same_day = o0["option"] == "same_day"
        drive = minutes(a, b)
        for (ts, te, how, reo) in spells:
            te = min(te, hard_end) if how != "booked" else te
            k = 0
            t = ts
            while (t <= te) if how in ("booked", "offer") else (t < te):
                t_next = t + PERIOD
                y = int(how == "booked" and t <= te < t_next)
                if how == "offer" and t <= te < t_next:
                    break  # booked through a direct offer: censored here
                L = lpa_at(lpa[oid], t)
                f = fee_at(t)
                nview = len({d for tv, d, _ in order_views[oid] if tv < t})
                rows.append({
                    "w": w, "fam": fam, "gig": g, "order": oid, "spell": f"{w}:{g}:{ts}", "y": y,
                    "t": t, "fee_ratio": f / ref, "first_ratio": first_fee_order / ref,
                    "raised": int(f > first_fee_order + 1), "since_raise_h": since_change(t), "hrs_left": (L - t) / 60, "hour": (t % DAY) / 60,
                    "dow": (t // DAY) % 7, "cov30": cov30[a], "reach_a": reach[a], "reach_b": reach[b],
                    "age_h": (t - first_post[oid]) / 60, "gig_age_h": (t - ts) / 60, "viewers": nview,
                    "reopened": int(reo), "urgent": int(urgent_t is not None and t >= urgent_t),
                    "priv_a": int(leg["pickup"]["privateAddress"]), "priv_b": int(leg["delivery"]["privateAddress"]),
                    "same_day": int(same_day), "premium": int(leg["car"]["premium"]), "drive_h": drive / 60,
                    "ready_in_h": (leg["pickup"]["window"]["from"] - t) / 60,
                    "days_ahead": max(0, leg["pickup"]["window"]["from"] // DAY - t // DAY),
                    "ref": ref, "price": o0["priceCents"], "end": how,
                })
                if y:
                    break
                t = t_next
                k += 1
    return rows, drops, dict(n_skip)


def drop_row(booked_by, t_out, dropped, fam, w, g, oid, r, o0, lpa_hist, cov30, reach, drv):
    tb, did, fee, via_offer = booked_by
    leg = o0["legs"][0]
    L = lpa_at(lpa_hist, tb)
    d = drv.get(did, {"drops": 0, "completedGigs": 0, "rating": 4.7})
    return {"w": w, "fam": fam, "gig": g, "order": oid, "y": int(dropped), "fee_ratio": fee / r["referenceFeeCents"],
            "hold_h": max(0.0, (L - tb) / 60), "hour": (tb % DAY) / 60, "cov30": cov30[leg["pickup"]["placeId"]],
            "reach_b": reach[leg["delivery"]["placeId"]], "drive_h": minutes(leg["pickup"]["placeId"], leg["delivery"]["placeId"]) / 60,
            "drv_drop_rate": d["drops"] / (1 + d["completedGigs"] + d["drops"]), "drv_rating": d["rating"],
            "priv_a": int(leg["pickup"]["privateAddress"]), "same_day": int(o0["option"] == "same_day"), "via_offer": int(via_offer),
            "t_out_h": (t_out - tb) / 60}


def build_all():
    tags = tag_of_worlds()
    rows, drops, skips = [], [], defaultdict(int)
    for w in sorted(os.listdir(RUNS)):
        if not (RUNS / w / "reveal.json").exists():
            continue
        fam = FAMILY.get(tags.get(w))
        if fam is None:   # a run without a known tag (e.g. written while this script was developed): skip
            continue
        r, d, s = build_world(w, fam)
        rows += r
        drops += d
        for k, v in s.items():
            skips[k] += v
    return rows, drops, dict(skips)


# ---------------------------------------------------------------------------------------------- features
HAZ_FEATURES = None  # filled by hz_features names


def hz_x(r):
    """Feature vector for the booking hazard. Pure python (the policy evaluates it online from hazard.json)."""
    f = r["fee_ratio"]
    lc = math.log1p(r["cov30"])
    hl = max(-3.0, min(48.0, r["hrs_left"]))
    h = r["hour"]
    age = max(0.0, r["age_h"])
    x = {
        "fee_lo": min(f, 1.0), "fee_mid": min(0.3, max(0.0, f - 1.0)), "fee_hi": max(0.0, f - 1.3),
        "fee_x_lcov": (min(f, 1.3) - 1.0) * (lc - 4.5),
        "fresh_raise": float(r.get("since_raise_h", 99) < 0.5),
        "lcov": lc, "lreach_b": math.log1p(r["reach_b"]), "lreach_a": math.log1p(r["reach_a"]),
        "hl": hl, "hl_2": max(0.0, hl - 2), "hl_5": max(0.0, hl - 5), "hl_10": max(0.0, hl - 10), "hl_20": max(0.0, hl - 20),
        "hl_neg": min(0.0, hl),
        "h_night": float(h >= 23 or h < 7), "h_7_9": float(7 <= h < 9), "h_12_15": float(12 <= h < 15),
        "h_15_18": float(15 <= h < 18), "h_18_21": float(18 <= h < 21), "h_21_23": float(21 <= h < 23),
        "sat": float(r["dow"] == 5), "sun": float(r["dow"] == 6), "mon": float(r["dow"] == 0), "fri": float(r["dow"] == 4),
        "lage": math.log1p(age), "first_period": float(r["gig_age_h"] < PERIOD / 60 and not r["reopened"]),
        "fp_x_lcov": float(r["gig_age_h"] < PERIOD / 60 and not r["reopened"]) * lc,
        "fp_x_night": float(r["gig_age_h"] < PERIOD / 60 and not r["reopened"]) * float(h >= 21 or h < 7),
        "fp_x_fee": float(r["gig_age_h"] < PERIOD / 60 and not r["reopened"]) * (min(f, 1.3) - 1.0),
        "night_x_lcov": float(h >= 23 or h < 7) * lc, "hl6_x_fee": float(hl < 6) * (min(f, 1.3) - 1.0),
        "fam_old_x_fee": float(r.get("fam") == "smart_old") * (min(f, 1.3) - 1.0),
        "lviewers": math.log1p(r["viewers"]), "raised": float(r["raised"]), "reopened": float(r["reopened"]),
        "urgent": float(r["urgent"]), "priv_a": float(r["priv_a"]), "priv_b": float(r["priv_b"]),
        "same_day": float(r["same_day"]), "premium": float(r["premium"]), "drive_h": min(10.0, r["drive_h"]),
        "days_ahead": float(min(3, r["days_ahead"])), "not_ready": float(r["ready_in_h"] > 0),
        "fam_econ": float(r.get("fam") == "econ"), "fam_smart": float(r.get("fam") == "smart"),
        "fam_old": float(r.get("fam") == "smart_old"),
    }
    return x


DECISION_DROP = ("lviewers",)  # outcome-like covariates left out of the model the DP uses


def hz_x_dec(r):
    x = hz_x(r)
    for k in DECISION_DROP:
        x.pop(k)
    return x


RAW = ["fee_ratio", "since_raise_h", "cov30", "hrs_left", "hour", "dow", "age_h", "gig_age_h", "viewers", "raised", "reopened", "urgent",
       "priv_a", "priv_b", "same_day", "premium", "drive_h", "days_ahead", "ready_in_h", "reach_a", "reach_b"]
FAMS = ["cand6", "econ", "smart", "smart_old"]


def raw_x(r):
    return [float(r[k]) for k in RAW] + [float(FAMS.index(r["fam"]))]


def dr_x(r):
    f = r["fee_ratio"]
    hh = min(72.0, r["hold_h"])
    h = r["hour"]
    return {"fee": f, "fee_m1": max(0.0, f - 1.0), "lhold": math.log1p(hh), "hold_gt24": float(hh > 24),
            "night": float(h >= 22 or h < 7), "lcov": math.log1p(r["cov30"]), "lreach_b": math.log1p(r["reach_b"]),
            "drive_h": min(10.0, r["drive_h"]), "drv_drop_rate": r["drv_drop_rate"], "priv_a": float(r["priv_a"]),
            "same_day": float(r["same_day"])}


def matrix(rows, fx):
    names = list(fx(rows[0]).keys())
    X = np.array([list(fx(r).values()) for r in rows], dtype=float)
    return X, names


# ---------------------------------------------------------------------------------------------- fitting
def fit_logit(X, y, names, l2=1.0, fixed=None):
    """L2-penalised logistic regression (standardised features) by L-BFGS; `fixed` = {name: coef} held fixed (offset)."""
    from scipy.optimize import minimize
    fixed = fixed or {}
    free = [i for i, n in enumerate(names) if n not in fixed]
    off = sum(X[:, names.index(n)] * v for n, v in fixed.items()) if fixed else np.zeros(len(y))
    Z = X[:, free]
    mu, sd = Z.mean(0), Z.std(0) + 1e-9
    Z = (Z - mu) / sd

    def f(w):
        z = w[0] + Z @ w[1:] + off
        p = 1 / (1 + np.exp(-z))
        ll = np.logaddexp(0, z) - y * z
        g = p - y
        return ll.sum() + 0.5 * l2 * w[1:] @ w[1:], np.concatenate([[g.sum()], Z.T @ g + l2 * w[1:]])

    w = minimize(f, np.zeros(len(free) + 1), jac=True, method="L-BFGS-B", options={"maxiter": 2000}).x
    coef = np.zeros(len(names))
    coef[free] = w[1:] / sd
    for n, v in fixed.items():
        coef[names.index(n)] = v
    b0 = float(w[0] - (w[1:] * mu / sd).sum())
    return {"names": names, "coef": [float(c) for c in coef], "intercept": b0, "fixed": fixed}


def predict(model, X):
    z = model["intercept"] + X @ np.array(model["coef"])
    return 1 / (1 + np.exp(-z))


def logit_one(model, x):
    z = model["intercept"] + sum(c * x[n] for n, c in zip(model["names"], model["coef"]))
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


def logloss(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def auc(p, y):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p))


def calib(p, y, bins=(0, .01, .03, .06, .1, .2, .35, .5, .7, 1.01)):
    out = []
    for lo, hi in zip(bins, bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum():
            out.append((f"{lo:.2f}-{hi:.2f}", int(m.sum()), round(float(p[m].mean()), 4), round(float(y[m].mean()), 4)))
    return out


def raise_experiments(rows, pred=None):
    """Natural experiments on raises (policy-timed, not state-timed), as a check on the pooled fee coefficient.
    (a) CANDIDATE6 raises 0.9 -> 1.0 exactly 90 min after posting; econ (datagen3) does not. Diff-in-diff of the
        30-min booking probability, age 90-120 vs 60-90 min, gigs that opened at 0.9 and are > 4 h from lastPickupAt.
    (b) 3-4 h before lastPickupAt the old smart policy shows 1.7, econ (datagen3) 1.1: same clock, +0.6 fee."""
    val = (lambda i, r: r["y"]) if pred is None else (lambda i, r: pred[i])

    def p30(sel):
        n = sum(1 for r in rows if sel(r)); k = sum(val(i, r) for i, r in enumerate(rows) if sel(r))
        return float(k) / max(1, n), n
    out = {}
    base = lambda r, fam, lo, hi: (r["fam"] == fam and not r["reopened"] and abs(r["first_ratio"] - 0.9) < 0.02
                                   and r["hrs_left"] > 4 and lo <= r["gig_age_h"] * 60 < hi)
    for fam in ("cand6", "econ"):
        (pre, n1), (post, n2) = p30(lambda r: base(r, fam, 60, 90)), p30(lambda r: base(r, fam, 90, 120))
        out[f"step90_{fam}"] = {"h_pre": pre, "h_post": post, "n": [n1, n2]}
    lo = lambda h: math.log(h / (1 - h))
    c, e = out["step90_cand6"], out["step90_econ"]
    out["step90_did_logodds"] = (lo(c["h_post"]) - lo(c["h_pre"])) - (lo(e["h_post"]) - lo(e["h_pre"]))
    sel = lambda fam: (lambda r: r["fam"] == fam and not r["reopened"] and not r["urgent"] and r["gig_age_h"] > 3 and 3 <= r["hrs_left"] < 4)
    hs, ns = p30(sel("smart")); he, ne = p30(sel("econ"))
    hs0, _ = p30(lambda r: r["fam"] == "smart" and not r["reopened"] and r["gig_age_h"] > 3 and 5 <= r["hrs_left"] < 7)
    he0, _ = p30(lambda r: r["fam"] == "econ" and not r["reopened"] and r["gig_age_h"] > 3 and 5 <= r["hrs_left"] < 7)
    out["late_smart17_vs_econ11"] = {"h_smart": hs, "h_econ": he, "n": [ns, ne], "h_smart_pre": hs0, "h_econ_pre": he0,
                                     "did_logodds": (lo(hs) - lo(hs0)) - (lo(he) - lo(he0))}
    out["slope_above_1p1_per_unit"] = out["late_smart17_vs_econ11"]["did_logodds"] / 0.6
    return out


# ---------------------------------------------------------------------------------------------- DP
def solve_dp(hz, dr, gig, levels=LEVELS, raise_pen=0.03, late_cost=2.2, horizon_buffer_h=3.0, drop_delay_p=6,
             max_periods=6 * 72, rise_k=0.2):
    """Finite-horizon DP for one gig. gig: t_post (minute), lpa (lastPickupAt), cov30, reach_a, reach_b, priv_a, priv_b,
    same_day, premium, drive_h, ready_from. Costs in units of the typical fee.
    State (period k, level i, periods since the last raise s in {0,1,2,>=3}); a raise makes the next 3 periods "fresh"
    (the hazard's fresh_raise burst: drivers who were waiting for it book). Action: keep, or raise to any higher level
    (+raise_pen per raise). Drivers learn "booked fee / first viewed fee": a booking at f_j after opening at f_0 costs
    rise_k * (f_j / f_0 - 1) extra (future gigs wait longer). Booking at level j in period k costs f_j + p_drop * (V(k+d, j) - f_j)
    (a dropped gig comes back later at the same fee; the dropping driver is not paid). Horizon = lastPickupAt -
    horizon_buffer_h (= deadline_close): unbooked there costs late_cost. One DP per opening level (raised is relative
    to the opening). Returns (expected cost, schedule [(minute, level)], P(booked by horizon), T)."""
    t0 = gig["t_post"]
    T = int(max(1, min(max_periods, (gig["lpa"] - horizon_buffer_h * 60 - t0) // PERIOD)))
    nL = len(levels)
    H0 = np.zeros((T, nL)); H1 = np.zeros((T, nL)); HF = np.zeros((T, nL)); PD = np.zeros((T, nL))
    for k in range(T):
        t = t0 + k * PERIOD
        for i, f in enumerate(levels):
            H0[k, i] = logit_one(hz, hz_x_dec(state_row(gig, t, f, raised=0, k=k)))
            H1[k, i] = logit_one(hz, hz_x_dec(state_row(gig, t, f, raised=1, k=k)))
            HF[k, i] = logit_one(hz, hz_x_dec(state_row(gig, t, f, raised=1, k=k, since_raise_h=0.1)))
            PD[k, i] = logit_one(dr, dr_x(drop_state(gig, t, f)))
    best = None
    for i0 in range(nL):
        fl = np.array(levels) + rise_k * (np.array(levels) / levels[i0] - 1)   # booking cost incl. the learning cost
        V = np.full((T + 1, nL, 4), 1e9)
        V[T, i0:, :] = late_cost
        A = np.zeros((T, nL, 4), dtype=int)
        for k in range(T - 1, -1, -1):
            kd = min(T, k + drop_delay_p)
            for i in range(i0, nL):
                for sr in range(4):
                    h = H0[k, i] if i == i0 else (HF[k, i] if sr < 3 else H1[k, i])
                    s2 = min(sr + 1, 3)
                    c_best = h * (fl[i] + PD[k, i] * (V[kd, i, 3] - fl[i])) + (1 - h) * V[k + 1, i, s2]
                    a_best = i
                    for j in range(i + 1, nL):
                        h = HF[k, j]
                        c = raise_pen + h * (fl[j] + PD[k, j] * (V[kd, j, 3] - fl[j])) + (1 - h) * V[k + 1, j, 1]
                        if c < c_best - 1e-12:
                            c_best, a_best = c, j
                    V[k, i, sr] = c_best
                    A[k, i, sr] = a_best
        if A[0, i0, 3] != i0:   # raising at once = opening higher (covered by that opening's DP)
            continue
        if best is None or V[0, i0, 3] < best[0]:
            best = (float(V[0, i0, 3]), i0, A.copy())
    cost, i0, A = best
    sched, i, sr, alive = [(t0, levels[i0])], i0, 3, 1.0
    for k in range(T):
        j = A[k, i, sr]
        if j != i:
            sched.append((t0 + k * PERIOD, levels[j]))
            h, sr = HF[k, j], 1
        else:
            h = H0[k, i] if i == i0 else (HF[k, i] if sr < 3 else H1[k, i])
            sr = min(sr + 1, 3)
        i = j
        alive *= 1 - h
    return cost, sched, 1 - alive, T


def state_row(gig, t, f, raised, k, since_raise_h=99.0):
    return {"fee_ratio": f, "cov30": gig["cov30"], "hrs_left": (gig["lpa"] - t) / 60, "hour": (t % DAY) / 60,
            "dow": (t // DAY) % 7, "reach_b": gig["reach_b"], "reach_a": gig["reach_a"],
            "age_h": (t - gig.get("first_post", gig["t_post"])) / 60, "gig_age_h": k * PERIOD / 60,
            "reopened": 0, "viewers": gig.get("viewers0", 0) + min(k, 6) * gig.get("view_rate", 1.0), "raised": raised,
            "urgent": 0, "priv_a": gig["priv_a"], "priv_b": gig["priv_b"], "same_day": gig["same_day"],
            "premium": gig["premium"], "drive_h": gig["drive_h"], "ready_in_h": (gig["ready_from"] - t) / 60,
            "days_ahead": max(0, gig["ready_from"] // DAY - t // DAY), "fam": gig.get("fam", "cand6"),
            "since_raise_h": since_raise_h}


# ---------------------------------------------------------------------------------------------- main
def split_worlds(rows, frac=0.25):
    """Hold out ~25% of the worlds of each policy family (deterministic)."""
    import hashlib
    by = defaultdict(set)
    for r in rows:
        by[r["fam"]].add(r["w"])
    test = set()
    for fam, ws in by.items():
        ws = sorted(ws, key=lambda w: hashlib.md5(w.encode()).hexdigest())
        test |= set(ws[:max(1, round(frac * len(ws)))])
    return test


def fit_models(rows_all, drops, verbose=True):
    """Hazard: fitted on the cand6 / econ / smart families. The old smart family (datagen1: weeks at 50-80% on time,
    every gig on a 30-min urgent ramp) is left out: its drivers had learned to wait for ramps and its >1.3 fees are
    all urgent rescues; including it flips the sign of the fee slope below 1.0.
    Fee slope above 1.3 is not identified from pooled data (only urgent / hard gigs sit there; pooled slope < 0), so it
    is fixed at 0 (see below); the natural experiments are reported next to the model's reproduction of them."""
    log = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    exp = raise_experiments(rows_all)
    log("raise experiments (observed):", json.dumps(exp, default=float)[:700])
    rows = [r for r in rows_all if r["fam"] != "smart_old"]
    test = split_worlds(rows)
    y = np.array([r["y"] for r in rows], dtype=float)
    te = np.array([r["w"] in test for r in rows])
    cand = np.array([r["fam"] == "cand6" for r in rows])
    out = {"n_rows": len(rows), "n_spells": len({r["spell"] for r in rows}), "n_book": int(y.sum()),
           "test_worlds": sorted(test), "raise_experiments": exp, "families": sorted({r["fam"] for r in rows})}
    Xd, nd_ = matrix(rows, hz_x_dec)
    keep = [i for i, n in enumerate(nd_) if n not in ("fam_old", "fam_old_x_fee")]
    Xd, nd_ = Xd[:, keep], [nd_[i] for i in keep]
    # Above 1.3x the pooled slope is negative (only urgent rescues and hard gigs sit there) and fixing it to the
    # 1.1 -> 1.7 experiment distorts the other fee terms (tried: step90 then over-predicted 2x). So it is fixed at 0:
    # monotone and conservative -- the DP gets no modelled gain from going above 1.3 (except the raise burst).
    fixed = {"fee_hi": 0.0}
    out["fee_hi_fixed"] = fixed["fee_hi"]
    res = {}
    for tag, fx in (("full", hz_x), ("decision", hz_x_dec)):
        X, names = matrix(rows, fx)
        kk = [i for i, n in enumerate(names) if n not in ("fam_old", "fam_old_x_fee")]
        X, names = X[:, kk], [names[i] for i in kk]
        m = fit_logit(X[~te], y[~te], names, fixed=fixed)
        p = predict(m, X[te])
        base = np.full(te.sum(), y[~te].mean())
        res[tag] = (m, X, names)
        out[f"valid_{tag}"] = {"logloss": logloss(p, y[te]), "logloss_const": logloss(base, y[te]), "auc": auc(p, y[te]),
                               "logloss_cand6": logloss(p[cand[te]], y[te][cand[te]]),
                               "auc_cand6": auc(p[cand[te]], y[te][cand[te]]),
                               "calibration": calib(p, y[te]), "calibration_cand6": calib(p[cand[te]], y[te][cand[te]])}
        log(f"[{tag}] held-out logloss {out[f'valid_{tag}']['logloss']:.4f} (const {out[f'valid_{tag}']['logloss_const']:.4f}) "
            f"AUC {out[f'valid_{tag}']['auc']:.3f} | cand6 logloss {out[f'valid_{tag}']['logloss_cand6']:.4f} AUC {out[f'valid_{tag}']['auc_cand6']:.3f}")
        for c in out[f"valid_{tag}"]["calibration_cand6"]:
            log("   calib cand6 (bin, n, pred, obs)", c)
    m_full = fit_logit(res["decision"][1], y, res["decision"][2], fixed=fixed)
    out["hazard"] = m_full
    pexp = raise_experiments(rows, predict(m_full, res["decision"][1]))
    out["raise_experiments_model"] = pexp
    log(f"model vs observed: step90 DiD {pexp['step90_did_logodds']:.2f} vs {exp['step90_did_logodds']:.2f}; "
        f"late 1.1->1.7 DiD {pexp['late_smart17_vs_econ11']['did_logodds']:.2f} vs {exp['late_smart17_vs_econ11']['did_logodds']:.2f}; "
        f"cand6 step90 h {pexp['step90_cand6']['h_pre']:.4f}->{pexp['step90_cand6']['h_post']:.4f} "
        f"(obs {exp['step90_cand6']['h_pre']:.4f}->{exp['step90_cand6']['h_post']:.4f})")
    # gradient boosting with a monotone fee constraint, as a flexible benchmark
    from sklearn.ensemble import HistGradientBoostingClassifier
    R = np.array([raw_x(r) for r in rows])
    mono = [1 if k == "fee_ratio" else 0 for k in RAW] + [0]
    hgb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, monotonic_cst=mono,
                                         categorical_features=[len(RAW)], l2_regularization=1.0, random_state=0)
    hgb.fit(R[~te], y[~te])
    ph = hgb.predict_proba(R[te])[:, 1]
    out["valid_hgb"] = {"logloss": logloss(ph, y[te]), "auc": auc(ph, y[te]), "auc_cand6": auc(ph[cand[te]], y[te][cand[te]]),
                        "logloss_cand6": logloss(ph[cand[te]], y[te][cand[te]])}
    log(f"[hgb monotone] held-out logloss {out['valid_hgb']['logloss']:.4f} AUC {out['valid_hgb']['auc']:.3f} cand6 AUC {out['valid_hgb']['auc_cand6']:.3f}")
    # HGB partial dependence of fee for cand6 rows (average over their states)
    idx = np.where(cand)[0][::7]
    pdp = {}
    for f in LEVELS:
        Rf = R[idx].copy(); Rf[:, 0] = f; Rf[:, RAW.index("raised")] = 0
        pdp[f] = float(hgb.predict_proba(Rf)[:, 1].mean())
    out["hgb_fee_pdp_cand6"] = pdp
    log("HGB fee partial dependence (cand6 states):", {k: round(v, 4) for k, v in pdp.items()})
    # drop model
    yd = np.array([d["y"] for d in drops], dtype=float)
    Xd, nd = matrix(drops, dr_x)
    ted = np.array([d["w"] in test for d in drops])
    md = fit_logit(Xd[~ted], yd[~ted], nd)
    pdv = predict(md, Xd[ted])
    out["valid_drop"] = {"logloss": logloss(pdv, yd[ted]), "logloss_const": logloss(np.full(ted.sum(), yd[~ted].mean()), yd[ted]),
                         "auc": auc(pdv, yd[ted]), "calibration": calib(pdv, yd[ted], bins=(0, .03, .06, .1, .15, .25, .4, 1.01))}
    log(f"[drop] held-out logloss {out['valid_drop']['logloss']:.4f} (const {out['valid_drop']['logloss_const']:.4f}) AUC {out['valid_drop']['auc']:.3f}")
    out["drop"] = fit_logit(Xd, yd, nd)
    return out


HL_BUCKETS = [(3, 6), (6, 10), (10, 18), (18, 30), (30, 48), (48, 200)]
COV_BUCKETS = [(0, 5), (6, 20), (21, 60), (61, 10000)]


def bucket(v, bs):
    for i, (lo, hi) in enumerate(bs):
        if lo <= v < hi + (1 if bs is COV_BUCKETS else 0):
            return i
    return None


def late_cost_default(urgent_fee=1.5, p_late_warn=0.5, refund_frac=0.35, price_ratio=1.6, trust=0.3, sla=0.6):
    """Cost (x typical fee) of reaching deadline_close unbooked: the urgent rescue fee + P(late | warned) x
    (refund + dealer-trust loss + SLA shadow price). Defaults from reveal6: price/typical 1.6, ~45-50% of warned late."""
    return urgent_fee + p_late_warn * (refund_frac * price_ratio + trust + sla)


def gig_states(rows, fam="cand6"):
    """First-posting states of the policy family's single-leg orders (one per order)."""
    seen, out = set(), []
    for r in rows:
        if r["fam"] != fam or r["gig_age_h"] != 0 or r["reopened"] or (r["w"], r["order"]) in seen or r["age_h"] > 0.01:
            continue
        seen.add((r["w"], r["order"]))
        out.append({"t_post": r["t"], "lpa": r["t"] + r["hrs_left"] * 60, "cov30": r["cov30"], "reach_a": r["reach_a"],
                    "reach_b": r["reach_b"], "priv_a": r["priv_a"], "priv_b": r["priv_b"], "same_day": r["same_day"],
                    "premium": r["premium"], "drive_h": r["drive_h"], "ready_from": r["t"] + r["ready_in_h"] * 60,
                    "fam": "cand6"})
    return out


def policy_table(hz, dr, states, late_cost, raise_pen, levels=LEVELS, rise_k=0.2):
    cells = defaultdict(list)
    for g in states:
        hl0 = (g["lpa"] - g["t_post"]) / 60
        bi, ci = bucket(hl0, HL_BUCKETS), bucket(g["cov30"], COV_BUCKETS)
        if bi is None or ci is None:
            continue
        cost, sched, pb, T = solve_dp(hz, dr, g, levels=levels, raise_pen=raise_pen, late_cost=late_cost, rise_k=rise_k)
        # status quo (cand6-like): open 0.9, 1.0 after 90 min, 1.1 at L-10h
        sq = schedule_cost(hz, dr, g, [(g["t_post"], 0.9), (g["t_post"] + 90, 1.0), (g["lpa"] - 600, 1.1)], late_cost, raise_pen,
                           rise_k=rise_k)
        steps = [((g["lpa"] - t) / 60, f) for t, f in sched[1:]]
        cells[(bi, ci)].append({"open": sched[0][1], "steps": steps, "cost": cost, "p_book": pb, "sq_cost": sq[0],
                                "sq_p_book": sq[1], "final": sched[-1][1]})
    table = []
    for (bi, ci), v in sorted(cells.items()):
        opens = np.array([x["open"] for x in v])
        first_up = [x["steps"][0] for x in v if x["steps"]]
        # schedule as "level reached by h hours before lastPickupAt" (median over gigs in the cell)
        reach_at = {}
        for f in levels[1:]:
            hs = [next((h for h, ff in x["steps"] if ff >= f), None) if x["open"] < f else 99 for x in v]
            hs = [h for h in hs if h is not None]
            if len(hs) >= len(v) / 2:
                reach_at[f] = round(float(np.median(hs)), 1)
        table.append({"hl_bucket": HL_BUCKETS[bi], "cov_bucket": COV_BUCKETS[ci], "n": len(v),
                      "open": float(np.median(opens)), "open_mean": round(float(opens.mean()), 3),
                      "first_step_h_before_lpa": round(float(np.median([h for h, _ in first_up])), 1) if first_up else None,
                      "first_step_level": float(np.median([f for _, f in first_up])) if first_up else None,
                      "share_with_step": round(len(first_up) / len(v), 2),
                      "level_by_h_before_lpa": reach_at, "final_median": float(np.median([x["final"] for x in v])),
                      "exp_cost": round(float(np.mean([x["cost"] for x in v])), 3),
                      "sq_cost": round(float(np.mean([x["sq_cost"] for x in v])), 3),
                      "p_book": round(float(np.mean([x["p_book"] for x in v])), 3),
                      "sq_p_book": round(float(np.mean([x["sq_p_book"] for x in v])), 3)})
    return table


def schedule_cost(hz, dr, gig, sched, late_cost, raise_pen, horizon_buffer_h=3.0, drop_delay_p=6, rise_k=0.2):
    """Expected cost (x typical) of a fixed schedule under the models (drop -> re-enter later at the same fee)."""
    t0 = gig["t_post"]
    T = int(max(1, min(6 * 72, (gig["lpa"] - horizon_buffer_h * 60 - t0) // PERIOD)))
    lv = []
    for k in range(T):
        t = t0 + k * PERIOD
        f = sched[0][1]
        for ts, ff in sched:
            if ts <= t:
                f = max(f, ff)
        lv.append(f)
    last_up = [None] * T
    for k in range(1, T):
        last_up[k] = k if lv[k] > lv[k - 1] else last_up[k - 1]
    H = [logit_one(hz, hz_x_dec(state_row(gig, t0 + k * PERIOD, lv[k], raised=lv[k] > lv[0], k=k,
                                          since_raise_h=99.0 if last_up[k] is None else (k - last_up[k]) * PERIOD / 60)))
         for k in range(T)]
    PD = [logit_one(dr, dr_x(drop_state(gig, t0 + k * PERIOD, lv[k]))) for k in range(T)]
    V = [0.0] * (T + 1)
    V[T] = late_cost
    for k in range(T - 1, -1, -1):
        kd = min(T, k + drop_delay_p)
        fk = lv[k] + rise_k * (lv[k] / lv[0] - 1)
        book = fk + PD[k] * (V[kd] - fk)
        V[k] = H[k] * book + (1 - H[k]) * V[k + 1] + (raise_pen if k + 1 < T and lv[k + 1] > lv[k] else 0.0)
    alive = 1.0
    for h in H:
        alive *= 1 - h
    return V[0], 1 - alive


def drop_state(gig, t, f):
    return {"fee_ratio": f, "hold_h": max(0, (gig["lpa"] - t) / 60), "hour": (t % DAY) / 60, "cov30": gig["cov30"],
            "reach_b": gig["reach_b"], "drive_h": gig["drive_h"], "drv_drop_rate": gig.get("drv_drop_rate", 0.06),
            "priv_a": gig["priv_a"], "same_day": gig["same_day"]}


def main():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if CACHE.exists() and "--rebuild" not in sys.argv:
        rows, drops, skips = pickle.load(open(CACHE, "rb"))
    else:
        rows, drops, skips = build_all()
        pickle.dump((rows, drops, skips), open(CACHE, "wb"))
    print(f"hazard rows {len(rows)}, spells {len({r['spell'] for r in rows})}, bookings {sum(r['y'] for r in rows)}; "
          f"drop rows {len(drops)}; skipped gigs {skips}")
    drops = [d for d in drops if not d["via_offer"]]
    fit_path = CACHE.parent / "fit.pkl"
    if fit_path.exists() and "--refit" not in sys.argv and "--rebuild" not in sys.argv:
        fit = pickle.load(open(fit_path, "rb"))
    else:
        fit = fit_models(rows, drops)
        pickle.dump(fit, open(fit_path, "wb"))
    hz, dr = fit["hazard"], fit["drop"]
    for k in ("hazard", "drop"):
        print(k, {n: round(c, 3) for n, c in zip(fit[k]["names"], fit[k]["coef"])}, "b0", round(fit[k]["intercept"], 3))
    # fee effect: P(booked within 60 min) at a flat fee, CANDIDATE6 posting states, by coverage bucket
    import random
    states = gig_states(rows)
    random.seed(0)
    sub = random.sample(states, min(len(states), int(os.environ.get("HAZ_DP_N", 600))))
    eff = {}
    for ci, cb in enumerate(COV_BUCKETS):
        gs = [g for g in sub if bucket(g["cov30"], COV_BUCKETS) == ci]
        eff[str(cb)] = {"n": len(gs)}
        for f in (0.9, 1.0, 1.1, 1.2, 1.3, 1.4):
            p60 = []
            for g in gs:
                alive = 1.0
                for k in range(6):
                    alive *= 1 - logit_one(hz, hz_x_dec(state_row(g, g["t_post"] + k * PERIOD, f, raised=0, k=k)))
                p60.append(1 - alive)
            eff[str(cb)][f] = round(float(np.mean(p60)), 3)
    print("P(booked within 60 min of posting) at a flat fee, by pickup coverage:", json.dumps(eff))
    lc = late_cost_default()
    tables = {}
    for name, lcost, pen, rk in (("base", lc, 0.03, 0.2), ("late_low", 1.6, 0.03, 0.2), ("late_high", 3.5, 0.03, 0.2),
                                 ("no_learning", lc, 0.0, 0.0), ("learning_high", lc, 0.10, 0.5)):
        tables[name] = {"late_cost": lcost, "raise_pen": pen, "rise_k": rk, "table": policy_table(hz, dr, sub, lcost, pen, rise_k=rk)}
        print(f"policy table [{name}] late_cost {lcost:.2f} raise_pen {pen} rise_k {rk}")
        for r in tables[name]["table"]:
            print("  hl", r["hl_bucket"], "cov", r["cov_bucket"], "n", r["n"], "open", r["open"], f"({r['open_mean']})",
                  "levels by h-before-LPA", r["level_by_h_before_lpa"], "final", r["final_median"],
                  "cost", r["exp_cost"], "vs status quo", r["sq_cost"], "P(book)", r["p_book"], "sq", r["sq_p_book"])
    out = {
        "about": "Booking hazard per 10-min period (logit, features = lab.fit_hazard.hz_x_dec), drop model (dr_x), "
                 "and DP fee-schedule tables. Fees/costs in units of the typical fee x cars/legs. Built by lab/fit_hazard.py.",
        "period_min": PERIOD, "levels": LEVELS, "hazard": hz, "drop": dr,
        "validation": {k: fit[k] for k in fit if k.startswith("valid")},
        "raise_experiments": fit.get("raise_experiments"), "hgb_fee_pdp_cand6": fit.get("hgb_fee_pdp_cand6"),
        "n": {k: fit[k] for k in ("n_rows", "n_spells", "n_book")}, "test_worlds": fit["test_worlds"],
        "fee_effect_p60": eff, "hl_buckets": HL_BUCKETS, "cov_buckets": COV_BUCKETS, "policy": tables,
        "dp_defaults": {"horizon_buffer_h": 3.0, "drop_delay_p": 6, "late_cost": lc, "raise_pen": 0.03, "rise_k": 0.2,
                        "late_cost_formula": "urgent_fee 1.5 + P(late|warned) 0.5 x (refund 0.35 x price/typical 1.6 + trust 0.3 + SLA 0.6)"},
    }
    path = ROOT / "lab" / "models" / "hazard.json"
    path.write_text(json.dumps(out, default=float, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
