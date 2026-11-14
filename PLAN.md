# Experiment queue toward the final (Sun 08:00). Updated Sat ~15:00

Principles (user research): freeze baselines as pinned params; evaluate on untouched paired L8 seeds with whole-week results; select on total qualified profit + qualification failures; Thursday-start and restart tests for robustness; logs alone can't evaluate counterfactual prices.

| # | Experiment | Why | Status |
|---|---|---|---|
| 1 | validate8: C7 vs C7+risk_max .15 vs C7+risk_max .15+flu(0.5), 20 fresh seeds | Two positive same-seed results need confirmation | running |
| 2 | Booking-hazard + drop model → fee DP schedule (agent) → integrate into fee_schedule → A/B | Bet #1: timing matters (late_h +€480; blanket raises −€1k) → selective intervention | model being built |
| 3 | Pickup-window capacity forecast (committed unstaffed + expected pending wins, by pickup day × region vs supply) → admission cost | Load by *pickup window*, not arrival day; reusable-capacity allocation (Goyal–Iyengar–Udwani) | to implement |
| 4 | Joint delivery-menu pricing | choice model fitted: P(sd)=σ(2.46−9.77Δ); premiums lose (−447,−50) | deprioritised |
| 5 | Portfolio SLA: P(week ≥ 90%) ≥ 99% with correlated shocks (snow/flu/bulk) via Monte Carlo of pending orders | Rare bad weeks (89.8%) remain | after 3 |
| 6 | FREEZE final config → `lab/final_config.json` (resolved params, git hash); 40-week untouched validation + Thursday-start + restart tests | Robustness for the final | Sat evening |
| 7 | 20:00 test final with the frozen config, live clock | Last live rehearsal | 19:40 |
