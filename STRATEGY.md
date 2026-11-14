# Strategy for 1st place (synthesis of all research, for discussion)

Inputs: `MATH_MODEL.md` (formulation), `ALGO_TOOLKIT.md` (fast algorithms), `INDUSTRY.md` (what to steal), `TUNING.md` (how to optimise), `FINDINGS.md` (our data), leaderboard.

## Where we are vs where #1 is

| | €/week | On-time | Won/week | €/order |
|---|---|---|---|---|
| **Target: #1 Juhus** | 16.0k (aim **≥18k** by Sunday) | 97.5%, worst week 95.1% | 373 | 42.9 |
| Us: best `markup` variant so far | ~0k | 82–88%, worst week 64–75% | 280–365 | ~0 |

**The gap is on-time and fees, not quoting volume.** We already win about the right number of orders. We just can't staff them cheaply and on time.

## The core idea (one sentence, for the jury)
> **We run Spread as a broker that prices both sides of the spread with the same currency: the expected cost of staffing an order on time, including the shadow value of scarce drivers, set by two dual prices.**

## Architecture: 4 modules + 2 dual prices

```
             ┌────────────── shared cost model ĉ(order) & π(order on time) ──────────────┐
request ──▶  [1 QUOTE]  p* = argmax (p − ĉ − λ_town + μ·(π−0.9)·… ) · P_win(p)             │
             (censored win model + TacTex calibration + regime detector)                   │
won     ──▶  [2 HIRE]   committed opening fee f₀ from cost model; few late steps;            │
             direct offers ranked by index; backward induction from deadline              │
open legs ─▶ [3 CHAIN]  weighted min path cover (Hungarian) every ~15 min                   │
events  ──▶  [4 LEARN]  P_win params, booking hazard, who works today, dealer trust         │
duals:       μ (on-time buffer, dual mirror descent)   λ_town,day (driver capacity)       ┘
```

1. **QUOTE.** Bid shading:
   - censored logistic/probit win model on log(p/list) with lane/day/dealer/option features;
   - a world-level estimate in the first hours;
   - TacTex calibration (wins ÷ predicted);
   - CUSUM for the price-war and outage days;
   - closed-form optimal markup over the effective cost.
2. **HIRE.** Committed posted price (Coase) plus direct offers:
   - opening fee = lowest fee with P(booked before the critical time) ≥ target, from the cost model (the typical fee reveals the cost scale; drivers living near the **delivery** are cheap);
   - **no steady ramp**;
   - late: direct offers (Pandora/BALANCE order), then one steep step.
3. **CHAIN.** Legs → DAG → max-weight bipartite matching gives chains (trade-ins, backhauls, same-yard). Chainability lowers the quote cost.
4. **LEARN.** Online estimates feeding 1–3:
   - competitor offsets;
   - the booking hazard by (fee/typical, hours left, town supply);
   - active drivers from `gig_viewed`;
   - dealer trust count.

**Duals**
- **μ:** € per point of on-time buffer, updated `μ ← max(0, μ + η·(0.95 − running on-time))`. **One knob trades margin against safety.**
- **λ(town, day):** a capacity bid price rising with the load ÷ expected driver supply (newsvendor / knapsack threshold).

## Build order (each step is benchmarked on the bench vs the previous one)

| Step | What | Why first | Expected effect |
|---|---|---|---|
| **S1** | **Staffability model:** per-order π (P on time) and ĉ (expected fee) from simple features: drive minutes vs slack to the deadline, drivers within reach of the pickup *and* the delivery, hour/day, notes. Fit on practice reveals | Everything else uses it; it fixes the on-time gap | On-time 85% → 93%+ |
| **S2** | **Hiring v2:** committed opening fee from ĉ; late steps only; direct offers to nearby/finishing drivers | Fees are the biggest cost; the starter's ramp teaches waiting | €/order +€10–20 |
| **S3** | **Quote v2:** censored win model + optimal markup + calibration; decline when the expected value ≤ 0 | Price = the biggest lever (t = 5.3 in sweep1) | +€3–6k/week |
| **S4** | **Duals μ, λ(town, day)** | Safety and selectivity with one knob | Worst week ≥ 93% |
| **S5** | **Chaining** (path cover) + trade-ins in one gig | Cost reduction, plus a creative point | +€1–3k/week |
| **S6** | **Notes parser v2** (weekdays, tomorrow, words, manual, plates, tyres) | Failed visits and silent lateness | small but cheap |
| **S7** | **Regime detectors + dealer trust in the price** | Level 8 specials | +€0.5–2k/week |
| **S8** | **Tuning** (Optuna TPE → CMA-ES, objective J, paired racing) + **final runtime** (stream, restart, rate limits) | Squeeze and survive | +10–20% |

The final-runtime work (live stream, restart, 20 actions/s) must happen before **Sun 07:30**. Rehearse it in the **20:00 test final**.

## Metrics we optimise (TUNING.md)
```
J = mean margin − €3,000 · mean(max(0, 0.95 − OT_w)·100);   J = −∞ if any week < 90%
```
- Report the 5th-percentile on-time, the worst week, € per order, quote ÷ list, fee ÷ typical, drops, expiries.
- Seeds: 3 pools (train, selection, held-out).
- The jury wants an **ablation table**: one idea per row, on the same held-out weeks.

## Open questions to discuss
1. **Scope vs time:** S1–S4 are must-haves for the top 10. S5–S7 are for #1. Do we have the people and hours?
2. **Team split:** A = quote + learning (S3, S7); B = staffability + hiring (S1, S2, S4); C = bench, tuning, runtime, notes (S6, S8)?
3. **The test final at 20:00:** rehearse with whatever we have by then?
4. **Do we ask the Bahn booth for a hint** on the hiring side (opening fee and direct offers)?
5. **Ranking runs:** they're free information (a public comparison), but our team page shows them. Start once we beat `markup`?
