# Algorithm toolkit: fast heuristics, all under 50 ms per decision (research wave 3A)

[mem] = from memory, not checked against the paper. Links to the full math: `MATH_MODEL.md`.

## Ranked shortlist (value ÷ effort, 24 h)

| # | Technique | What it fixes | Effort | Complexity |
|---|---|---|---|---|
| 1 | **Weighted min-path-cover chaining** (Hungarian) | Driver fees, our biggest cost; makes lanes that chain cheaper to quote | ~3 h | O(n³), 5–30 ms for n ≤ 300 |
| 2 | **Dual price λ on late risk** (dual mirror descent) | The 90% SLA as a smooth term in the price | ~20 lines | O(1) |
| 3 | **Newsvendor cap per town-day and option** | The catastrophic penalties in towns with few drivers | ~1 h | O(1) |
| 4 | **Logistic hazard for time-to-book + EB town shrinkage + isotonic** | When and how much to raise fees; supplies P(late) to #2 and #3 | ~3 h | fits in seconds |
| 5 | **Morning LP: shadow value φ(town, day) of drivers** (Ma–Fang–Parkes style) | Opportunity cost in quotes; bonus for gigs ending where drivers are scarce | ~2 h | under 100 ms with HiGHS |
| 6 | **CUSUM on win rate and booking rate** | Detecting the price-war and outage days | ~30 min | O(1) |
| + | Stochastic-BALANCE scoring of direct offers | Spreads the 3-offers-per-driver-per-day budget | small | O(deg) |
| + | Zhou–Chakrabarty–Lukose exponential threshold | A forecast-free fallback before estimates warm up | small | O(1) |

---

## 1. Chaining = minimum path cover in a DAG (polynomial)

**Graph**
- Node = leg i, with origin o_i, destination d_i, drive time τ_i, earliest pickup a_i, deadline D_i, provisional start s_i.
- Edge i→j iff all of these hold:
  - `s_i + τ_i + T(d_i, o_j) ≤ D_j − τ_j` (the driver reaches and delivers j in time);
  - `τ_i + T(d_i, o_j) + τ_j ≤ 12 h`;
  - the deadhead `T(d_i, o_j)` is short (< 90 min).
- Edges follow time order, so the graph is a DAG.

**Reduction:** split each leg into i⁺ (has a successor) and j⁻ (has a predecessor). **Min path cover = n − |max matching|.**

**Weighted version:**
- Edge weight `w_ij = fee(i) + fee(j) − fee(i→j)`: the saved ticket home plus the saved trip to the pickup, minus the cost of the deadhead.
- Solve with `scipy.optimize.linear_sum_assignment(−W)`, with a dummy "no successor" column so a leg can stay unmatched.

**Repair:** pairwise feasible does not mean the whole path is feasible (the 12 h limit is cumulative and start times shift). Walk each chain and split it at the first violation.

**Use**
- Re-solve every 5–15 world minutes over unbooked legs.
- Feed "chainability" (the best w_ij for a new request) into the quote as a cost discount.

Refs: Fulkerson/Dilworth (standard); online taxi dispatch backbone: https://dspace.mit.edu/handle/1721.1/135142

## 2. Dual price for the 90% constraint (Balseiro–Lu–Mirrokni dual mirror descent)

```
decision:  p_t = argmax_p  P(win|p) · (p − cost − λ_t · p_late_t)
update:    λ_{t+1} = max(0, λ_t − η·(ρ − b_t))        b_t = p_late if won else 0
           ρ = (0.10 − δ)·P(win) for a typical order;  η ≈ 1/√T;  λ_0 ≈ late refund cost
variant:   multiplicative  λ_{t+1} = λ_t · exp(−η(ρ − b_t));  PID if it oscillates
```
- Run separate λ's for "late risk" and for "driver-hours per region" to get knapsack behaviour too.
- Refs:
  - https://proceedings.mlr.press/v119/balseiro20a.html
  - https://arxiv.org/abs/2011.10124
  - PID variant: https://arxiv.org/abs/2202.06152
  - Agrawal–Devanur: https://arxiv.org/abs/1410.7596

## 3. Newsvendor / overbooking cap per town-day

