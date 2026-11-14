"""Econ: quote = argmax_p  P(win | p) * (p - E[cost]),  the "golden point" per request and option.

Win model (logistic in log price, learned online):
    P(win | p) = sigmoid( beta * (theta_w + theta_d[dealer] + theta_o[option] - log(p / list)) )
    theta_w   world price level (competitor level x dealer acceptance): SGD on every win/loss
    theta_d   per-dealer offset (competitor adapts per dealer + dealer trust): SGD, shrunk to 0
Cost model:
    E[cost] = fee_hat * typical fee  +  P(late) * late_cost * p  +  lam
    P(late) from the learned staffability model (lab/models/risk.json); options above risk_max are not offered.
Capacity / safety: inherited mu controller (Smart.safety) raises the risk penalty when warnings pile up.
"""
from __future__ import annotations

import math
from collections import defaultdict

from ..desk import DAY
from .smart import Smart

GRID = [0.85 + 0.025 * i for i in range(53)]  # p / list from 0.85 to 2.15


class Econ(Smart):
    NAME = "econ"
    DEFAULTS = {
        **Smart.DEFAULTS,
        "risk": 1, "scarce": 0, "safety": 1, "gate": 1,
        "beta": 8.0,            # slope of the win curve in log price
        "theta0": 0.30,         # initial log price level where P(win)=0.5  (exp(.30)=1.35 x list)
        "eta_w": 0.02, "eta_d": 0.04, "d_shrink": 0.995, "d_max": 0.3,
        "fee_hat": 1.1,         # expected driver fee / typical fee
        "late_cost": 0.6,       # expected loss if late, as share of price (refund + trust + SLA)
        "lam": 0.0,             # flat opportunity cost per order (cents) for scarce capacity
        "min_ev": 0.0,          # decline if best expected profit (cents) below this
        "opt_sd": 0.0, "opt_w3": 0.0,  # log offsets of option acceptance vs next_day
        "jitter": 0.0,
        "winmodel": 0,          # 1 = use lab/models/win.json: offline lane (pickup/delivery town), option, hour effects + beta
        "lane_w": 1.0,
        "eta_a": 0.0, "a_max": 0.3,
        "mu_eur": 0.0, "risk_hard": 1.0,   # (1) EV penalty in EUR per unit P(late); hard gate on P(late)
        "seg_fee": 0, "fee_priv": 1.30, "fee_short": 1.10, "fee_sdseg": 1.10, "fee_else": 0.98,   # (4)
        "war": 0, "war_n": 25, "war_loss": 0.75, "war_shift": -0.20,   # (5) price-war mode
        "inv_k": 0.0, "inv_radius": 60,   # Avellaneda-Stoikov inventory skew: cost += inv_k * typical * q / capacity
        "lane_cost": 0, "lane_n0": 10.0,      # cost per pickup town from realised fee/typical, shrunk to fee_hat
        "ekf": 0, "ekf_v0": 0.0225, "ekf_q": 0.0025,   # per-dealer EKF on the competitor offset (TrueSkill-style)
        "pulse": 0, "pulse_mult": 1.5, "pulse_skip_big": 0.15,   # rotation: starve half the dealers each day
        "adapt_k": 0.0, "adapt_big": 15, "adapt_small_w": 0.3,   # Stackelberg shadow cost per win (cents/100 per morning left)
        "beta_override": 0.0,
        "day_level": 0, "eta_day": 0.06,     # fast daily level, reset each morning (world level learns slower)
        "bulk": 0, "bulk_cap": 12, "bulk_frac": 0.1,      # bulk order (iceberg): cap wins per batch at min(cap, frac*yard drivers)
        "sd_prem": 0.0, "fri_sd": 0.0,                    # same_day price premium; extra on Friday same_day
        "snow": 0, "snow_drive": 1.25, "snow_quote": 0.05,  # snow forecast handling
        "tradein_decl": 0,          # decline 2-leg (trade-in) requests (33% late under CANDIDATE2)
        "min_slack": 0,             # decline options with (deadline - ready - drive) below this many minutes
        "cost_pl_k": 0.0,           # job-specific expected payout: fee_est = typical*(fee_hat + cost_pl_k*P(late))
        # adaptive aggressiveness: once the week looks easy (projected OT high after day `adapt_day`), loosen
        "adaptive": 0, "adapt_from_day": 1, "adapt_ot": 0.965, "adapt_mu_eur": 20.0, "adapt_cost_pl_k": 0.0,
        "adapt_fee_hat": 0.95, "adapt_s2": 0.965,
        "outage": 0, "out_thr": 4.0, "out_n": 8, "out_shift": 0.2, "out_test": 0.26, "out_km": 80, "out_freeze": 1,
        "long_relief": 0.0, "long_min": 240, "lr_ot": 0.0,   # lr_ot: relief only while projected on-time >= lr_ot
          # scale risk penalties by (1-long_relief) for drives >= long_min (long hauls earn 3-5x)
        "peak": 0, "peak_k": 0.3, "peak_budget": 1.1,   # (6) smooth peak days: extra cost when today's wins exceed budget
        "opt_fee": 0, "fee_sd": 1.15, "fee_nd": 1.03, "fee_w3": 0.99,   # measured fee/typical by option (9.3k orders)   # online per-pickup-town offset (outage region / local moves), reset each morning          # how much of the offline lane effect to trust
    }

    def on_start(self):
        super().on_start()
        self.wm = None
        if self.p["winmodel"]:
            import json
            from pathlib import Path
            self.wm = json.loads((Path(__file__).resolve().parent.parent / "models" / "win.json").read_text())
            self.p["beta"] = self.p["beta_override"] or self.wm["beta"]
            self.p["theta0"] = self.wm["intercept"] + self.wm["world_mean"]
        self.theta_w = self.p["theta0"]
        self.theta_d = defaultdict(float)
        self.theta_a = defaultdict(float)
        self.recent = []
        self.batch_seen = defaultdict(int); self.batch_won = defaultdict(int); self.batch_of = {}
        self.theta_day = 0.0; self.theta_day_d = -1
        self.fee_sum = defaultdict(float); self.fee_n = defaultdict(int)   # realised fee/typical per pickup town
        self.ekf_mu = defaultdict(float); self.ekf_v = defaultdict(lambda: self.p["ekf_v0"]); self.ekf_day = {}          # recent real-quote outcomes (1 = lost)
        self.war_day = -1
        self.theta_a_day = -1
        self.out_obs = []; self.out_day = -1; self.out_region = set(); self.out_last = -999; self._near = {}
        self.pending: dict[str, tuple] = {}   # request -> (dealer, [(option, log ratio)])

    # ---- learning
    def on_event(self, e):
        super().on_event(e)
        k = e["kind"]
        if k == "order_won" and e["order"]["id"] in self.batch_of:
            self.batch_won[self.batch_of[e["order"]["id"]]] += 1
        if k == "ledger" and e["line"]["kind"] == "driver_fee" and e["line"].get("orderId") in self.orders:
            o = self.orders[e["line"]["orderId"]]
            rq = self.requests.get(o["id"])
            if rq:
                t = o["legs"][0]["pickup"]["placeId"]
                self.fee_sum[t] += -e["line"]["cents"] / rq["referenceFeeCents"]; self.fee_n[t] += 1
        if k in ("order_won", "order_lost"):
            rid = e["order"]["id"] if k == "order_won" else (e.get("requestId") or e.get("orderId"))
            pend = self.pending.pop(rid, None)
            if not pend:
                return
            dealer, quotes, lanes, town = pend
            if k == "order_won":
                won_opt = e["order"]["option"]
                lr = next((x for o, x in quotes if o == won_opt), quotes[0][1])
                y = 1.0
            else:
                lr = min(x for _, x in quotes)   # lost even our cheapest option
                y = 0.0
            day = e["at"] // DAY
            if self.p["war"]:
                self.recent = (self.recent + [1 - y])[-self.p["war_n"]:]
                h = (e["at"] % DAY) / 60
                if (self.war_day != day and len(self.recent) >= self.p["war_n"] and 10 <= h < 17 and e["at"] > 600
                        and sum(self.recent) / len(self.recent) >= self.p["war_loss"]):
                    self.war_day = day
                    self.count("war_mode")
                if self.war_day == day:
                    return   # freeze learning on the price-war day
            p = self.pwin(dealer, None, lr, lanes + self.theta_a[town])
            g = y - p
            if self.p["outage"]:
                self.outage_obs(e["at"], town, p, y)
                if self.p["out_freeze"] and self.in_outage(town, e["at"]):
                    self.count("out_learn_skip")
                    return
            if self.p["ekf"]:
                d0 = e["at"] // DAY
                if self.ekf_day.get(dealer) != d0:          # morning: competitor moved, widen
                    self.ekf_v[dealer] += self.p["ekf_q"]; self.ekf_day[dealer] = d0
                b = self.p["beta"]
                v = 1 / (1 / self.ekf_v[dealer] + b * b * p * (1 - p))
                self.ekf_mu[dealer] += v * b * g
                self.ekf_v[dealer] = v
                self.theta_w += self.p["eta_w"] * g * 0.5
                self.count("learn"); return
            if self.p["day_level"]:
                if self.theta_day_d != day:
                    self.theta_day, self.theta_day_d = 0.0, day
                self.theta_day = max(-0.25, min(0.25, self.theta_day + self.p["eta_day"] * g))
                self.theta_w += self.p["eta_w"] * 0.3 * g
            else:
                self.theta_w += self.p["eta_w"] * g
            td = self.theta_d[dealer] * self.p["d_shrink"] + self.p["eta_d"] * g
            self.theta_d[dealer] = max(-self.p["d_max"], min(self.p["d_max"], td))
            if self.p["eta_a"]:
                ta = self.theta_a[town] + self.p["eta_a"] * g
                self.theta_a[town] = max(-self.p["a_max"], min(self.p["a_max"], ta))
            self.count("learn")

    # ---- competitor outage (RULES: one region = a town + places within 80 km, one working day 08:00-18:00, ~+30% prices)
    def near(self, c):
        if c not in self._near:
            pl = self.ctx.places
            def dist(x, y):   # straight line (haversine), as the rules say
                la1, lo1, la2, lo2 = map(math.radians, (pl[x]["lat"], pl[x]["lon"], pl[y]["lat"], pl[y]["lon"]))
                h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
                return 12742 * math.asin(math.sqrt(h))
            self._near[c] = {t for t in pl if t == c or dist(c, t) <= self.p["out_km"]}
        return self._near[c]

    def in_outage(self, town, t):
        return self.out_day == t // DAY and 8 * 60 <= t % DAY < 18 * 60 and town in self.out_region

    def outage_obs(self, at, town, p, y):
        day, h = at // DAY, at % DAY
        if not (8 * 60 <= h < 18 * 60):
            return
        self.out_obs = [x for x in self.out_obs if x[0] // DAY == day] + [(at, town, p, y)]
        if self.out_day == day or at - self.out_last < 20:
            return
        self.out_last = at
        P, b = self.p, self.p["beta"] * self.p["out_test"]
        best, best_c = 0.0, None
        for c in {x[1] for x in self.out_obs}:
            reg = self.near(c)
            llr, n = 0.0, 0
            for _, t, pp, yy in self.out_obs:
                if t in reg:
                    pp = min(0.999, max(0.001, pp))
                    q = 1 / (1 + math.exp(-(math.log(pp / (1 - pp)) + b)))
                    llr += math.log(q / pp) if yy else math.log((1 - q) / (1 - pp))
                    n += 1
            if n >= P["out_n"] and llr > best:
                best, best_c = llr, c
        if best_c is not None and best > P["out_thr"]:
            self.out_day, self.out_region = day, self.near(best_c)
            self.count("outage_on")
            self.outage_info = (day, best_c, round(best, 1), at)

    def lane(self, r, option):
        if not self.wm:
            return 0.0
        wm, lw = self.wm, self.p["lane_w"]
        a, b = r["legs"][0]["pickup"]["placeId"], r["legs"][0]["delivery"]["placeId"]
        return lw * (wm["a"].get(a, 0) + wm["b"].get(b, 0)) + wm["o"].get(option or "next_day", 0) + wm["h"].get(str((r["arrivedAt"] % 1440) // 180), 0)

    def adapt_check(self, now):
        """Switch to the aggressive profile when the week is going well (and back if it stops going well)."""
        P = self.p
        if not hasattr(self, "_base_p"):
            self._base_p = {k: P[k] for k in ("mu_eur", "cost_pl_k", "fee_hat", "s2_target")}
            self.aggr = False
        proj = getattr(self, "proj_ot", None)
        easy = (now // DAY >= P["adapt_from_day"] and proj is not None and proj >= P["adapt_ot"]
                and len(self.orders) >= 60 and self.mu < 0.05)
        if easy and not self.aggr:
            P.update(mu_eur=P["adapt_mu_eur"], cost_pl_k=P["adapt_cost_pl_k"], fee_hat=P["adapt_fee_hat"], s2_target=P["adapt_s2"])
            self.aggr = True; self.count("adapt_on")
        elif not easy and self.aggr and (proj is None or proj < P["adapt_ot"] - 0.01):
            P.update(self._base_p); self.aggr = False; self.count("adapt_off")

    def pwin(self, dealer, option, log_ratio, lane=0.0):
        P = self.p
        off = P["opt_sd"] if option == "same_day" else P["opt_w3"] if option == "within_3_days" else 0.0
        tr = math.log(1 + 0.01 * self.trust_n[dealer]) if P["trust"] else 0.0
        war = P["war_shift"] if (P["war"] and self.war_day == self.now // DAY and (self.now % DAY) < 18 * 60) else 0.0
        dd = self.ekf_mu[dealer] if P["ekf"] else self.theta_d[dealer]
        if P["day_level"] and self.theta_day_d == self.now // DAY:
            dd += self.theta_day
        z = P["beta"] * (self.theta_w + dd + off + tr + lane + war - log_ratio)
        return 1 / (1 + math.exp(-max(-30, min(30, z))))

    # ---- quoting
    def price_quote(self, r):
        P = self.p
        if P["adaptive"]:
            self.adapt_check(r["arrivedAt"])
        if P["flu"]:
            self.mu = max(self.mu, self.flu_check(r["arrivedAt"]))
        if r["arrivedAt"] // DAY != self.theta_a_day:   # new day: regional shocks last one day
            self.theta_a.clear(); self.theta_a_day = r["arrivedAt"] // DAY
        legs = r["legs"]
        a, b = legs[0]["pickup"]["placeId"], legs[0]["delivery"]["placeId"]
        if P["gate"] and self.reach[a] + P["drop_w"] * self.reach[b] < P["min_reach"]:
            self.count("decl_supply")
            return self.decline(r)
        drive = sum(self.ctx.minutes(l["pickup"]["placeId"], l["delivery"]["placeId"]) for l in legs)
        ready = max(l["pickup"]["window"]["from"] for l in legs)
        snow_hit = False
        if P["snow"] and self.snow_at(a, b, ready):
            drive = int(drive * P["snow_drive"]); snow_hit = True
            self.count("snow_req")
        if P["bulk"] and r.get("batchId"):
            key = (r["batchId"], a, ready)
            self.batch_seen[key] += 1
            self.batch_of[r["id"]] = key
            if self.batch_seen[key] >= 3:
                cap = min(P["bulk_cap"], max(1, int(P["bulk_frac"] * len(self.homes[a]))))
                if self.batch_won[key] >= cap:
                    self.count("bulk_capped")
                    return self.decline(r)
        if P["tradein_decl"] and len(legs) > 1:
            self.count("tradein_decl")
            return self.decline(r)
        start = max(ready, r["respondBy"] + P["lead_min"])
        fee = P["fee_hat"] * r["referenceFeeCents"]
        if P["lane_cost"]:
            n0 = P["lane_n0"]
            ratio = (self.fee_sum[a] + n0 * P["fee_hat"]) / (self.fee_n[a] + n0)
            fee = ratio * r["referenceFeeCents"]
        if P["pulse"]:
            day = r["arrivedAt"] // DAY
            big = self.dealer_req[r["dealerId"]] / max(1, sum(self.dealer_req.values())) > P["pulse_skip_big"]
            grp = (sum(map(ord, r["dealerId"])) + day) % 2
            if not big and grp == 0 and day < 4:
                self.count("pulse_starve")
                return {o["kind"]: o["listPriceCents"] * P["pulse_mult"] for o in r["options"]}
        prices, quotes, lanes_seen = {}, [], []
        for o in r["options"]:
            if P["min_slack"] and o["deadline"] - max(ready, r["respondBy"]) - drive < P["min_slack"]:
                self.count(f"slack_decl_{o['kind']}")
                continue
            if P["gate"] and start + drive + P["slack_min"] > o["deadline"]:
                self.count(f"gate_{o['kind']}")
                continue
            pl = self.p_late(r, o) if self.risk_model is not None else 0.1
            relief = (1 - P["long_relief"]) if drive >= P["long_min"] and getattr(self, "proj_ot", 1.0) >= P["lr_ot"] and getattr(self, "flu_boost", 0.0) <= 0 else 1.0
            fee_o = fee * (1 + relief * P["cost_pl_k"] * pl / max(0.5, P["fee_hat"]))
            if pl > (P["risk_hard"] if P["mu_eur"] else P["risk_max"] * (1 - 0.5 * self.mu)):
                self.count(f"risk_decl_{o['kind']}")
                continue
            lst = o["listPriceCents"]
            if P["seg_fee"]:
                priv = any(l["pickup"]["privateAddress"] or l["delivery"]["privateAddress"] for l in legs)
                fac = P["fee_priv"] if priv else P["fee_short"] if drive < 60 else P["fee_sdseg"] if o["kind"] == "same_day" else P["fee_else"]
                fee = r["referenceFeeCents"] * fac
            elif P["opt_fee"]:
                fee = r["referenceFeeCents"] * (P["fee_sd"] if o["kind"] == "same_day" else P["fee_w3"] if o["kind"] == "within_3_days" else P["fee_nd"])
            ln = self.lane(r, o["kind"]) + self.theta_a[a]
            if P["outage"] and self.in_outage(a, r["respondBy"]):
                ln += P["out_shift"]
                self.count("out_priced")
            lanes_seen.append(ln)
            late_cost = P["late_cost"] * (1 + 2 * self.mu) * relief
            peak_cost = 0.0
            if P["peak"]:
                day = r["arrivedAt"] // DAY
                past = [self.wins_by_day.get(d, 0) for d in range(day) if self.quotes_by_day.get(d, 0) >= 20]
                ref = max(40.0, (sum(past) / len(past))) if past else 85.0   # only days we actually played
                over = self.wins_by_day.get(day, 0) - P["peak_budget"] * ref * min(1.0, ((r["arrivedAt"] % DAY) - 8 * 60) / 600 + 0.1)
                if over > 0:
                    peak_cost = P["peak_k"] * r["referenceFeeCents"] * over / max(10.0, ref) * 3
            adapt_cost = 0.0
            if P["adapt_k"]:
                day0 = r["arrivedAt"] // DAY
                mornings = max(0, 4 - day0)
                el = max(0.25, (r["arrivedAt"] - 8 * 60) / DAY)
                big = self.dealer_req[r["dealerId"]] / el >= P["adapt_big"] or self.trust_n[r["dealerId"]] >= 20
                adapt_cost = P["adapt_k"] * 100 * mornings * (1.0 if big else P["adapt_small_w"])
            inv_cost = 0.0
            if P["inv_k"]:
                q = 0
                for oo in self.orders.values():
                    if None not in oo["deliveredAt"]:
                        continue
                    if any(g in self.booked for g in self.gigs_of(oo["id"])):
                        continue
                    if self.ctx.minutes(oo["legs"][0]["pickup"]["placeId"], a) <= P["inv_radius"]:
                        q += 1
                cap = max(1.0, self.reach[a] / 10)
                inv_cost = P["inv_k"] * r["referenceFeeCents"] * q / cap
            stake = P["protect_k"] * self.trust_at_stake(r["dealerId"], r["arrivedAt"]) if P["protect"] else 0.0
            best, best_ev = None, P["min_ev"]
            for g in GRID:
                p = g * lst
                ev = self.pwin(r["dealerId"], o["kind"], math.log(g), ln) * (p * (1 - pl * late_cost) - fee_o - P["lam"] - pl * stake - relief * P["mu_eur"] * 100 * pl * (1 + 2 * self.mu) - peak_cost - inv_cost - adapt_cost)
                if ev > best_ev:
                    best, best_ev = g, ev
            if best is None:
                self.count(f"ev_decl_{o['kind']}")
                continue
            mult = 1.0
            if o["kind"] == "same_day":
                mult *= math.exp(P["sd_prem"] + (P["fri_sd"] if r["arrivedAt"] // DAY == 4 else 0.0))
            if snow_hit:
                mult *= math.exp(P["snow_quote"])
            prices[o["kind"]] = best * lst * mult
            quotes.append((o["kind"], math.log(best * mult)))
        if not prices:
            return self.decline(r)
        self.pending[r["id"]] = (r["dealerId"], quotes, (min(lanes_seen) if lanes_seen else 0.0) - self.theta_a[a], a)
        return prices
