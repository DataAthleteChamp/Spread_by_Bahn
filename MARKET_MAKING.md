# Spread as market making (research wave, Sat midday)

## Mapping (Avellaneda–Stoikov / GLFT / Cartea–Jaimungal–Penalva)

| A-S | Spread |
|---|---|
| mid s | expected marginal staffing cost c(town, day) |
| δ | markup p − c |
| λ(δ) = A e^{−kδ} | win probability (logistic, β ≈ 7.8; k ≈ β(1−P)/p) |
| q | net short driver capacity per town/day (won but unstaffed − free drivers) |
| γσ²τ | slope of the driver supply curve (marginal fee per extra unfilled order) |

**Markups**
- Myopic optimum `m* = 1/(β(1−P)) ≈ 21%`. We run ~30%: the extra ~9 points is the shadow price of drivers, which should vary **by town**.
- Quote rule (CJP): `p = c_town + (1/γ)ln(1+γ/k) + Δ_town·(q+½)`, with γ = 0.01/€ → middle term ≈ €12; Δ_town ≈ €3–6.

**Driver side = execution with a deadline.** Drivers learning our raises is permanent market impact (Almgren–Chriss / Obizhaeva–Wang). Prefer a near-flat posted fee and one hazard-triggered move.

## Microstructure analogues
- **Adverse selection:** the competitor's lane factor is high exactly where staffing is hard, so our wins concentrate on hard lanes (winner's curse).
  - Fix: a **lane-specific cost** (shrunken realised fees).
  - Monitor with markouts per lane.
- **Quote fading** when inventory is short. **Pennying:** quote `p̂_c·e^{−ε}`, choosing ε by maximising expected margin.

## Exploiting the adaptive competitor (Deng–Schneider–Sivan: you can at least reach Stackelberg against learners)
- We're capacity-bound (~390 of ~1000 requests), so **losing is cheap and manipulation is cheap**.
1. **Rotation / pulsing:** starve dealer group A (quote 1.5× list) so the competitor raises A tomorrow, harvest group B; swap daily.
2. **Threshold riding:** keep each dealer's share just under the competitor's cut threshold.
3. **Day after the war:** don't chase on the war day; harvest the next day (the competitor raises after "we won few").
4. **Outage:** price against the backup (+20–25%).
5. **Morning knapsack:** win only the top capacity × margin.

## Statistics and filters
- **Per-dealer EKF** on ln p_c (TrueSkill-style):
  - `p̂ = σ(β(μ − ℓ))`
  - `v⁺ = 1/(1/v + β²p̂(1−p̂))`
  - `μ⁺ = μ + v⁺β(y − p̂)`
  - morning: `μ += drift(win share)`, `v += 0.05²`
- **Online refit of β** over the last 300 quotes.
- **Arrival dispersion** (Poisson vs Hawkes), win-rate autocorrelation per dealer, buy-side depth (drivers per town/hour), booking hazard logit.

## Code references
- Hummingbot `avellaneda_market_making.pyx`, `trading_intensity.pyx` (curve_fit A e^{−kδ})
- hftbacktest GLFT tutorial
- sublee/trueskill
- mbt_gym

## Ranked experiments
1. Per-dealer EKF of the competitor price
2. Lane-specific cost
3. Inventory-faded quote
4. Capacity knapsack
5. Rotation / pulsing
6. Regime detectors
7. Hazard-triggered single randomised raise
8. Online β refit

**Jury candidates:** "we farm the competitor's learning rule" (pulsing); "Avellaneda–Stoikov for logistics".
