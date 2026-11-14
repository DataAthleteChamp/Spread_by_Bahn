# Hidden mechanics catalogue (statistical hunt over 64 L8 worlds, ~66k requests, 33k gigs, 1.76M views)

## Hard facts
1. **The dealer decision is a hard threshold per request:** 0 inversions in 2,367 paired comparisons (same request, different quotes). The "noise" is a fixed draw per request, shared by all teams in the final.
2. **The exact list price:** `next_day = 20 + 0.25·km` (map km), `same_day ×1.075`, `within_3_days ×0.93`. The residual is pure rounding.
3. **The competitor price noise floor is ≈0.16 log** after exact list + trust + seed-day + town + dealer×day effects (β ≈ 11, symmetric curve). Request features (notes, lead, EV, private) add nothing; premium −4%; each extra option offered −2.5%.

## Catalogue

| Mechanic (trading analogue) | Evidence / size | Detection | Technique |
|---|---|---|---|
| Fair value threshold | σ ≈ 0.16 | Day level sd 0.06 after 10 quotes | Logistic, exact list, β ≈ 11 |
| Day regime | sd 0.06–0.08 | 10–20 quotes | Reset each morning |
| Price war (jump) | −0.19 ± 0.05; Mon/Thu most often | ~10 quotes | Shift −0.06, freeze, restore |
| **Snow** | Forecast exactly 24 h ahead, full day, 2–6 places, Tue–Fri; drive ×1.23; late 22% vs 19.5%; slower booking | The event | Drive ×1.25 in gating, +0.1 opening fee, +5% quote |
| Flu | Not visible in views; booking-within-60-min dips to 0.6–0.75× | Weak | Tighten risk when the 60-min hit rate drops by 11:00 |
| **Bulk order (iceberg)** | 1/week, 30–40 cars, one yard, one ready time. Late: ≤10 yard drivers **52%**; 10–40 → 30%; 40–100 → 9%. Wins ≤ 0.1×yard drivers: 0/65 late | batchId + same ready time after 3–5 requests | **Cap wins at min(12, 0.1 × yard drivers)** |
| Dealer batches | 48% of requests in batches (median 2), +0.11 residual correlation | batchId | Count jointly against capacity |
| Order flow | Batch arrivals are Poisson (Fano 0.99). Flat 9–18 h. Mon 225 → Fri 179 | — | No Hawkes |
| Win momentum | Fully explained by day/lane levels | — | Nothing extra to exploit |
| Adverse selection | No winner's curse beyond lane effects | — | Price on lane and load |
| Option choice | At equal ratio, same_day is chosen 88%; at a +10–20% premium, 54% | — | **Same_day premium** |
| **Friday same_day** | **20.8% late** (other days 5–8.6%); Friday booking slowest | Calendar | +15% or strict risk |
| **Posting clock** | 08h: 1 min median wait; 15–16h: 20–24 min; 19–20h: 1–6 min. Next-day pickups book in 1–3 min | Calendar | Post next-day gigs in the evening or 07–08h; same_day won after 14:00 → open 1.1× |
| Changes / cancellations | Changes 6.1% (38% destination, +28 km); cancellations 1.2% (11% "continues": full fee) | Event | Ignore |
| Real drive time | Median 1.00× road minutes, p90 1.16× | — | Pad 15% |

## Top changes (offline estimates, untested)
1. Bulk cap
2. Same_day premium ×1.08–1.12
3. Friday same_day +0.15 log
4. Exact list + trust in the win model (β 11)
5. Posting clock
6. Snow handling

## Final-day risks
1. A bulk order at a yard with few drivers (13 late in one week).
2. A Friday combining war + snow + same_day.
3. An undetected flu on the peak day.