- S = random driver supply for a town-day (Poisson or negative binomial; mean = home-town drivers × supply rate + drivers chained in).
- Accept the j-th order iff `F_S(j−1) ≤ m / (m + c)`, where:
  - m = expected margin;
  - c = expected loss if not staffable in time (refund, ×2 if undelivered) + λ.
- **Note:** the agent's example used c = 2 × price (undelivered). In reality most unstaffed cars still arrive late with a 10–50% refund, so c is usually 0.25–1 × price. Calibrate c from practice data.
- **Nested options** (Littlewood-style [mem]): same_day uses today's supply S₀; within_3_days can use S₀ + S₁ + S₂.
- **Use:** once a town-day reaches Q*, quote high, so we only win at a premium.

## 4. Statistics for fees and safety

**4a. Discrete-time logistic hazard of booking**
- Rows: one per open gig per 10-minute period.
- `h_k = σ(α_k + β·log(fee/ĉ) + γ_town + δ·hours_to_deadline + ζ·#raises)`.
- `P(booked by t) = 1 − ∏(1 − h_k)`. Plain `LogisticRegression`; censoring is handled automatically.
- **Fee rule:** pick the lowest fee (bisection) such that P(booked before deadline − slack) ≥ target.

**4b. Empirical-Bayes shrinkage across towns**
- `p̂ = (k + α)/(n + α + β)`.
- Method of moments: `α + β = m(1−m)/v − 1`.
- For the hazard model, use ridge-penalised town effects.

**4c. Isotonic regression (PAVA, O(n))**
- Enforce that P(book) is monotone in the fee and P(win) monotone in price.
- `sklearn.isotonic.IsotonicRegression`.

**4d. Conformal / quantile safety margin**
- Split-conformal or CQR (quantile LightGBM plus a conformal correction).
- **Latest safe posting time** = deadline − drive time − q₀.₉(time-to-book).
- Ref: https://arxiv.org/abs/1905.03222

**4e. Change points**
- BOCPD (Adams & MacKay, https://arxiv.org/abs/0710.3742) with a Beta-Bernoulli likelihood on win/lose.
- Or a Bernoulli **CUSUM**: `S ← max(0, S + x_t − k)`, alarm at `S > h`.
- **Price war:** a loss streak everywhere. **Outage:** a win spike in one region.

## 5. Threshold acceptance (no forecast needed)

**Zhou, Chakrabarty & Lukose 2008 (online knapsack)**
- Accept iff `r ≥ Ψ(z)`:
  - `Ψ(z) = L` for `z ≤ 1/(1 + ln(U/L))`;
  - `Ψ(z) = (U·e/L)^z · (L/e)` otherwise.
- z = share of the town-day's capacity used; r = margin per driver-hour.
- Ref: https://link.springer.com/chapter/10.1007/978-3-540-92185-1_63

**Prophet rules**
- A single threshold τ (E[max]/2) gets at least half of the optimum.
- k slots: choose τ such that `N·P(v > τ) = k` [mem].
- Ref: https://arxiv.org/pdf/1507.01155

## 6. Direct offers: Stochastic BALANCE [mem]

- `score(d, g) = p_accept(d, g) · (value − fee) · (1 − e^{f_d − 1})`.
- `f_d` = share of driver d's offer budget used (3/day), or the summed acceptance probability of their failed offers.
- Refs:
  - https://arxiv.org/abs/1905.12778
  - fully online matching: https://arxiv.org/abs/1802.03905

## 7. Pricing and dispatch jointly

**Banerjee–Johari–Riquelme:** the optimal *static* price matches dynamic policies on throughput and revenue. Dynamic pricing's value is **robustness**.
→ A well-tuned static base price by lane × option plus a small state-dependent correction (λ, cap). No big dynamic model.
https://sigecom.hosting.acm.org/exchanges/volume_15/1/BANERJEE.pdf

**Ma–Fang–Parkes spatio-temporal pricing:** solve a flow LP; the duals give the driver value at each node.
→ Each morning: an LP over 30 towns × 3 days; dual φ(town, day).
- Quote ≥ cost + φ_origin − φ_destination.
- Give a bonus to gigs that end where drivers are scarce.
https://arxiv.org/abs/1801.04015

**Feng–Niazadeh–Saberi:** batch, then match. Waiting and re-optimising every ~10 min beats instant greedy dispatch.
https://arxiv.org/abs/2210.11648
