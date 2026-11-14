# Research wave 4: implementations, forecasting and control, game theory, other industries

[mem] = unverified. Both agents' mappings onto Spread are derived, so verify them on the bench.

## A. Market making = Spread ("we are a market maker")

**Avellaneda–Stoikov**
- Fill intensity `λ(δ) = A·e^{−kδ}` (= our win curve).
- Reservation price `r = s − qγσ²(T−t)`.
- Spread `δa + δb = γσ²(T−t) + (2/γ)ln(1 + γ/k)`.
- As γ → 0, the markup → 1/k: the monopoly markup for an exponential curve.
- GLFT (arXiv 1105.3115) adds inventory caps.

**Mapping to Spread**

| Market making | Spread |
|---|---|
| s | expected staffing cost of a lane |
| **q** | **unstaffed committed backlog in the pickup town minus free drivers** (our "short position") |
| σ² | variance of the fill cost |
| τ | time to the order's pickup deadline |

→ **Quote = ĉ + q⁺·γσ²·τ + (1/γ)ln(1 + γ/k).** Each unstaffed order in a town raises every quote out of that town. Pricing brakes itself when staffing falls behind.

Refs:
- https://math.nyu.edu/%7Eavellane/HighFrequencyTrading.pdf
- https://arxiv.org/abs/1105.3115v5
- https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/

## B. Game theory against the adaptive competitor

- The competitor's price is a function of our win share per dealer, `p_c(s_d)`, with `p_c' < 0`.
- Optimal steady state: **a higher markup and a lower share than the myopic optimum.**
  - Hold a target share per dealer with a PI controller.
  - Probe `p_c'` with share experiments on a few dealers.
- **Commitment / Stackelberg vs learners:** Deng, Schneider & Sivan, NeurIPS 2019.
  https://papers.NeurIPS.cc/paper_files/paper/2019/file/f15eda31a2da646eea513b0f81a5414d-Paper.pdf
- **Pulse against the lag:** the competitor updates each morning. Win heavily while it is still expensive, then back off.
- **Shocks:**
  - outage: raise prices in the region by +20–25%;
  - price war: CUSUM detects it; **don't follow it down**; keep drivers for tomorrow.
- **Trust as an investment** (Kreps–Wilson [mem], CLV):
  - an on-time order is worth ≈ 0.01·p̄·N_remaining(d);
  - a late one costs ≈ T_d/2·p̄·N_remaining. **That loss grows with trust**, so strict on-time triage for high-trust dealers.

## C. Execution timing and optimal stopping (driver fees)

- **Almgren–Chriss:** `x(t) = X·sinh(κ(T−t))/sinh(κT)`. Driver learning acts as *permanent* market impact, i.e. Coase. Fix it with commitment.
- **Optimal stopping without recall (costs):** `c*₀ = penalty / backup`; `c*ₙ = E[min(C, c*ₙ₋₁)]`; accept a driver if `C ≤ c*ₙ`.
- → Staff most orders early at a fair flat fee. Make randomised-timing take-it-or-leave-it offers at threshold `c*ₙ` for the rest.

## D. Aviation, military, insurance, energy

- **Airline revenue management:**
  - EMSR-b: `P(D_high > y) = p_low/p_high`;
  - bid prices = LP duals over (town, day) driver capacity → quote floor = cost + π_origin;
  - "overbook" towns that have reliable inbound drivers.
- **Military airlift ADP (Powell):** a myopic assignment each step plus a learned value V̂(resource, location, time) updated from LP duals, `V̂ ← (1−α)V̂ + α·dual`.
  - Small slack buffers cut the cost of uncertainty.
  - Doctrine: triage priority classes; first feasible, then improve.
  - https://www.informs-sim.org/wsc05papers/011.pdf
- **Insurance price optimisation:**
  - conversion model `P(m) = 1/(1 + e^{a+bm})`;
  - `m* = 1/(b(1−P))`;
  - one Lagrange multiplier per portfolio constraint, `mᵢ* = λρᵢ + 1/(b(1−P))`;
  - **bisection on λ until projected on-time ≥ target**.
  - https://arxiv.org/pdf/1711.07753
