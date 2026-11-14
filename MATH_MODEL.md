# Spread: a mathematical model of the problem

Goal: write the challenge as an optimisation problem, using **everything the docs reveal about the simulator's mechanics**, so we optimise the right thing with the right tools.
Notation: money in €, time in world minutes from Monday 00:00. "Docs" = RULES.md / HANDBOOK.md.

---

## 0. The target (leaderboard, level 8, fetched Sat ~11:00)

| | €/week | On-time (mean / worst week) | Orders won / week | € per order | Week-to-week sd |
|---|---|---|---|---|---|
| **#1 Juhus** | **16,006** | 97.5% / 95.1% | 373 | 42.9 | €819 |
| #2 Bob the builders | 14,678 | 98.0% / 97.4% | 301 | **48.8** | €1,232 |
| House best | 14,358 | 96.9% / 95.4% | 364 | 39.4 | €1,341 |
| #10 Cookiezi | 11,332 | 94.5% / 90.8% | 281 | 40.3 | €976 |
| Davincians (unranked!) | 12,495 | 93.4% / **89.9%** | 380 | 32.9 | — |
| House starter | −69,887 | 47.7% / 35.1% | 911 | −76.7 | €14,817 |

- Juhus beats House best on 4 of 5 weeks. The leaders improved by about €2k/week between two rounds, so **aim for ≥ €18k/week by Sunday**.
- **There are two winning shapes:**
  - volume: ~370 orders × €43 (Juhus, House best);
  - selectivity: ~300 orders × €49 (Bob).
- **One week under 90% means not ranked** (Davincians: 89.9% in one week). The leaders run at **95–98%**. That safety buffer is a deliberate choice.
- The top teams' sd is about €1k/week, so their systems are robust, not lucky.

Rough arithmetic for #1: ~370 orders × ~€45 margin. With median list ≈ €65 and typical fee ≈ €60, **you need quotes ≈ 1.3–1.45× list and fees ≈ 1.0–1.2× typical, on the right ~37% of requests**.

---

## 1. The full problem (one sentence)

> A finite-horizon, partially observed stochastic control problem: online pricing of arriving requests against an adaptive competitor (revenue), coupled to online procurement from strategic, learning sellers (cost), subject to a chance constraint on service (≥90% on time) and network effects (chaining, dealer trust).

This is a POMDP and intractable as a whole. We **decompose it** into sub-problems that are each simple (closed form or polynomial), linked by a few **dual prices**.

---

## 2. Objects and notation

| Symbol | Meaning | Known? |
|---|---|---|
| i ∈ R | price request: dealer d(i), legs ℓ (pickup a, delivery b), options o ∈ {SD, ND, W3}, deadline D_io, list price L_io, typical fee F_i, note | ✅ on arrival |
| p_io | our quote for option o | decision |
| q_io | competitor's price | ❌ hidden |
| W_i ∈ {0, 1} | we win | observed at respondBy |
| j ∈ J | driver: home h_j, rating, licence, completed gigs, drops | ✅ (`/drivers`) |
| A_t ⊆ J | drivers working on day t | ❌ (views partly reveal it) |
| g | gig: ordered stops, audience, fee schedule f_g(t) non-decreasing, ≤48 steps | decision |
| c_j(g) | driver j's cost of gig g | ❌ structure known |
| τ(a, b) | road minutes (map) | ✅ |
| T_d | trust count of dealer d (0..25) | ✅ (we can count it ourselves) |
| S_i | on time? (1/0) | outcome |

---

## 3. What the docs reveal about the simulator (our "model knowledge")

### 3.1 Competitor price (docs, "Dealers compare prices")
```
q_io = L̃_io · λ_ab · δ_day · ω · η_i · κ_d(t) · [1.3 if outage region-day] · [0.8 if price-war day]
```
- `L̃` = list price before rounding.
- `λ_ab` = lane factor: a **world-invariant** part (high where little work comes back and few drivers live near b) × a per-world part.
- `δ_day` = a fresh factor each day.
- `ω ∈ [1.26, 1.54]` at level 8.
- `η_i` = small noise per request.
- `κ_d(t)` = adapts per dealer each morning, a few steps: down if we win much at d, up if little.
- Plus morning step moves per place, and **one weekly reshape** where short and long lanes move in opposite directions.

