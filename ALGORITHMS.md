# Spread: which algorithms we need

Sources: `docs/RULES.md`, `docs/HANDBOOK.md`, `docs/API.md` (official, downloaded 2026-11-14), plus the research in `RESEARCH.md`.
Where the docs disagree, RULES.md is correct.

---

## 0. Reality check: timeline (Helsinki time)

| When | What | Why it matters |
|---|---|---|
| Sat 14:00 and 20:00 | **Test finals** (live clock, about 19 min, level 8 from Thursday) | The only rehearsal of real-time mode, stream handling and restarts |
| Sat/Sun every 3 h | Ranking rounds (5 secret level-8 weeks) | Leaderboard vs **House best** (Bahn's own system) |
| **Sun 07:30** | Final set, **registration closes** | The team must exist before this |
| **Sun 08:00** | **Final**, about 34 min, autonomous, rate limit 20 actions/s | Must stay up, survive restarts, and rebuild state from snapshot + events |
| Sun 10:00 | Submission closes (code link, hash, 5–10 slides) | The jury wants *ideas + measured effect of each idea* |

The final only has to get us into the **top 10 ranked**. After that, the jury judges elegance, clarity, creativity and robustness.
So the design goal is a **robust, explainable system that clears 90% on time with positive margin**, not a fragile max-margin monster.

---

## 1. Where the money is (what the mechanics say)

Score = Σ prices of delivered orders − driver fees − refunds − penalties − fines.

| Lever | Mechanic | Implication |
|---|---|---|
| **Quote price** | P(win) falls steeply once our price exceeds the competitor's price. At level 8 the competitor's price ≈ list × 1.26–1.54 × lane × day × noise | **The list price is way too cheap at level 8.** The starter quotes list and loses money because it wins everything it can't deliver |
| **Which requests to win** | Driver shortage (26–40% of drivers, uneven by town) | **Selection beats volume.** Refuse what we can't staff (quote very high = free decline; *not* quoting costs goodwill) |
| **Driver fee** | Driver books if fee − own cost > outside option *and* > expected value of waiting | The typical fee often finds no one at level 8. Cost depends hugely on **where the driver is** |
| **Strategic waiting** | Drivers learn our raise ratio (booked fee ÷ first viewed fee) and our time-to-book | **Don't always ramp.** Open near the clearing price, then raise rarely and steeply. Use direct offers |
| **Lateness** | Refund of 10/25/50/100%; undelivered = −2× price; late = halves dealer trust | A late car destroys several cars' worth of margin. Protect the 90% SLA |
| **Dealer trust (level 8)** | +1% accepted price per on-time order to that dealer, cap +25%; late halves it | Concentrate on dealers we deliver to well. Trust compounds |
| **Competitor adapts** | Cuts prices for dealers where we win most; raises where we win few | Don't take ~everything from one dealer. Keep learning online |
| **Price war** (1 day, −20%) | Unannounced, 08–18 | Detect it from a sudden loss streak and don't chase it down. Sit out or win only cheap lanes |
| **Outage** (1 region-day, backup +30%) | Unannounced | Detect it from a sudden win streak in a region and **raise prices there** |
| **Notes** (FI/SV/EN) | The world obeys the note even if we don't | Parse ready time, pickup/delivery hours, tighter deadline, manual, plates, summer tyres |
| **Hard rules** | Premium → experienced audience (−€150); EV <30% and >200 km → charging stop (−€100); multi-car gig ≤12 h driving | Pure bookkeeping. Get it right once |

---

## 2. Components we need

### A. Note parser (deterministic, FI/SV/EN)
- Extract: ready/release time, pickup hours, delivery hours, tighter deadline, `manual`, `no plates`, `summer tyres`, plus corrections ("not 3pm") and relative days (tänään/idag/today, huomenna/i morgon/tmrw, weekdays = 2–6 days ahead, word-hours 9–17, "half three" = 14:30).
- Approach: regex + keyword tables first. **Measure accuracy with `reveal`** (it gives the true meaning of every won order's note). Optionally use an LLM offline to generate and check patterns. Don't use an LLM in the live loop (4.5 s per request in real time, plus the rate limits).
- Payoff: avoids failed visits (≥€25 each plus a lost day) and late cars.

### B. Cost / feasibility model per request ("can we staff this, and for how much?")
Estimate the **expected driver fee F̂** and **P(on time)** for each request *before* quoting:
- Inputs: the typical fee, road minutes (map), pickup town driver density (`/drivers` gives homes; level 8 is uneven by town), hour/day, slack until deadline, return-trip attractiveness (drivers living near the delivery place make it cheap), where *our* drivers will finish (chaining), notes.
- Start simple: `F̂ = typicalFee × m(town supply, slack, hour)`, with `m` learned from our own booked fees ÷ typical fee across practice weeks (from the reveal: views with seen fee, plus events: booked fee).
- Upgrade: a regression (GBM) on practice data: booked-fee ratio and time-to-book as functions of the features above.

### C. Quoting = price × win-probability optimisation, with an opportunity cost
For each option `o` of a request:

```
maximize over p:   P_win(p | lane, dealer, day) · ( p · P_ontime − F̂ − E[refund] − λ · capacity_used )
```

- **P_win model:** logistic in `log(p / list)` with features (lane/pickup-delivery towns, dealer, day, hour, option). Prior from practice weeks (the lane part "holds in every world"). **Online update** from each win/loss (Bayesian logistic, or a per-dealer/per-region offset updated like an Elo rating). Censored binary feedback: we only learn "accepted at p" or "rejected at p".
- **Price level of the world:** estimate on Monday morning from the first win/loss outcomes (level 8 competitor = list × 1.26–1.54). This is the single biggest number to get right.
- **λ (shadow price of capacity):** a simple rule is to raise λ when the projected on-time rate approaches 90% or the pickup town is short of drivers. That gives revenue-management style order acceptance.
- **Trust bonus:** add `trust_count(dealer)%` to the price we can charge that dealer.
- **Regime detectors:** loss streak across all dealers → price-war day (don't undercut, accept fewer). Win streak in one region → outage (raise toward +30%).
- **Option choice:** quote `within_3_days` attractively when we can batch it into multi-car gigs. Quote `same_day` only when staffing is clearly feasible.
- **Decline:** quote 10× list (free). Never leave a request unquoted (costs goodwill).

### D. Gig fee schedule = posted-price mechanism against strategic, learning drivers
- **Open near the estimated clearing fee**, not at a lowball. Drivers learn raise *ratios* and *time to book*, so constant ramps teach them to wait.
- Schedule shape: a flat opening fee, then **few, large, late steps** timed against the deadline (`lastPickupAt` minus travel and notice time). Use the 48-step schedule to pre-commit, so no reprice calls are needed (fewer tokens in the final).
- **Direct offers** (10 min, ≤3/driver/day, ≤3 open/gig): target drivers who **just finished our gig near the pickup** (we see their position), or who live near pickup/delivery (from the roster). An offer avoids the "wait for raise" premium.
- **Drop risk:** a fee that barely covers cost gets dropped. Keep a margin above the estimated cost, and prefer drivers with a low drop history (the roster shows past drops).
- **Escalation policy:** after `deadline_close`, escalate fast (the starter goes 1.5× → 2.5×). Do it earlier for high-value orders because a late order also costs trust.

### E. Batching / chaining (network effects)
- **Trade-ins:** one gig with the old car's pickup right after the new car's delivery (the docs recommend it).
- **Multi-car gigs ≤12 h:** same-yard cars (the bulk order of 30–40 cars), or A→B plus B→C chains. Greedy insertion is enough: pair legs where `delivery_i` is near `pickup_j` and the time windows fit.
- **Back-haul pricing:** a request whose pickup is where our drivers end up is cheap for us, so we can quote lower and win it.

### F. Robust runtime (judged on robustness)
- Event-driven loop on `world.stream()`. On start or restart: rebuild state from `snapshot()` + `events()` (the starter shows how).
- Respect rate limits (20 actions/s in the final). Batch actions (≤50 per batch).
- Idempotent actions. Every request gets a quote within 15 world-minutes (4.5 real seconds in daytime).
- Run on a cloud VM near Stockholm (their server is there).

### G. Evaluation harness (the jury wants the "effect of each idea")
- Deterministic seeds: run N≥20 seeds × variants in parallel (8 practice slots, rate limits).
- Log margin, on-time share, wins, fee ratio, late count per variant. That gives an **ablation table** for the slides.
- `fork` lets us compare two decisions on the same future (e.g. quote-price policy A vs B from Monday 12:00).
- `reveal` after each week gives a training set (quotes → outcomes, views → fees, note truths).

---

## 3. Suggested build order (MVP first, then upgrades)

1. **Run the starter** at levels 1 → 8. Set up the seed-sweep harness plus a CSV logger (reveal-csv).
2. **Stop the bleeding:** quote ≈ list × 1.3 at level 8. Refuse requests whose estimated fee or feasibility is bad. Enforce the hard rules (premium, EV, plates, manual) and the note parser v1.
   → Goal: **ranked (≥90% on time) with positive margin.**
3. **Fee policy v2:** opening fee from the learned clearing ratio by town/hour. Few steep steps. Direct offers to nearby finishing drivers.
4. **Quote optimiser:** logistic P_win with an online world-level estimate. Expected-margin maximisation. Capacity shadow price.
5. **Batching:** trade-ins in one gig, same-yard multi-car, chaining.
6. **Regime detectors** (price war / outage), trust-aware pricing, per-dealer win-share cap.
7. **Robustness:** restart test, test finals, VM near Stockholm.
8. **Slides:** one idea per slide, with an ablation on the same 20 seeds.

---

## 4. Open questions (ask at the Bahn booth / measure)
- How steep is P_win above the competitor's price (the slope of the logistic)? Measure it with price sweeps on practice seeds (`fork`!).
- How much faster do direct offers book than app posts at the same fee?
- How strongly does the drivers' learned "raise belief" change booking delays? Test fixed-fee vs ramp on the same seed.
- How accurate is the regex note parser on the reveal? Is an LLM-assisted pattern generator worth it?