- **Energy supply curves:** price the *marginal* driver, not the average. The quote rises steeply as a town reaches its last driver. Add small random noise so neither learner (competitor, drivers) can read our pattern.

## E. Implementations (GitHub etc.)

- **DiDi V1D3** (https://arxiv.org/abs/2105.08791): V(town, slot) by TD(0); match with `price − cost + γ^Δt·V(dest) − V(origin)` via `linear_sum_assignment`.
- **TAC SCM:** no public TacTex or DeepMaize source; reuse the papers.
- **Bid shading:**
  - AuctionGym (Amazon), https://github.com/amazon-science/auction-gym
  - BayesMAB, https://github.com/BayesMAB/BayesMAB
  - Verizon WR, https://arxiv.org/abs/2009.09259 (exactly our setting).
- **Uber Freight posted-price MDP** (https://www.uber.com/blog/freight-markov/):
  - state = load + lead time;
  - a *monotone* booking classifier (e.g. `HistGradientBoostingClassifier(monotonic_cst=...)`);
  - backward Bellman from a terminal cost;
  - UCB exploration;
  - a PID on booking speed.
- **Bandit libraries:** bayesianbandits, MABWiser, contextualbandits. A hand-written 30-line Thompson-sampling logistic is easier to control.
- **OR-tools PDPTW:** https://developers.google.com/optimization/routing/pickup_delivery. Only needed for multi-car chains.

## F. Hierarchical forecasting and reconciliation (town → region → total)

- **MinT:** `ỹ = S (SᵀW⁻¹S)⁻¹ SᵀW⁻¹ ŷ`, with W = I (OLS) or `diag(S·1)` (WLS-struct). About 3 lines of numpy. Library: Nixtla `hierarchicalforecast`.
- **Practical recipe:**
  - Gamma–Poisson shrinkage of town counts toward the region: `(won + α·prior·elapsed)/(elapsed·(1+α))`;
  - reconcile with WLS-struct;
  - clip at 0.
- **Verdict:** town-day counts are small (often <10), so **empirical-Bayes shrinkage does most of the work**. Reconciliation mainly buys coherence. It is worth it only when town-level and total-level plans must agree (e.g. a daily total capacity versus town budgets).

## G. Target tracking and control (adjusting as we go)

**Multiplicative stochastic-approximation tracker**
- On a win: `m ← m(1+a)`; on a loss: `m ← m(1−b)`. The win rate converges to `b/(a+b)`. For 30%: a = 0.035, b = 0.015.
- Steps of 1–4% move the price about ±20% within a day.
- Use one m per town cluster plus a global m, with shrinkage.

**Dual / PID pacing** (Balseiro, Lu, Mirrokni & Sivan, https://arxiv.org/abs/2202.06152)
- PID = mirror descent. Use `λ ← max(0, λ + η·(load − target))`.

**Two targets at once (win rate + ≥90% on time)**
- **Cascade, not competing loops.** The inner loop (drivers, fast) keeps on-time. The outer loop (quotes, 5–10× slower) adds λ_town.
- Deadband ±3 percentage points.
- Anti-windup clamp of ±20% on the integral.
- EMA of measured rates (half-life ~50 decisions).
- Halve the gains after two sign flips.
- **Asymmetric gain:** react 3× faster when projected on-time drops below 92%.

**Model vs tracker:** do both. The model chooses the *target* (argmax margin·P(win)); the tracker *holds* it as the competitor drifts.

## H. Industry practice

- **DoorDash switchbacks:** randomise by (region × time block). In our simulator: alternate seeds or day blocks. **Inject a known +5% effect to check that the bench detects it.**
- **Gig platforms:** drivers learn that low acceptance brings better offers. That's our mechanic. Randomise raises or post fair prices early.

## Jury "creative idea" candidates
1. **"Spread is a market maker":** Avellaneda–Stoikov backlog skew keeps the SLA through pricing.
2. **"We steer the competitor's learning":** a Stackelberg target share per dealer, pulsing against its lag, and refusing the price war.
3. **"Beating Coase with drivers":** committed flat fees plus optimal-stopping take-it-or-leave-it offers.
