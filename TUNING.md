# How to tune and evaluate (research wave 3C)

[mem] = cited from memory, not checked online.

## Budget reality
- A candidate needs many seeds. 600–900 weeks/hour ÷ 16 seeds ≈ **40–60 candidates per hour**, so about 300–600 over 12 h.
- With that budget, **smart seed allocation and paired comparisons matter more than a fancy optimiser**.

## Tool
- **Optuna** (Python; parallel via SQLite or journal storage):
  - first a TPE broad search: `TPESampler(multivariate=True, n_startup_trials=30, constant_liar=True)`;
  - then CMA-ES refinement: `CmaEsSampler(restart_strategy="ipop", popsize 8–16)`.
- Add **our own paired racing**: start each candidate on 4 seeds and extend it to 12 only if it is within 1 standard error of the best.
- Alternatives:
  - irace (R): the best fit in theory, but it means a shell bridge from R.
  - SMAC3: heavier, and not reproducible when run in parallel.
  - NSGA-II (margin vs on-time) as a two-objective study: useful for a **trade-off chart for the jury**.

## Objective (what we tune)
```
J = mean_w(M_w)
  − κ · mean_w( max(0, τ − OT_w) · 100 )        κ ≈ €3,000 per percentage point below τ
  − ρ · (mean_w(M_w) − CVaR20(M))               ρ ≈ 0.2  (optional downside term)
J = −∞ if any week has OT_w < 0.90               (the final = one week: 90% is a cliff)
τ ≈ 0.90 + 2.5 · sd(OT_w)                        → typically 0.93–0.95
```
- Track the **5th percentile** of on-time share, not just the minimum, which is too noisy.
- **Rule of three:** 0 failures in n weeks gives a 95% upper bound on the failure rate ≈ 3/n. 60 clean weeks → ≤5%; 300 → ≤1%.

## Seeds
- Three pools:
  - **train ~200** (rotated each generation);
  - **selection ~60**;
  - **final held-out ~200** (used once).
- Paired test sample size: `n ≈ 6.2 · (s_d / δ)²`. With s_d ≈ €1,000 and δ = €500 that is about 25 seeds. Screen on 4–8 seeds; decide on 30–60.
- **Winner's curse:** the best tuning score is inflated by about `sd·√(2 ln k)` [mem]. Re-score on fresh seeds and pick by **mean − 1 SE**.
- **Domain randomisation:** treat instances as (world type, seed) and **report the worst world type**. The Dynamic Pricing Challenge found algorithm rankings swing across market types.

## Explaining it to the jury
- **One-at-a-time sweeps** (5 values × 30 seeds) → tornado charts.
- Optuna `get_param_importances` (PED-ANOVA by default). It describes only the region the search explored.
- **Cumulative ablation:** start at the baseline, add one idea at a time, on the same 60 held-out weeks, with paired 95% CIs. Also do leave-one-out from the final policy.
- **Fix unimportant parameters at round values.** Six meaningful knobs look more elegant than twenty.

## What winners of simulation competitions did
- **Dynamic Pricing Challenge:**
  - a greedy price-matching rule was hard to beat;
  - too much exploration hurts;
  - ignoring the competition hurts more as it gets fiercer.
- **TAC SCM / Travel / Power TAC** [mem]: prediction models (prices, demand) plus simple decision rules, tuned with many simulated games and paired evaluation.
- **Amazon Last Mile 2021:** engineered classical optimisation fitted to the structure of the data, not end-to-end ML.
- **ROADEF:** local search tuned with irace. Over-tuning to public instances cost places on the hidden instances.
- **Kaggle Halite / Kore:** heavily tuned rule bots. RL (Lux S1) needed far more compute.
- **Common pattern:** a simple core policy, many paired simulations, a range of test environments, safety margins on hard constraints, no fragile over-tuning, and picking the strategy by detected regime rather than ensembles.

## Dashboard (per run; summarise as mean, sd, 5th percentile, minimum)

| Group | Metrics |
|---|---|
| Outcome | margin, margin per order, revenue, cost, paired Δ with CI |
| Constraint | on-time (mean, min, 5th percentile, count of weeks < 92% / < 90%), late refunds, undelivered |
| Commercial | win rate, average quote ÷ list, average fee ÷ typical fee |
| Operations | drops, expiries, deadline warnings, direct offers sent / accepted, failed visits |
| Breakdowns | by town, day and world type |
| Metadata | parameter id, git hash, seeds, server rate limit, wall time |

## 12-hour protocol (A = tuner and infrastructure, B = analysis and dashboard, C = policy ideas and ablations)

| Hours | Stage | Weeks | Notes |
|---|---|---|---|
| 0–1 | Setup | ~300 | Freeze seed pools. Baseline on 60 seeds → sd(OT), sd(M), paired s_d → choose τ |
| 1–2 | Screening | ~600 | One-at-a-time sweeps on 8 seeds; keep ≤12 active parameters |
| 2–6 | Broad search | ~2,500 | TPE, 8 workers, objective J, 4 → 12 seeds racing, kill a candidate on any week < 90% |
| 6–9 | Refine | ~2,000 | CMA-ES from the top 3; 16 rotated seeds per generation |
| 9–10 | Select | ~600 | Top 10 on 60 selection seeds; choose by the lower bound of J and the 5th percentile of on-time |
| 10–11 | Validate | ~400 | Winner and runner-up on 200 final seeds; rule-of-three bound ≤ 1.5% |
| 11–12 | Jury | ~400 | Ablation, importance chart, tornado plots, trade-off frontier |

Cut each stage by about 40% if the server is congested (the broad search first). We have far less time than 12 clean hours, so compress it.

## Sources
- https://arxiv.org/abs/1804.03219
- https://rdrr.io/cran/irace/src/R/irace-options.R
- https://automl.github.io/SMAC3/latest/advanced_usage/9_parallelism/
- https://optuna.readthedocs.io/en/latest/reference/samplers/generated/optuna.samplers.NSGAIISampler.html
- https://optuna.readthedocs.io/en/latest/reference/generated/optuna.importance.get_param_importances.html
- https://routingchallenge.mit.edu/last-mile-routing-research-challenge-2021-winners