→ **log q is additive:** `log q = log L + a_ab + b_day + w + k_d + ε`. That is exactly a linear model in log space, so we can learn it from binary outcomes with a probit or logit.

### 3.2 Dealer acceptance
- P(accept our option o) falls in `p_io / q_io`, **"quickly above the competitor's price"**.
- When several options are quoted, the dealer weighs `price − speed value_d(o)`. Dealers differ in price sensitivity and speed value.
- **Trust (level 8):** the price the dealer accepts is ×(1 + 0.01·T_d).
  - `T_d ← min(25, T_d + 1)` for each order delivered on time.
  - `T_d ← ⌊T_d / 2⌋` for a late one.
- **Satisfaction:** late or undelivered orders lower acceptance, an on-time order raises it a little, and an unquoted request lowers it slightly.

Model:
```
P_io(p) = σ( β · (log q̂_io + log(1 + 0.01·T_d) + s_d − log p) )
```
- σ = logistic or probit.
- β = steepness, to estimate. It is large: "falls quickly".

### 3.3 Driver cost and booking rule (docs, "How the world works")
```
c_j(g) = α·drive(g)                               (time at the wheel)
       + π_ahead(loc_j → a) + α_pt·pt_time(loc_j → a)   (cheap ticket bought ahead, cheap time)
       + π_day(b → h_j)     + α_pt·pt_time(b → h_j)     (expensive day ticket home)
       + extras(evening, weekend, private, trade-in, charging, plates, dislike)
       + [night away, if a far morning pickup]
```
- `α_pt ≪ α`: transit time is cheap compared with time at the wheel.
- Small towns have a last connection in the evening; after it, the trip home is expensive.
- For a driver already on our gig, a second gig costs only the **marginal** time and tickets.

