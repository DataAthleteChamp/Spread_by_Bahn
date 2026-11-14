# Independent analyst review (Sat, after sweep14). Read-only analysis of runs.jsonl plus 28 reveals.

## Where the gap is
- Per order (econ): revenue €87.3, fee €60.3, refunds €1.5. **Refunds can't close the gap.**
- Price is already at or above the logistic optimum (margin share ~31% vs 1/(β(1−P)) ≈ 25%).
- **Fee is the main lever:** 83% of bookings sit exactly at our 0.9 floor. Drivers within 30 km of the pickup book in a median of **1 minute**.
- Margin per order rises with drive length: <60 min €18.6 … 300–600 min €60. Late rates are flat up to 5 h.

## Blind spots
1. **The risk gate removes the most profitable orders** (P(late) vs margin corr +0.39). Ration on-time per € of margin: `ev −= mu_eur·P(late)`. Offline estimate: **+€1.1–1.5k/wk**.
2. **On-time depends on the peak day.** +10 orders on the busiest day costs −1.55 points; spread over the week, −0.33. The mu controller reacts too late (bench-4).
3. **The price-war day costs 30–60 orders.** Detect it, shift −0.20 for the day, freeze learning.
4. **Private-address orders:** €11.7/order, fee 1.32× typical, 6.6% late. Short drives cost 1.10× → segment the cost.
5. **The low-fee tests were confounded** by the old 2.8× ladder (drivers learned big raises). Re-test a 0.8 opening fee on easy, well-covered gigs.
6. **Offers really are dead:** 21k offers → 152 accepted.

## Bugs
- The urgent reprice can **lower** a hard order's fee (1.3–1.55 → 1.2) at deadline_close.
- **Rejoin wipes learning:** `trust_n` = 0 and θ falls back to the prior after a reconnect (on_event is replayed before the orders are known).
- **The protect stake is ~50× too large:** it uses weekly revenue and ignores that trust rebuilds within ~1 day.
- Econ learning mixes options (minor). `repost` strips note windows. `WAKE_ON` lacks delivered/drop/no_show.
- The mu controller is mostly idle (the warn_ema target is too high).

## Proposed experiments
1. `mu_eur` 100/150/250 with a hard gate at pl > 0.6.
2. Cheap opening fee 0.8 for P(late) < 0.10 with ≥10 drivers within 30 km of the pickup.
3. Fix the urgent downgrade.
4. Segment fee_hat (private 1.30, short 1.10, same_day 1.10, else 0.98).
5. Price-war mode.
6. Peak-day smoothing via a load-based lam.
7. Restart-safe learning.
8. Protect v2 with a realistic stake (cap ~€20).
