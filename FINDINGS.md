# Findings from our own data

## Setup (done 2026-11-14)
- Team **The Delusionals**. Key in `.env` (gitignored; never commit it).
- `.venv` with the official kit (`spread` 0.1.0) + numpy/pandas/scipy/sklearn.
- Connection: ~70 ms per request from here. Map saved to `data/map.json` (30 towns, 900 roads).
- **Determinism confirmed:** starter, level 8, seed `spread-1` → **−€72,612.51**, exactly the handbook's number.
- Starter week took **45 s wall time** (1,891 requests). Almost all of it is network round trips, not server compute.
- **Practice weeks are NOT submissions.** Only `--board` ranking runs and the final count. Experiment freely; never run `--board` by accident.

Load the env in a shell:
```sh
set -a; . ./.env; set +a
```

## Week 1 data (starter, level 8, seed spread-1)
Source: `data/reveal-wea254964db8276b04542/` (reveal CSVs).

### The money math
| | p10 | median | p90 |
|---|---|---|---|
| List price | €33 | €65 | €156 |
| Typical fee | €27 | €60 | €150 |
| **List ÷ typical fee** | 0.93 | **1.11** | 1.46 |
| **Paid fee ÷ typical fee** (starter) | 1.0 | **1.5** | 2.5 |

→ **At list price with typical fees, the margin is only ~10%.** At level 8 drivers are scarce, so the starter pays ~1.5× on average and loses money on most cars.
→ The margin has to come from **(a) quoting above list** (the competitor is +26–54%) and **(b) paying close to or below the typical fee**, by finding the drivers for whom the car is cheap: nearby, returning home, or chaining.

### The week's shape
- 1,037 requests (~200 a day). The starter won 959 and lost 78.
- **41% have notes** (fi 281, en 124, sv 19). Trade-ins are rare (1.4%).
- Options offered: same_day 732, next_day 943, within_3_days only 162.
- The starter got 45% on time, for both same_day and next_day.

### Drivers vs demand, by pickup town (this world; level 8 shuffles town supply per world)
832 drivers: Helsinki 295, Tampere 109, Espoo 76, Vantaa 47, Oulu 39 … and **0–2 drivers** in Hyvinkää, Lempäälä, Pori, Rauma, Kemi, Kouvola, Kajaani.

| Pickup town | Drivers | Requests from | Drivers per request | Starter on-time |
|---|---|---|---|---|
| Vantaa | 47 | 187 | 0.25 | 47% |
| **Hyvinkää** | **2** | **166** | 0.01 | 48% (probably the bulk-order yard) |
| Helsinki | 295 | 102 | 2.89 | 53% |
| Lahti | 34 | 71 | 0.48 | **22%** |
| Oulu | 39 | 68 | 0.57 | **23%** |
| Kuopio | 23 | 10 | 2.30 | 78% |
| Rovaniemi / Kemi / Joensuu | 5 / 0 / 7 | 11 / 4 / 4 | — | **0%** |

→ **Supply per town is the strongest signal for "can we staff this?"** It is in the driver list (`/drivers`) at the start of the week. The far north and towns with no drivers are traps.

### Event volume
- 168k `gig_viewed` events in one week. These are rich data on which drivers are active and where.
- 1,312 bookings, **343 drops**, 587 gig expiries, 1,249 deadline warnings.
- Only 26 failed visits: notes matter, but they are not the biggest leak here.

## Ideas this suggests (to test)
1. **Quote multiplier by supply:** high where drivers per request is low, decline the 0-driver towns unless the price is very high.
2. **Capacity cap per pickup town per day**, from the driver count.
3. **The opening fee matters most:** the starter's ramp leads to 343 drops and 587 expiries.

## Experiment log

### 2026-11-14 sweep1: markup policy, level 8, seeds bench-0..7 (paired)
| Variant | Margin/wk | On-time (mean / min) | Ranked | Won | Δ vs markup (t) |
|---|---|---|---|---|---|
| starter (spread-1 only) | −€72,613 | 45.5% | 0/1 | 949 | |
| markup (mult 1.30, min_drivers 3, flat fee 1.1 → 1.6 late) | −€14,435 | 72.9% / 56.4% | 0/8 | 534 | — |
| markup mult=1.45 | **€141** | 82.2% / 64.4% | 3/8 | 365 | +€14,575 (t=5.3) |
| markup min_drivers=12 | −€5,191 | 82.0% / 64.9% | 4/8 | 411 | +€9,244 (2.7) |
| mult=1.45, min_drivers=12, fee 1.3 → 2.0 | −€1,162 | **88.5%** / 75.4% | 4/8 | 281 | +€13,273 (3.4) |