**Driver j books gig g at displayed fee f iff:**
```
f − c_j(g) > u_j(t)          (outside option that day)
f − c_j(g) ≥ V_wait_j        (value of waiting for a raise)
```
- `V_wait_j ≈ (r̄_j − 1)·f·P(still open | j's belief)`.
- `r̄_j` = j's running mean of (booked fee ÷ first-viewed fee) over our orders j viewed and could do. Old orders fade.
- Drivers wait **less** close to the pickup and **more** the longer the gig has stayed on the board (the gig's age survives a repost).

**The typical fee reveals the cost scale:**
```
F_i = θ · c_typical-resident-of-a(drive + trip to pickup + trip home) · ν_i      (θ is one factor for every lane)
```
- So `F_i / θ` is a noisy estimate of the cost for a driver who lives in the pickup town.
- For any other driver j: `c_j(g) ≈ F_i/θ · ratio(j)`, with ratio(j) built from map minutes: a driver living near b has no expensive trip home.
- **This is the key lever.** The cheapest driver for a car is the one whose home is near the delivery (or whose next pickup is near it), not the one in the pickup town.

**Visibility**
- Notifications go to drivers whose **home is within 30 km of the pickup** (straight line), once per order. A raise sends no notification.
- No notifications are read from 23:00 to 07:00.
- Drivers far away browse but rarely book.
- **Bookings need feasibility:** the driver must reach every stop inside its window. A 7 h drive due at 20:00 gets no driver after 13:00.

**Drops**
- The hazard of a drop rises with holding time and is higher when `f − c_j` is small. It is low at night.
- A driver who dropped a gig rebooks it only at a higher fee.

**Direct offer:** one driver, 10 minutes, accepted iff `f − c_j > u_j`, with **no waiting term**. Limits: ≤3 per driver per day, ≤3 open per gig.

### 3.4 Payoff
```
Π = Σ_{i won} [ p_i·(1 − ρ(lateness_i)) − 2·p_i·1{undelivered} ] − Σ_g fee_g − Σ (failed visit, release, fines, waiting)
ρ = 0 if on time; 0.10 if ≤ 2 h late; 0.25 if 2–24 h; 0.50 if ≤ 2 business days; 1.00 if later.
Undelivered at the end: revenue 0 and a penalty of 2·p (a swing of 3·p vs delivered).
Constraint:  Σ S_i ≥ 0.9 · Σ W_i   (per week; the final is one week)
```

---

## 4. The decomposition (each piece is simple)

### 4.1 Lagrangian: one dual price μ makes the 90% constraint local
Relax the constraint with a multiplier μ ≥ 0 (€ per on-time order):
```
L = Σ_i W_i · [ p_i − E[fee_i] − E[refund_i] + μ·(π_i − 0.9) ]
```
where `π_i = P(on time | won)`.

**Every order then gets an effective cost:**
```
c_i^eff = E[fee_i] + E[refund_i] − μ·(π_i − 0.9) + λ_{a,t} − V_trust,d
```
- `λ_{a,t}` = shadow price of driver capacity at pickup town a on day t (bid-price control, revenue management).
- `V_trust,d ≈ 0.01 · (expected remaining revenue from d) · π_i` when T_d < 25.
- Orders with `π_i < 0.9` cost extra, and orders with `π_i > 0.9` get a subsidy. **One number, μ, trades margin against safety.**
- Online update (dual / primal-dual): `μ ← max(0, μ + η·(0.9 + buffer − running on-time estimate))`, with buffer ≈ 0.05.

### 4.2 Quoting: closed form given the curve
For each option:
```
p* = argmax_p (p − c^eff) · P(p)
```
- With a logistic curve, the first-order condition is **`p* − c^eff = 1 / (β·(1 − P(p*)))`**, solved by the Lambert W function or 10 Newton steps. Microseconds.
- **Decline** if `max_p (p − c^eff)·P(p) ≤ 0`: quote 10× list, which costs nothing.
- **Option choice:** quote every option whose expected value is positive. For options we don't want, quote high so the dealer ignores them.
- The dealer then picks by `price − speed value`. We can make the slow option attractive when batching makes it cheap.

### 4.3 Learning q (the competitor): a probit with model structure, O(n·k) per update
- **Model:** `y_i = 1{log p_i < log q_i}`, with `log q_i = xᵢᵀθ + ε` and `x` = [lane (pickup, delivery), day, world, dealer, option].
- **Offline (practice worlds):** fit the world-invariant lane part `ā_ab`. It becomes the **prior**.
- **Online (the final):** estimate `w` (world level) from Monday's first hours. ~100 quotes pin it to about ±0.6%. Then daily `b_day` and dealer offsets with forgetting.
- **Detectors:**
  - CUSUM on wins: a sudden all-region surge in losses means **price war** (shift −0.22 that day);
  - a regional surge in wins means **outage** (+0.26 there).
- **Exploration for free:** about ±3% jitter on p.

### 4.4 Fee setting: committed posted price plus direct offers (optimal-stopping view)
For a gig g with deadline-driven critical time `t_c` (= last minute a driver can book and still be on time):

**Booking-rate model**
```
h(t; f) = Σ_{j ∈ A_t ∩ Vis(g)} ν_j · 1{f − c_j(g) > max(u_j, V_wait_j)}
P(booked by t_c | f) = 1 − exp(−∫ h dt)
```

**Policy**
1. **Open at a committed fee `f₀ = min f s.t. P(booked by t_c − buffer) ≥ 1 − ε`**, using the cost model (§3.3) over the drivers who can see the gig.
2. **Don't ramp** (Coase): each visible raise increases r̄_j for every viewer and makes future gigs more expensive.
3. If there is still no booking at t_c − buffer: **direct offers** in Pandora's-box order of index `z_j = max_f [V − f − k / P_j(accept | f)]` (no waiting term, so no learning of raises). Then one steep public step as a last resort.
4. Expected cost = `E[fee] + E[late penalty]·P(not booked in time)`, so deadline-critical gigs justify a higher f₀.

### 4.5 Dispatch / batching: polynomial via path cover
- Legs are nodes. Edge `i → j` if a driver can deliver i and then pick up j in time, the combined plan is ≤ 12 h, and the windows are feasible.
- **Edge weight** = cost saved = `c(i) + c(j) − c(i ⊕ j)`. Mainly it saves the trip home after i and the trip to j's pickup.
- **Chains = paths in a DAG.** A minimum-cost path cover = **maximum-weight bipartite matching** between out-copies and in-copies of the legs. Hungarian algorithm: O(n³); with n ≈ 50 open legs that takes milliseconds.
- Special cases:
  - trade-ins (old car's pickup right after the new car's delivery: the docs say do it);
  - same-yard bulk orders (30–40 cars from one place: chains are impossible, so you need many drivers; price high);
  - backhauls into our own drivers' end points.

### 4.6 Capacity / admission: newsvendor per town-day
- Expected staffable orders from pickup town a on day t is roughly `N_a,t ≈ (drivers within reach of a) × P(working) × gigs per driver`, learned from practice.
- The expected marginal cost of the n-th order at a rises steeply as n approaches N, so `λ_{a,t}` rises with committed load. In practice: a piecewise-linear λ by load ratio.
- **Critical-fractile view:** accept orders up to the quantile `(margin) / (margin + expected lateness cost)` of the random supply.

---

## 5. Which parts are hard, and which are easy

| Sub-problem | Exact form | Complexity | What we do |
|---|---|---|---|
| Joint control | POMDP | intractable | Decompose (§4) |
| Quote price | 1-D concave maximisation | O(1) | Closed form + learned curve |
| Competitor learning | GLM with binary outcome | O(n·k) | Probit / logit with priors |
| μ, λ duals | online convex optimisation | O(1) per step | Subgradient updates |
| Chaining | min-cost path cover | O(n³) polynomial | Hungarian / greedy |
| Fee for one gig | optimal stopping with strategic agents | small DP | Committed f₀ + offers |
| Offer ordering | Pandora's box | O(m log m) | Sort by index |
| Parameter tuning | noisy black-box | sim budget | CMA-ES / racing on paired seeds |

---

## 6. What we must estimate (and from what)

| Parameter | Source | When |
|---|---|---|
| Lane prior `ā_ab`, steepness β, option offsets | Our quotes in many practice worlds (win/loss) | Offline |
| World level w, day effects, dealer offsets | Live win/loss | Online, first hours |
| Cost-scale θ and relative cost ratio(j) | Booked fees vs typical fees vs driver home/delivery geometry (reveal: views with fee seen, bookings) | Offline, then refine online |
| Who works today (A_t) | `gig_viewed` events (driver ids), bookings | Online |
| Booking hazard vs (f/F, time to t_c, drivers near) | Practice gigs: survival model | Offline |
| Drop hazard vs margin | Practice drops | Offline |
| Capacity N_a,t by town | Practice + driver list | Offline + online |
| On-time probability π_i | Practice outcomes vs features (slack, drive time, supply, notes) | Offline |

---

## 7. Different lenses on the same problem (useful for the jury's "creative" criterion)
1. **Two-sided marketplace:** we are a broker setting a bid on one side (dealers) and an ask on the other (drivers). Margin = spread. **The name of the challenge is "Spread".**
2. **First-price procurement auction** against one adaptive bidder (= bid shading in ad tech).
3. **Revenue management:** perishable driver capacity per town-day, with bid prices.
4. **Strategic durable-goods (Coase) problem, reversed:** drivers are patient sellers who learn our raises.
5. **Network flow:** cars as commodities, drivers as reusable resources whose end points become free supply.
6. **Reputation dynamics:** trust T_d is a state that compounds, so being on time is an investment with returns.