Takeaways:
- **A higher markup is the biggest lever** (t=5.3). We're still well below House best (~€14k/wk, ~97% on time, ~365 won).
- Even winning only 281 orders, on-time is under 90% in half the weeks. **Failing to staff is the core problem, not volume.** Next: per-request feasibility (road minutes vs time left, drivers near the pickup *and* the delivery), better note handling, and direct offers.

### 2026-11-14 tournament1 + sweeps 2–5 (level 8, seeds bench-0..7, paired; ~330 weeks)
**Strategies (all vs markup 1.45 / min_drivers 12):** S7_safety +€6.1k (t=5.7), S6_cap +€5.4k, S2_gate_scarce +€3.9k, S3_hire +€4.6k. The tracker at win_target 0.45 = −€5.1k (wins too much and on-time collapses). Direct offers: ~0 accepted (most expire unread), so useless as implemented. S8_full is worse than its parts (the tracker drags it down).

**Lateness diagnosis (2 weeks, 527 orders):**
- An order with a `deadline_close` warning is late **62%** of the time vs 2% without one.
- A drive over 5 h: 24% late.
- Delivery to the far north / remote towns: 19–40% late.
- Failed visit: 43% late.
- The late pattern: *nobody books → warning → warning → booked too late.* Every late order did get a driver.
- Most gigs book within **~6 min at 0.9× typical**. About 15% are "hard" and nobody touches them.

**Fees:**
- Low opening fees with escalation don't help (drivers learn raises).
- Higher fees and early escalation buy on-time 1:1 with margin.
- About 0.9× typical is near optimal for easy gigs.

**Quote price:**
- Steep: 1.35× → 260 wins, 1.45× → ~165, 1.6× → 73.
- Remote-delivery uplift (`scarce_b_k=0.4, long_k=0.05`) → 93.5% on-time, 7/8 ranked.
- Best so far: `S7_safety:scarce_b_k=0.4,long_k=0.05,mult=1.4` → **€6.25k/wk, 92.3% on-time, 6/8 ranked, 209 won**.

**P&L (best config):** revenue ~€95/order, driver fee ~€55/order (58%), margin ~€36/order. Leaders: €43/order × 370. **Our gap is volume (210 vs 370), not unit economics.** The fitted win curve (β ≈ 9 per log unit) puts the capacity-free optimum at ~1.15–1.25× list with ~50% win rate. So: win more orders, but **only those we can staff**. That needs a per-request staffability (P(late)) model → datagen1 is running (16 weeks, mult 1.2, reveal).

### 2026-11-14 learned staffability model + sweep6
- `lab/train_risk.py`: logistic P(late) on quote-time features, trained on 20 runs / 11,767 orders. Mostly overloaded datagen weeks, so the absolute level is too high: **use it as a ranking**. **Held-out-world AUC 0.72.**
  - Top drivers of lateness: drive² (+), slack (−), reach of the delivery town (−), premium (+), reach of the pickup town (−), later weekday (+).
- sweep6 (vs best hand-tuned, €6.25k / 92.3% / 6 of 8 ranked):

| Variant | €/wk | On-time (mean / min) | Ranked | Won |
|---|---|---|---|---|
| risk, mult 1.30, risk_max 0.4, k 0.5 | **€7,291** (+€1.0k, t=2.2) | 94.7% / 84.3% | 7/8 | 269 |
| risk, mult 1.35, risk_max 0.4, k 0.5 | €7,087 (+€0.8k, t=3.8) | 96.2% / 87.9% | 7/8 | 223 |
| **risk, mult 1.25, risk_max 0.35, k 0.8** | €6,756 | **97.3% / 93.2%** | **8/8** | 238 |

  → **The model moves the whole frontier: more orders AND better on-time.** First config with every week ranked and a worst week of 93%.
