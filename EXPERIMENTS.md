# Experiment journal

Each entry has three parts: **Why** (the hypothesis), **Result** (auto-appended table), and **Decision** (what we do next and why).
Every experiment ran on practice worlds at level 8, paired on the same seeds, unless it says otherwise. Raw data is in `results/runs.jsonl`; details are in FINDINGS.md.

**Goal:** beat #1 (Juhus, €16.0k/week, 97.5% on time). Stretch goal: €20k+/week. Never accept a week under 90% on time.

---

## History so far (Sat morning, before the journal existed)

| # | Experiment | Why | Outcome | Decision |
|---|---|---|---|---|
| E1 | starter on spread-1 | Check that our setup reproduces the handbook | −€72,612.51, exact | The bench can be trusted |
| E2 | sweep1: markup mult/min_drivers/fees | Does quoting above list fix the starter? | mult 1.45: +€14.6k vs 1.30 (t=5.3), still ~€0 | Price is the strongest lever; staffing is the problem |
| E3 | tournament1: 8 smart presets | Which idea helps on its own? | S7_safety best (+€6.1k vs markup). Tracker at a 45% win target: −€5.1k. Direct offers: ~0 accepted | Keep safety, gate, scarce. Drop the tracker at high targets. Fix or drop offers |
| E4 | diagnosis of late orders | Why are we late? | Warned orders are 62% late; drives >5 h 24%; remote delivery 19–40%. Pattern: nobody books, then the warning comes | Price remote and long orders higher; escalate earlier |
| E5 | sweep2–4: remote uplift, escalation steps | Fix the hard orders | Remote uplift → 93.5% on-time, 7/8 ranked, but only 162 won. Escalation trades margin for on-time 1:1 | Fees are not the lever; volume is |
| E6 | sweep5: low opening fees | Do we overpay on easy gigs? | No: open low + raise = worse (drivers learn the raises) | Keep the opening fee at ~0.9× typical |
| E7 | P&L decomposition | Where is the gap to #1? | Us ~€36/order × ~210; #1 €43 × 370. **The gap is volume** | Win more orders, but only staffable ones |
| E8 | datagen1 + risk model (AUC 0.72 on unseen worlds) + sweep6 | Can a learned P(late) select orders? | **€6.8k, 97.3% on time, 8/8 ranked** (mult 1.25, risk_max 0.35, k 0.8); €7.3k at 94.7% | The model shifts the whole frontier. Next: retrain at normal load; learn the price level online |

## Sat 03:40 — tag `tooltest` — level 8, 1 seeds (bench-0..)
**Why:** tooling smoke test

**Variants:** `starter`; `S7_safety`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
starter                                        1    €-72,458       €0   54.3%  54.3%   0/1     892           —       
S7_safety                                      1      €4,308       €0   85.3%  85.3%   0/1     252           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
starter                                        0.88    1.00     1.00     1.62    -79.5   387    320   966     26
S7_safety                                      0.25    1.50     1.50     1.26     16.8    37     37    79      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 03:49 — tag `sweep7` — level 8, 7 seeds (bench-0..)
**Why:** VOLUME: leaders win 409-458 orders/wk at 35-41 EUR/order. Our win curve says the capacity-free optimum is ~1.15-1.25x list. With the risk gate, do lower prices win more orders while on-time stays >=95%? Also saves reveals at normal load to retrain the risk model (datagen1 was overloaded).

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.15,risk_max=0.35`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.2,risk_max=0.35`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.2,risk_max=0.45`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   7      €6,793   €2,559   97.3%  93.2%   7/7     242           —       
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   7      €5,951   €2,542   93.9%  81.4%   6/7     331       €-842   -1.6
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   7      €6,580   €2,774   94.8%  81.8%   6/7     287       €-213   -0.4
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   7      €7,286   €2,803   93.4%  78.5%   6/7     319        €493    1.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.35    1.44     1.46     1.03     27.5     6     28    14      8
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.49    1.34     1.35     1.10     17.3    17     40    39     11
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.42    1.38     1.40     1.06     22.2    13     36    24      8
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.40    1.41     1.42     1.10     22.3    20     42    39      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep7):** Lower prices win more (242 → 331 orders), but € per order falls from 27.5 to 17.3, so margin doesn't grow. Leaders get €35–41/order at 450 orders, which implies driver cost ≈ 0.8× typical; we pay 1.03–1.10×. → **The lever is cost per order (JIT posting, pairing), not price.** Retrained the risk model (v2) including the sweep7 normal-load weeks.

## Sat 03:50 — RANKING RUNS — `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,mult=1.25,risk_max=0.35,risk_k=0.8`
**Why:** First real leaderboard check of our best practice config (E8: €6.8k, 97.3%, 8/8 ranked on bench seeds). Does practice performance transfer to the secret ranking worlds?

- run 1: €9,210, on-time 98.2%, won 330
- run 2: €9,602, on-time 97.9%, won 383
- run 3: €6,022, on-time 95.0%, won 239
- run 4: €8,008, on-time 98.4%, won 252
- run 5: €7,951, on-time 96.8%, won 316
- **5 ranking runs: total €40,793 (€8,159/week), min on-time 95.0%**

**Decision (board1):** On the real leaderboard we're **rank 45 of 56: €40,793 over 5 weeks (€8.2k/wk), 97.4% on time, 5/5 ranked.** The ranking worlds run ~€1.4k/wk better than our bench seeds, so the bench is slightly pessimistic (good). Top 10 ≈ €71k (€14.3k/wk); #1 €83.2k. Need roughly +75%. Next lever: cost per order → pairing orders into one gig.

## Sat 04:04 — tag `sweep8` — level 8, 8 seeds (bench-0..)
**Why:** Pain-point fixes: (1) just-in-time posting (one notification per order; most drivers book only next day), (2) notes read at first post (plates/manual) + charging stop only >200km (rule 3), (3) option steering to slack, (4) econ policy = argmax P(win)*(p-cost) with online-learned world/dealer price level. Risk model now v2 (AUC .79, trained incl. normal-load weeks).

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,risk_max=0.25`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,notes2=1,charge_fix=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,same_day_mult=1.15,w3_mult=0.9`; `econ`; `econ:defer=1,notes2=1,charge_fix=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €6,979   €2,544   93.2%  79.6%   7/8     342           —       
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €6,536   €2,231   95.5%  86.5%   7/8     313       €-443   -1.9
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,693   €2,791   93.9%  81.2%   7/8     347        €714    3.6
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,044   €2,581   94.5%  81.3%   7/8     346      €1,065    6.3
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,310   €2,545   92.8%  77.4%   7/8     345        €331    2.4
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €6,703   €2,413   96.6%  93.1%   8/8     306       €-276   -0.5
econ                                           8      €7,505   €1,852   95.7%  88.1%   7/8     288        €526    1.5
econ:defer=1,notes2=1,charge_fix=1             8      €7,825   €1,785   96.0%  89.0%   7/8     291        €846    2.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.44    1.36     1.38     1.11     19.8    22     46    45      9
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.46    1.35     1.36     1.07     20.4    13     36    28      8
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.09     21.5    20     47    41     10
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.07     22.7    18     45    39      7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.10     20.7    23     45    47      7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.39    1.35     1.34     1.01     21.3    10     35    19      5
econ                                           0.43    1.41     1.39     1.10     25.4    12     33    26      8
econ:defer=1,notes2=1,charge_fix=1             0.43    1.42     1.39     1.08     26.3    11     29    22      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep8):**
- **JIT posting +€714 (t=3.6); JIT + notes2 + charge_fix +€1,065 (t=6.3)** → new base `B+F` ≈ €8.0k at 94.5%. Keep all three.
- `econ` gives the highest €/order (25–26 vs ~21) and the best on-time among high-margin variants (96%): €7.8k with F.
- Option steering (same_day 1.15, w3 0.9) is the safest (min OT 93.1%, 8/8) but −€0.3k.
- Risk model v2 is more permissive at risk_max 0.35 (342 won, 93.2%).
- Next: pairing on top of B+F and econ+F.

## Sat 04:06 — tag `pairsmoke` — level 8, 1 seeds (bench-0..)
**Why:** (not given)

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,pair=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   1      €6,750       €0   92.4%  92.4%   1/1     340           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.42    1.37     1.37     1.12     19.2    26     50    49      1

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 04:23 — tag `sweep9` — level 8, 8 seeds (bench-0..)
**Why:** Pairing: JIT alone defers only ~32 orders/wk so pairing barely fires (3 pairs). Add batching window (hold won orders 30-60 min when slack>6h) to pair A(a->b)+B(b'->c) with b' near b: removes driver's trip home => lower cost/order (leaders imply ~0.8x typical fee). Also econ with cheaper cost assumptions.

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,pair=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,pair=1,batch_min=30`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,pair=1,batch_min=60,pair_gap=75`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,pair=1,batch_min=60,pair_gap=75,pair_disc=0.75`; `econ:defer=1,notes2=1,charge_fix=1`; `econ:defer=1,notes2=1,charge_fix=1,pair=1,batch_min=60,pair_gap=75`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,044   €2,581   94.5%  81.3%   7/8     346           —       
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,112   €2,859   94.3%  81.3%   7/8     346         €68    0.4
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,926   €2,749   92.9%  83.8%   6/8     338       €-119   -0.4
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,370   €2,623   93.0%  86.4%   7/8     335        €326    1.3
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,575   €2,520   90.7%  80.6%   6/8     322       €-469   -1.2
econ:defer=1,notes2=1,charge_fix=1             8      €7,825   €1,785   96.0%  89.0%   7/8     291       €-219   -0.6
econ:defer=1,notes2=1,charge_fix=1,pair=1,ba   8      €8,147   €1,879   94.6%  88.9%   6/8     289        €102    0.2
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,206   €2,151   95.7%  90.2%   8/8     356        €161    0.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.07     22.7    18     45    39      7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.08     22.7    18     46    39      7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.44    1.36     1.38     1.15     22.9    23     30    46      9
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.43    1.36     1.38     1.18     24.5    23     29    46      9
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.42    1.37     1.38     1.21     23.1    28     28    60      9
econ:defer=1,notes2=1,charge_fix=1             0.43    1.42     1.39     1.08     26.3    11     29    22      7
econ:defer=1,notes2=1,charge_fix=1,pair=1,ba   0.43    1.41     1.39     1.17     27.6    15     22    26      9
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.34     1.32     1.08     22.5    15     42    31      6

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep9):** Pairing fires with batching (174 pairs/wk) but gains only +€326 (t=1.3): paired gigs book slower, warnings go up, fee/typ 1.07 → 1.18. Keep as an option (batch 60, gap 75); not the breakthrough. `econ` with late_cost 0.4 / fee_hat 1.0: €8.2k, 95.7%, **8/8 ranked**. **Key insight:** we now win ~346 orders (≈ Juhus 373) with similar late counts but €23/order vs €43. The gap is per-order economics → test dealer trust pricing (+1% per on-time order per dealer, cap 25%).

## Sat 04:39 — tag `sweep10` — level 8, 8 seeds (bench-0..)
**Why:** Per-order economics gap (us EUR23/order vs Juhus EUR43 at similar volume). Rules: each dealer accepts +1% price per on-time order delivered (cap 25%), late halves. Price that explicitly (trust_k = share of the 1% taken as price). Also test lower fee floor 0.8 (gigs book in ~6 min at 0.9).

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,trust=1,trust_k=0.5`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,trust=1,trust_k=1.0`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,trust=1,trust_k=1.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,trust=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,trust=1,fee_floor=0.8`; `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,trust=1,trust_k=1.0,fee_floor=0.8`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,044   €2,581   94.5%  81.3%   7/8     346           —       
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,556   €2,896   95.4%  84.5%   7/8     309        €512    3.3
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,203   €2,736   95.4%  85.0%   7/8     270        €158    0.6
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,437   €1,941   96.4%  88.7%   7/8     237       €-607   -1.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,206   €2,151   95.7%  90.2%   8/8     356        €161    0.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,072   €2,173   95.4%  87.5%   7/8     352         €28    0.1
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €5,961   €2,029   93.0%  86.6%   6/8     348     €-2,084   -4.7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €7,252   €2,580   93.9%  83.0%   7/8     268       €-793   -7.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.45    1.36     1.38     1.07     22.7    18     45    39      7
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.40    1.42     1.43     1.06     26.8    13     38    25      6
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.35    1.45     1.44     1.05     29.4    12     31    22      5
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.30    1.47     1.44     1.05     30.9     8     24    16      5
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.34     1.32     1.08     22.5    15     42    31      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.34     1.33     1.08     22.3    15     40    32      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.34     1.32     1.18     16.6    23     32    55      8
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.35    1.44     1.44     1.11     26.2    16     27    34      5

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep10):** Trust pricing trust_k 0.5: **+€512 (t=3.3)** → keep. Higher trust_k loses too many wins (the competitor also cuts prices where we win). **Fee floor 0.8 hurts again** (−€0.8k to −€2.1k): the third confirmation that cheaper fees fail; 0.9× is the floor. Plateau ≈ €8.5k with hand-tuned rules → go back to data: fit the real win curve (β, lane/town/option/day structure) offline from the 28 reveal weeks.

## Sat 04:56 — tag `sweep11` — level 8, 8 seeds (bench-0..)
**Why:** Offline win model (n=40.6k quotes, beta=7.84) found lane structure of +-15% (cheap competitor into Helsinki area, dear into remote towns; pickups from Vantaa/Hyvinkaa +10%) and world level +-13%. econ+winmodel prices each lane with that prior and learns world/dealer level online.

**Variants:** `S7_safety:risk=1,scarce_b_k=0,long_k=0,scarce=0,risk_k=0.8,mult=1.25,risk_max=0.35,defer=1,notes2=1,charge_fix=1,trust=1,trust_k=0.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,lane_w=0.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,risk_max=0.45`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,late_cost=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,pair=1,batch_min=60,pair_gap=75`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,eta_w=0.04,eta_d=0.06`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   8      €8,556   €2,896   95.4%  84.5%   7/8     309           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,509   €2,140   95.7%  89.5%   7/8     347        €-47   -0.1
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,704   €1,800   95.7%  89.8%   7/8     346        €147    0.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,669   €2,086   96.0%  89.4%   7/8     351        €113    0.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,414   €2,096   91.5%  85.3%   6/8     416        €858    1.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,623   €1,773   95.8%  89.9%   7/8     335         €67    0.2
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,751   €1,726   93.9%  87.8%   7/8     342        €195    0.4
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,549   €2,024   95.7%  89.5%   7/8     341         €-7   -0.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
S7_safety:risk=1,scarce_b_k=0,long_k=0,scarc   0.40    1.42     1.43     1.06     26.8    13     38    25      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.51    1.35     1.34     1.08     24.0    14     41    30      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.51    1.36     1.34     1.07     24.6    14     38    29      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.35     1.35     1.07     24.2    13     37    29      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.36     1.17     22.2    35     50    78      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.36     1.36     1.07     25.3    13     38    29      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.34     1.33     1.20     25.1    20     24    37      9
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.36     1.34     1.07     24.5    14     38    29      6

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep11):** econ + offline lane prior ≈ base (€8.5–8.7k); lane structure alone isn't the breakthrough. **risk_max 0.45 → 416 orders, €9.4k but 91.5% (min 85%)**: volume is now limited only by staffing. Next: (a) a flat higher opening fee for risky orders only (by P(late)), (b) direct offers v2 to our own drivers who just delivered nearby (they work today, so they read offers), at the app fee.

## Sat 05:13 — tag `sweep12` — level 8, 8 seeds (bench-0..)
**Why:** Volume (risk_max .45 -> 416 orders, EUR9.4k) is limited by staffing (91.5% OT). Two targeted staffing fixes: (a) higher flat opening fee only for risky orders (hard_k*(P(late)-0.15)), no ladder; (b) offers v2: when OUR driver delivers, offer them the nearest unbooked gig at the app fee (rules: drivers who work today read most offers; offers avoid waiting-for-raise).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45,hard_k=1.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45,offers2=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45,hard_k=1.5,offers2=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,offers2=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45,hard_k=3.0,offers2=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.45,hard_k=1.5,offers2=1,offer2_f=0.9`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,704   €1,800   95.7%  89.8%   7/8     346           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,069   €2,168   90.7%  82.0%   5/8     412        €365    1.1
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,596   €2,052   92.7%  85.5%   7/8     424        €892    3.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,958   €2,174   90.3%  82.0%   4/8     413        €255    0.7
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,635   €2,068   92.7%  85.5%   7/8     423        €932    3.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,469   €1,883   93.6%  88.4%   7/8     407        €766    3.4
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,268   €1,769   92.9%  85.4%   7/8     422     €-1,436   -7.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,635   €2,069   92.7%  85.5%   7/8     423        €932    3.6

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.51    1.36     1.34     1.07     24.6    14     38    29      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.37     1.17     21.6    38     50    86      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.39     1.37     1.17     22.2    31     57    64      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.37     1.18     21.3    39     50    89      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.39     1.37     1.17     22.4    30     56    62      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.14     22.9    26     54    50      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.38     1.36     1.24     16.9    30     59    58      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.39     1.37     1.17     22.4    30     56    62      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep12):** The **risk-targeted opening fee (hard_k 1.5) gives +€892 (t=3.6) → €9.6k at 424 orders**, 92.7% OT (min 85.5%). **Offers v2: 0 accepted of ~100**: drivers who just delivered don't take another gig at the app fee. **Drop direct offers** (3 designs failed). risk_max 0.40 + hard 1.5 = €9.47k, 93.6%, min 88.4%. At volume our fee rises to 1.17× typical; the urgent ladder (up to 2.8×) pays ~1.5× typical to avoid a ~25% refund, which is uneconomic except for the SLA → test capping the urgent and late fees.

**Data (9.3k orders, sweep7/diag):** fee/typical by won option: same_day 1.15 (late 6.6%), next_day 1.03 (3.1%), within_3_days 0.99 (1.0%). Fees are ~70% of revenue; refunds are small. → econ `opt_fee=1` uses option-specific costs so same_day is priced higher and the dealer is steered to slack options.

## Sat 05:31 — tag `sweep13` — level 8, 8 seeds (bench-0..)
**Why:** Urgent ladder (1.9->2.8x typical) and late step (1.7x) pay far more than the lateness refund they avoid; at volume fee/typ rises to 1.17. Cap them and let the risk model keep OT. Also pairing on top of the new base.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,urgent_open=1.5,urgent_max=2.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,urgent_open=1.3,urgent_max=1.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,late_h=6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,pair=1,batch_min=60,pair_gap=75`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,risk_max=0.45,urgent_open=1.5,urgent_max=2.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,471   €1,883   93.4%  88.4%   7/8     407           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,069   €2,024   93.4%  86.1%   7/8     406        €599    3.7
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,307   €1,931   93.1%  84.1%   7/8     404        €836    5.0
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,703   €1,875   93.7%  86.2%   7/8     408        €232    1.4
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,418   €1,763   93.2%  85.3%   7/8     406        €947    6.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €8,888   €1,541   94.5%  88.4%   7/8     409       €-583   -3.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,645   €2,169   92.2%  84.0%   5/8     399        €174    0.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,200   €1,880   92.4%  83.9%   7/8     420        €730    3.7

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.14     22.9    26     54    51      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.11     24.4    26     56    51      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.35     1.09     25.1    27     54    54      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.12     23.4    25     51    58      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.08     25.2    27     54    57      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.38     1.36     1.17     21.3    22     57    39      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.35     1.26     23.7    30     34    58     11
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.37     1.12     23.9    31     56    63      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep13):** **Capping escalation pays: fee_late 1.4 + urgent 1.5→2.0 gives +€947 (t=6.6) → €10.4k**, on-time unchanged (93.2%). The urgent ladder was overpaying relative to the lateness it prevented. Next: push the caps lower, plus option-specific cost and the regional learner. The min-OT weakness (one seed ~85%) remains → a safety pass is needed before the final.

## Sat 05:47 — tag `sweep14` — level 8, 8 seeds (bench-0..)
**Why:** Escalation caps gave +947 (t=6.6). Push lower (late 1.25/1.1, urgent 1.3-1.6/1.2-1.4), add option-specific cost (same_day 1.15 vs next_day 1.03 vs w3 .99 measured), regional online offset (outage/local moves), more volume.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0,opt_fee=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.25,urgent_open=1.3,urgent_max=1.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.25,urgent_open=1.3,urgent_max=1.6,opt_fee=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0,opt_fee=1,eta_a=0.05`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0,opt_fee=1,risk_max=0.45`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.4,urgent_open=1.5,urgent_max=2.0,opt_fee=1,hard_k=1.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,418   €1,763   93.2%  85.3%   7/8     406           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,015   €1,873   94.1%  89.7%   7/8     359       €-402   -2.1
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,934   €1,878   92.7%  84.1%   7/8     404        €517    3.7
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,047   €1,571   92.4%  84.8%   7/8     400        €629    3.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,287   €1,705   93.4%  85.3%   7/8     358       €-130   -0.7
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,146   €1,811   94.1%  88.5%   7/8     358       €-272   -1.7
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,620   €1,850   94.0%  88.3%   7/8     374        €203    0.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,717   €1,659   94.4%  90.7%   8/8     363        €300    1.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.08     25.2    27     54    57      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.39     1.39     1.06     27.3    20     42    44      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.37     1.36     1.04     26.6    29     53    64      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.3    30     50    75      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.38     1.38     1.03     28.3    23     40    49      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.39     1.38     1.07     27.8    20     42    43      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.40     1.40     1.08     27.9    22     44    50      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.38     1.39     1.05     29.0    20     40    44      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep14):** **Lower caps (fee_late 1.1, urgent 1.2→1.4) → €11.05k (+€629, t=3.6)** at the same on-time. Fee escalation barely buys on-time; it was mostly waste. opt_fee + hard_k 1.0 → €10.7k but the **safest: 94.4%, min 90.7%, 8/8**. Data (trust trajectories): dealer D01 is about 1/3 of all requests; trust hits 25 by Tue–Wed, and one late order halves it (~€2k of future revenue). → test trust protection (`protect`: the at-stake value enters the quote cost and the opening fee).

## Sat 06:03 — tag `sweep15` — level 8, 8 seeds (bench-0..)
**Why:** Trust is capital: D01 (~1/3 of requests) reaches trust 25 by Tue-Wed and one late order halves it (~EUR2k future revenue). protect=1 adds P(late)*trust-at-stake to quote cost and bumps opening fee for high-trust dealers. Also near-zero escalation (escalation barely buys OT).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,opt_fee=1,hard_k=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,opt_fee=1,hard_k=1.0,protect=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,fee_late=1.0,urgent_open=1.0,urgent_max=1.2`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1,risk_max=0.45`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1,eta_d=0.08`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1,protect_fee_k=1.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,047   €1,571   92.4%  84.8%   7/8     400           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,698   €1,119   94.8%  91.2%   8/8     331     €-3,349   -9.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,672   €1,655   92.3%  87.6%   6/8     354       €-375   -1.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,937   €1,285   95.3%  92.4%   8/8     301     €-3,110   -7.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,409   €1,641   89.3%  82.4%   4/8     386       €-638   -5.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,825   €1,389   94.4%  92.4%   8/8     340     €-3,222   -8.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,465   €1,008   94.5%  91.2%   8/8     328     €-3,582   -9.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €6,720   €1,162   94.7%  90.9%   8/8     331     €-4,327  -12.9

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.3    30     50    75      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.41     1.37     1.15     22.9    17     40    34      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.43    1.38     1.38     1.00     29.7    26     36    64      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.38    1.43     1.39     1.12     26.0    14     34    30      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.36     1.35     1.00     26.6    40     47    92      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.42     1.38     1.17     22.6    18     40    37      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.41     1.35     1.15     22.4    18     38    37      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.40     1.37     1.19     20.0    17     38    34      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep15):** Protect v1 was strongly negative, as the analyst predicted (the stake was ~50× too large). Near-zero escalation and the other variants are in the table above. **Analyst review (ANALYST_REVIEW.md) → bugs fixed:** urgent reprice no longer goes below the opening fee; rejoin now replays quotes and orders so trust and θ survive a restart; protect stake v2 is realistic (cap €20). **Sweep16 tests the analyst's experiments.**

## Sat 06:19 — tag `sweep16` — level 8, 8 seeds (bench-0..)
**Why:** Analyst blind spots: (1) ration on-time per EUR margin (mu_eur*P(late) in EV) instead of uniform risk_max - offline replay +1.1-1.5k; (2) cheap 0.8 opening for easy well-covered gigs (83% bookings at the 0.9 floor; nearby drivers book in 1 min; old test confounded by 2.8x ladder); (4) segment cost (private 1.3, short 1.1); (5) price-war mode; protect v2 realistic stake. Urgent-downgrade bug fixed in all.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=150,risk_hard=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=250,risk_hard=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,easy_f=0.8`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,seg_fee=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,war=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=150,risk_hard=0.6,easy_f=0.8,seg_fee=1,war=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,019   €1,591   92.4%  84.8%   7/8     400           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,522   €2,236   96.2%  92.4%   8/8     175     €-3,498   -8.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €4,593   €1,560   96.5%  92.0%   8/8     102     €-6,426  -30.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,710   €1,618   91.3%  83.8%   6/8     392       €-309   -9.0
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,710   €1,684   93.3%  89.3%   7/8     360       €-310   -1.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,802   €1,720   91.5%  84.8%   7/8     421       €-217   -1.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €7,033   €2,225   94.7%  89.6%   7/8     172     €-3,987   -8.2
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,151   €1,782   92.9%  86.2%   7/8     389        €132    1.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.1    30     50    75      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.21    1.58     1.44     0.96     42.2     6     16    16      5
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.15    1.68     1.45     0.95     44.6     3      8     9      2
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.36     1.34     1.01     26.9    33     45    79      9
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.44    1.40     1.38     1.01     29.3    23     42    58      9
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.52    1.35     1.33     1.03     25.4    35     55    83      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.21    1.59     1.39     0.93     40.1     8     14    21      3
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.2    27     46    67      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep16):** The analyst's offline estimates didn't transfer.
- mu_eur 150/250 over-penalises: wins collapse to 102–175, though those orders earn €42–45 each. → test small mu_eur (20–60).
- easy_f 0.8: −€309 (t=−9). **Fourth confirmation that cheaper fees fail → closed.**
- seg_fee: −€310 but safer (min OT 89.3%).
- war mode: −€217 n.s. (more wins, 421).
- protect v2: +€132 n.s.

**Base stays L ≈ €11.0k.** Concern: L has one week at 84.8% (bench-4), so P(final unranked) ≈ 1/8. The final config must be safer.

## Sat 06:34 — tag `sweep17` — level 8, 8 seeds (bench-0..)
**Why:** mu_eur 150-250 overshot (P(late) ~0.2 typical -> EUR30-50 penalty > margin) but those orders earn EUR42-45. Find the right scale (20-60) to ration on-time per EUR of margin. Combos with protect v2 + war mode (both mildly positive/neutral).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=20,risk_hard=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=40,risk_hard=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=60,risk_hard=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=30,risk_hard=0.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,protect=1,war=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=40,risk_hard=0.6,protect=1,war=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,mu_eur=20,risk_hard=0.5,seg_fee=1,protect=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,019   €1,591   92.4%  84.8%   7/8     400           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,229   €1,628   92.0%  85.1%   7/8     379        €210    1.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,228   €2,054   93.2%  87.8%   6/8     335        €208    0.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,549   €2,363   93.8%  89.6%   6/8     297       €-471   -1.1
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,716   €1,713   92.6%  85.9%   6/8     341       €-303   -1.9
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,706   €1,697   91.6%  83.3%   7/8     407       €-313   -1.8
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,717   €1,999   92.3%  83.4%   6/8     351       €-302   -1.2
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,642   €2,027   93.9%  88.2%   7/8     319       €-377   -1.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.1    30     50    75      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.42     1.39     1.05     29.2    30     46    70      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.37    1.45     1.41     1.02     33.0    22     40    52      5
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.33    1.48     1.43     1.00     34.8    18     36    42      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.39    1.42     1.40     1.02     31.0    24     42    58      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.50    1.36     1.34     1.02     26.0    34     50    78      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.39    1.43     1.37     1.01     30.1    25     42    61      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.37    1.44     1.41     1.02     32.7    19     39    45      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep17):** mu_eur 20/40 → +€210 (n.s.); 60 and the combos are slightly negative. **The hand-tuning plateau is ~€11.0–11.2k.** → start Optuna TPE over 12 econ parameters (objective J: margin − €3k per point under 93% − €5k per week under 90%), 2 trials × 3 seeds in parallel, seeds tune-0..2.

**Robustness (restart_test, best config L, bench-0, killed Wed 12:00 and rebuilt via rejoin):** €11,956 / 90.9% / 418 won vs uninterrupted €12,061 / 91.4% / 418. **Restart costs <1%**; trust (84 counts) and learning survive. The live runtime (`lab.live`) uses the same rejoin.

## Sat 06:50 — tag `debugfail` — level 8, 1 seeds (tune-0..)
**Why:** (not given)

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.407,fee_hat=0.999,winmodel=1,trust=1,risk_max=0.318,hard_k=0.966,fee_late=1.216,urgent_open=1.31,urgent_max=1.4,risk_hard=0.6,trust_k=0.204,late_h=5.426,eta_w=0.038,eta_d=0.011,lead_min=141,mu_eur=16.692`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   1     €12,815       €0   92.7%  92.7%   1/1     397           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.42    1.40     1.43     1.03     32.2    29     48    53      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 07:14: Optuna study `econ1`, 40 trials × 3 seeds (tune-0..)
Base: `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,risk_hard=0.6,trust_k=1.0`. Best trial 15: J=13,046, params `{"risk_max": 0.388, "hard_k": 2.891, "late_cost": 0.609, "fee_hat": 1.133, "fee_late": 1.303, "urgent_open": 1.273, "late_h": 4.825, "trust_k": 0.504, "eta_w": 0.046, "eta_d": 0.014, "lead_min": 89, "mu_eur": 37.592}`

## Sat 07:31 — tag `validate1` — level 8, 8 seeds (bench-0..)
**Why:** Held-out validation (bench-0..7, never seen by Optuna, which tuned on tune-0..2) of top-4 Optuna trials (15,26,9,21) vs old best L; plus T15+safety2 (projected on-time controller). Pick the final/board config by J and min-OT.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.388,hard_k=2.891,late_cost=0.609,fee_hat=1.133,fee_late=1.303,urgent_open=1.273,late_h=4.825,trust_k=0.504,eta_w=0.046,eta_d=0.014,lead_min=89,mu_eur=37.592`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.355,hard_k=2.263,late_cost=0.648,fee_hat=1.134,fee_late=1.24,urgent_open=1.171,late_h=4.928,trust_k=0.563,eta_w=0.044,eta_d=0.023,lead_min=111,mu_eur=36.507`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.405,hard_k=2.715,late_cost=0.414,fee_hat=1.127,fee_late=1.249,urgent_open=1.108,late_h=6.647,trust_k=0.691,eta_w=0.05,eta_d=0.015,lead_min=76,mu_eur=37.304`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.37,hard_k=2.33,late_cost=0.381,fee_hat=1.117,fee_late=1.299,urgent_open=1.319,late_h=4.927,trust_k=0.808,eta_w=0.043,eta_d=0.011,lead_min=102,mu_eur=34.471`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.388,hard_k=2.891,late_cost=0.609,fee_hat=1.133,fee_late=1.303,urgent_open=1.273,late_h=4.825,trust_k=0.504,eta_w=0.046,eta_d=0.014,lead_min=89,mu_eur=37.592,safety2=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,019   €1,591   92.4%  84.8%   7/8     400           —       
econ:defer=1,notes2=1,charge_fix=1,winmodel=   7      €8,593   €2,025   96.1%  94.3%   7/7     240     €-2,278   -7.2
econ:defer=1,notes2=1,charge_fix=1,winmodel=   8      €8,643   €1,875   95.3%  93.4%   8/8     227     €-2,377   -6.2
econ:defer=1,notes2=1,charge_fix=1,winmodel=   7      €8,290   €1,643   94.7%  91.4%   7/7     250     €-2,485   -7.4
econ:defer=1,notes2=1,charge_fix=1,winmodel=   8      €9,147   €1,945   94.5%  89.4%   7/8     277     €-1,872   -6.1
econ:defer=1,notes2=1,charge_fix=1,winmodel=   7      €8,525   €2,039   95.9%  94.2%   7/7     238     €-2,345   -8.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.1    30     50    75      8
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.27    1.56     1.50     1.07     35.1     9     25    17      4
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.26    1.56     1.48     1.04     37.3    10     22    18      5
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.28    1.53     1.47     1.09     32.5    13     29    24      8
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.30    1.51     1.47     1.08     32.4    14     34    25      7
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.27    1.57     1.50     1.07     35.1     9     24    18      4

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (validate1):** **The Optuna configs do NOT generalise.** On held-out bench seeds the top 4 make €8.3–9.1k vs L €11.0k (t −6 to −8), though they are safer (94–96%, min 89–94%). Tuning on 3 seeds where L happened to fail made the tuner over-conservative (q/list 1.56, ~240 wins). Lesson: tune on more seeds, and handle safety *online* rather than by static conservatism. **Bug found and fixed:** fee steps that round to the same minute caused HTTP 400 "Fee steps must be in time order", which rejected the whole action batch (would have lost quotes in the final). Fix: `clean_schedule` + per-action fallback (`safe_act`) in the runner and the live loop.

## Sat 07:48 — tag `sweep18` — level 8, 8 seeds (bench-0..)
**Why:** Static conservatism (Optuna) loses EUR2k on held-out seeds; L is profitable but fails ~1 week in 5-8 (min OT 84%). Online safety2 (projected on-time controller) should keep L's margin in good weeks and tighten only in bad ones. Also the 2 most consistent Optuna findings (fast world-level learning eta_w .045, hard_k 2.5, earlier late step 4.8h) on top.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_k=15`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15`; `econ:defer=1,notes2=1,charge_fix=1,winmodel=1,trust=1,urgent_max=1.4,risk_hard=0.6,risk_max=0.37,hard_k=2.33,late_cost=0.381,fee_hat=1.117,fee_late=1.299,urgent_open=1.319,late_h=4.927,trust_k=0.808,eta_w=0.043,eta_d=0.011,lead_min=102,mu_eur=34.471,safety2=1,s2_target=0.93`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,eta_w=0.045,hard_k=2.5`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,eta_w=0.045,late_h=4.8`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,019   €1,591   92.4%  84.8%   7/8     400           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,946   €1,842   92.4%  84.0%   7/8     395        €-73   -0.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,858   €1,697   92.5%  85.0%   7/8     391       €-161   -1.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,979   €1,793   92.3%  84.1%   7/8     396        €-40   -0.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,086   €1,740   93.0%  86.5%   7/8     389         €67    0.4
econ:defer=1,notes2=1,charge_fix=1,winmodel=   8      €9,129   €1,948   94.5%  89.2%   7/8     276     €-1,890   -6.4
econ:defer=1,notes2=1,charge_fix=1,late_cost   8      €9,870   €1,744   93.0%  86.8%   7/8     395     €-1,149   -4.6
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,007   €1,624   92.7%  86.1%   7/8     393        €-12   -0.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.36     1.03     27.1    30     50    75      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.35     1.02     27.3    29     51    72      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.37     1.35     1.02     27.4    28     48    70      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.37     1.35     1.02     27.2    30     49    72      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.1    27     50    66      7
econ:defer=1,notes2=1,charge_fix=1,winmodel=   0.30    1.52     1.47     1.08     32.5    14     35    25      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.36     1.07     24.6    27     48    67     10
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.49    1.38     1.35     1.02     27.7    28     48    63      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep18):** The safety2 (projected on-time) controller is neutral (±€100): it reacts after the risky orders are already committed. The failing week (bench-4) is a Tuesday overload (115 wins). → test peak-day smoothing (econ `peak`: an extra cost when today's wins exceed peak_budget × the average day).

## Sat 08:04 — tag `sweep19` — level 8, 8 seeds (bench-0..)
**Why:** Analyst: on-time is driven by the busiest day (+10 orders on peak day = -1.55pt OT). Failing week bench-4 = Tuesday 115 wins. Peak smoothing adds a cost when today's wins exceed budget x average day (ref 85 on Monday).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.3`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.3`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=1.0,peak_budget=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=2.0,peak_budget=1.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,086   €1,740   93.0%  86.5%   7/8     389           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €11,033   €1,760   93.1%  87.9%   7/8     386        €-53   -1.5
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,964   €1,822   93.1%  88.4%   7/8     386       €-122   -1.0
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,963   €1,853   93.0%  88.4%   7/8     386       €-123   -1.2
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,780   €1,853   92.9%  89.7%   7/8     379       €-306   -2.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,985   €1,904   92.9%  87.2%   7/8     387       €-101   -1.3
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,769   €1,677   92.8%  89.0%   7/8     378       €-318   -1.9
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €10,688   €1,730   92.8%  88.3%   7/8     377       €-399   -3.7

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.1    27     50    66      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.2    26     48    62      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.35     1.02     28.0    26     46    64      6
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.0    26     46    65      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.47    1.38     1.35     1.01     28.1    26     45    64      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.48    1.38     1.36     1.02     28.0    27     49    67      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.47    1.38     1.36     1.02     28.1    26     45    62      7
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.47    1.38     1.36     1.02     28.0    26     45    65      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep19):** Peak smoothing lowers the peaks (bench-4 Tuesday 117 → 95–100) and lifts bench-4 OT 86.5% → 89.7% (peak_k 0.6, budget 1.0), at −€300/wk; overall neutral. bench-4 also collapses Thu/Fri in every variant (a hard world). **Plateau ≈ €11.0k on bench seeds** (the ranking runs earlier were ~20% above the bench → ~€13k on the real leaderboard). Next: fresh data from the current policy → risk model v3 with load features (wins today per town and in total).

## Sat 08:11 — tag `datagen3` — level 8, 8 seeds (train2-0..)
**Why:** Fresh training data with the current econ policy (behaviour changed a lot since risk v2 data): best config + a looser variant (more orders, more label variety). 16 weeks with reveal -> risk v3 with load features; also new held-out seeds train2-*.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0`; `econ:defer=1,notes2=1,charge_fix=1,late_cost=0.4,fee_hat=1.0,winmodel=1,trust=1,risk_max=0.40,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_max=0.5,mu_eur=0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €12,224   €2,319   93.0%  88.2%   7/8     382           —       
econ:defer=1,notes2=1,charge_fix=1,late_cost   8     €12,723   €3,005   92.0%  87.4%   6/8     401        €499    1.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.46    1.41     1.39     1.02     31.5    26     46    65      8
econ:defer=1,notes2=1,charge_fix=1,late_cost   0.46    1.44     1.42     1.05     31.1    31     52    83     10

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**datagen3 (current policy, new seeds train2-0..7):** best config €12.2k / 93.0% / min 88.2%; looser (risk_max 0.5) €12.7k / 92.0%. **Risk model v3** (`risk_v3.json`, trained on normal-load weeks incl. load features): calibrated base late rate 5.3%, held-out AUC 0.75; `won_today` is the 4th-strongest risk factor (+0.59 std). Its probability scale differs from v2 → thresholds need re-tuning (sweep20).

## Sat 08:28 — tag `sweep20` — level 8, 8 seeds (bench-0..)
**Why:** Risk model v3 (calibrated, load-aware: won_today) vs v2. Thresholds re-scaled to the calibrated probability scale (base late rate ~5%).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,late_cost=0.4,risk_max=0.40`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=1.0,risk_max=0.15,hard_thr=0.05,hard_k=4`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=1.5,risk_max=0.15,hard_thr=0.05,hard_k=4`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=1.0,risk_max=0.10,hard_thr=0.05,hard_k=4`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=1.0,risk_max=0.20,hard_thr=0.05,hard_k=4`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=2.0,risk_max=0.20,hard_thr=0.05,hard_k=6`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=1.0,risk_max=0.15,hard_thr=0.04,hard_k=8`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,hard_k=1.5,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,late_cost=0.7,risk_max=0.15,hard_thr=0.06,hard_k=3`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €10,780   €1,853   92.9%  89.7%   7/8     379           —       
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,876   €1,781   91.8%  86.3%   5/8     413      €1,095    3.7
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €12,180   €1,781   92.1%  86.7%   5/8     398      €1,400    5.6
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,677   €1,908   93.6%  88.3%   7/8     390        €897    2.4
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,694   €1,850   89.9%  84.5%   5/8     424        €913    3.2
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,598   €1,866   93.0%  87.3%   6/8     390        €818    2.2
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8      €9,374   €2,056   92.9%  88.1%   7/8     418     €-1,407   -3.6
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €12,074   €1,929   90.4%  83.7%   5/8     415      €1,294    3.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.47    1.38     1.35     1.01     28.1    26     45    64      7
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.48    1.38     1.36     1.02     28.3    33     47    81      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.46    1.38     1.38     1.01     30.2    31     51    78      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.49    1.35     1.34     0.98     29.4    24     46    63      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.48    1.38     1.37     1.05     27.2    42     50    98      9
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.43    1.41     1.38     1.05     29.2    27     44    68      9
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.49    1.38     1.36     1.13     22.1    29     53    72      9
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.49    1.36     1.34     1.00     28.6    39     52    99      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep20):** **Risk model v3 gives +€0.9–1.4k (t up to 5.6).** Best margin: late_cost 1.5, risk_max 0.15 → €12.18k but 92.1%, min 86.7%, only 5/8 ranked. Safest good one: late_cost 1.0, risk_max 0.10 → €11.68k, 93.6%, min 88.3%, 7/8. → `risk.json` is now v3 (v2 kept as risk_v2_backup.json). Refine around risk_max 0.10–0.12 with a higher late_cost.

## Sat 08:47 — tag `sweep21` — level 8, 8 seeds (bench-0..)
**Why:** Refine risk v3 around the safe point (risk_max .10) with higher late_cost (1.5 gave +EUR300 at .15), stronger safety2, stronger peak smoothing, faster world learning.

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.0,risk_max=0.10`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.10`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=2.0,risk_max=0.10`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.12`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.10,s2_target=0.96,s2_k=25`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.10,peak_k=1.0`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.08`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,late_cost=1.5,risk_max=0.10,eta_w=0.045`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,677   €1,908   93.6%  88.3%   7/8     390           —       
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,952   €2,029   93.5%  87.4%   7/8     384        €275    1.3
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,905   €1,781   94.0%  87.8%   7/8     373        €228    1.3
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,635   €1,797   92.4%  87.6%   6/8     386        €-42   -0.2
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,716   €1,822   94.4%  89.2%   7/8     372         €39    0.3
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,856   €1,884   93.3%  88.2%   7/8     383        €179    1.1
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,390   €1,982   94.1%  87.7%   7/8     365       €-288   -1.6
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   8     €11,537   €1,587   93.1%  88.0%   6/8     378       €-140   -0.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.49    1.35     1.34     0.98     29.4    24     46    63      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.48    1.37     1.36     0.98     30.6    24     43    64      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.46    1.38     1.36     0.98     31.5    22     44    60      7
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.47    1.38     1.36     1.00     29.7    29     50    76      9
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.47    1.37     1.36     0.98     31.0    20     44    58      7
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.48    1.37     1.35     0.98     30.4    25     46    63      8
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.48    1.36     1.34     0.97     30.6    21     42    56      7
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.47    1.37     1.35     0.98     30.1    26     50    67      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep21):** All refinements are within noise (€11.4–12.0k). late_cost 1.5 +€275 (t 1.3); s2 0.96/k25 → safest (94.4%, min 89.2%). **Plateau ≈ €11.9k on bench seeds.** → validate on 14 fresh seeds to pick the final candidate.

## Sat 08:55 — tag `validate2` — level 8, 14 seeds (val-0..)
**Why:** Final-candidate validation on 14 fresh seeds (val-0..13): safe base (late_cost 1.0) vs safest-good (late_cost 1.5 + safety2 0.96/k25).

**Variants:** `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,risk_max=0.10,late_cost=1.0`; `econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.95,s2_k=15,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,risk_max=0.10,late_cost=1.5,s2_target=0.96,s2_k=25`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1  14     €13,897   €4,313   93.4%  89.6%  13/14    408           —       
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1  14     €13,852   €4,072   94.1%  91.0%  14/14    388        €-45   -0.2

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.51    1.41     1.40     0.98     33.1    26     50    67      9
econ:defer=1,notes2=1,charge_fix=1,fee_hat=1   0.49    1.42     1.41     0.97     34.7    22     44    59      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (validate2, 14 fresh seeds val-0..13):** base €13.9k / 93.4% / min 89.6% / 13/14 ranked; **safer variant (late_cost 1.5 + safety2 0.96/k25): €13.85k / 94.1% / min 91.0% / 14/14 ranked**, same margin. The bench seeds bench-0..7 are harder than average. → **The safer variant becomes the CANDIDATE and the 09:00 ranking config.**

## Sat 09:11 — RANKING RUNS — `CANDIDATE`
**Why:** Ranking round Sat 09:00 with CANDIDATE (econ + risk v3 + JIT + notes + charging fix + capped escalation + hard-order fee + trust + safety2 0.96 + peak smoothing): validate2 EUR13.85k, 94.1%, 14/14 ranked on fresh seeds. Board1 (smart, 00:00 round): EUR8.2k/wk, rank 45 of 56.

- run 1: €8,941, on-time 91.6%, won 323
- run 2: €10,897, on-time 95.9%, won 362
- run 3: €10,668, on-time 95.5%, won 357
- run 4: €15,042, on-time 91.0%, won 431
- run 5: €11,195, on-time 93.4%, won 347
- **5 ranking runs: total €56,744 (€11,349/week), min on-time 91.0%**

**Result (board2, Sat 09:00 round, CANDIDATE):** €8,941 / €10,897 / €10,668 / €15,042 / €11,195 → **€56,744 total (€11.35k/wk), min on-time 91.0%, 5/5 ranked.** Leaderboard at 09:15 (24 teams done): **we're rank 18 of 23 and BEAT House best (€10.1k/wk in this round) by €1.2k/wk.** #1 source-exp €14.8k/wk; the top-10 cutoff is ≈ €13.7k/wk. The gap to the top 10 is ≈ +€2.4k/wk (+21%); to #1, +€3.4k/wk. This round looks harder than Sat 00:00 (House best 14.4k → 10.1k). Vs board1: €8.2k → €11.35k/wk (+38%), with House best down 30%, so we're relatively much stronger.

## Sat 09:15 — tag `sweep22` — level 8, 8 seeds (s22-0..)
**Why:** On top of CANDIDATE (EUR13.85k on fresh seeds): re-test ideas that were neutral/positive under older policies - pairing (+326 earlier), price-war mode, more volume (risk_max .13), protect v2, faster world learning, faster dealer learning. New seeds s22-0..7.

**Variants:** `CANDIDATE`; `CANDIDATE:pair=1,batch_min=60,pair_gap=75`; `CANDIDATE:war=1`; `CANDIDATE:risk_max=0.13`; `CANDIDATE:protect=1`; `CANDIDATE:eta_w=0.045`; `CANDIDATE:pair=1,batch_min=60,pair_gap=75,war=1,protect=1`; `CANDIDATE:trust=1,eta_d=0.03`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE                                      8     €13,345   €2,935   94.9%  93.0%   8/8     380           —       
CANDIDATE:pair=1,batch_min=60,pair_gap=75      8     €14,029   €3,338   93.2%  87.6%   7/8     375        €684    2.4
CANDIDATE:war=1                                8     €13,109   €3,050   94.9%  93.5%   8/8     395       €-236   -1.3
CANDIDATE:risk_max=0.13                        8     €13,691   €2,874   94.5%  92.5%   8/8     391        €346    2.5
CANDIDATE:protect=1                            8     €13,397   €2,943   95.1%  93.6%   8/8     378         €52    0.4
CANDIDATE:eta_w=0.045                          8     €13,366   €3,366   94.8%  92.7%   8/8     377         €21    0.1
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   8     €14,228   €3,322   93.6%  88.6%   7/8     393        €883    2.9
CANDIDATE:trust=1,eta_d=0.03                   8     €13,616   €2,929   95.4%  94.0%   8/8     384        €271    1.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE                                      0.46    1.38     1.38     0.97     34.3    19     40    53      8
CANDIDATE:pair=1,batch_min=60,pair_gap=75      0.46    1.38     1.38     1.00     36.5    25     30    58      9
CANDIDATE:war=1                                0.49    1.37     1.35     0.97     32.5    20     44    56      8
CANDIDATE:risk_max=0.13                        0.45    1.40     1.39     0.99     34.3    21     44    58     10
CANDIDATE:protect=1                            0.46    1.38     1.38     0.97     34.7    18     40    53      9
CANDIDATE:eta_w=0.045                          0.46    1.39     1.37     0.97     34.5    19     40    52      8
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   0.48    1.37     1.35     1.00     35.5    24     31    57      9
CANDIDATE:trust=1,eta_d=0.03                   0.47    1.39     1.38     0.97     34.7    17     42    48      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep22, seeds s22-*):** CANDIDATE €13.3k / 94.9% / 8/8. Pairing **+€684 (t=2.4)**; pair+war+protect **+€883 (t=2.9) → €14.2k** but min OT 87.6–88.6% (7/8). risk_max 0.13 **+€346 (t=2.5)**, 8/8. eta_d 0.03 +€271 (min 94.0%). war, protect and eta_w alone are neutral. **Ops finding:** the laptop slept ~2.5 h (09:15 → 11:52). For the test final and the final, run under `caffeinate -dis` or on a VM.

## Sat 11:56 — RANKING RUNS — `CANDIDATE`
**Why:** Side leaderboard level 7 (does not count for the final) with the L8 CANDIDATE

- run 1: €8,412, on-time 94.6%, won 313
- run 2: €12,949, on-time 97.1%, won 376
- run 3: €12,172, on-time 91.6%, won 407
- run 4: €10,302, on-time 96.1%, won 356
- run 5: €8,445, on-time 95.5%, won 310
- **5 ranking runs: total €52,280 (€10,456/week), min on-time 91.6%**

## Sat 12:02 — RANKING RUNS — `CANDIDATE`
**Why:** Side leaderboard level 6 (does not count for the final) with the L8 CANDIDATE

- run 1: €4,869, on-time 97.0%, won 198
- run 2: €3,416, on-time 93.9%, won 197
- run 3: €6,905, on-time 96.1%, won 306
- run 4: €3,763, on-time 95.3%, won 213
- run 5: €2,844, on-time 94.4%, won 179
- **5 ranking runs: total €21,797 (€4,359/week), min on-time 93.9%**

## Sat 12:06 — tag `sweep23` — level 8, 8 seeds (s23-0..)
**Why:** Combine sweep22 winners (risk_max .13, eta_d .03, pairing, war, protect) with stronger safety (s2_target .97) to keep min OT; test Avellaneda-Stoikov inventory skew (cost += inv_k*typical*unstaffed_nearby/capacity). Fresh seeds s23-*.

**Variants:** `CANDIDATE`; `CANDIDATE:risk_max=0.13,eta_d=0.03`; `CANDIDATE:pair=1,batch_min=60,pair_gap=75,war=1,protect=1`; `CANDIDATE:pair=1,batch_min=60,pair_gap=75,war=1,protect=1,s2_target=0.97`; `CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,batch_min=60,pair_gap=75`; `CANDIDATE:inv_k=0.1`; `CANDIDATE:inv_k=0.3`; `CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,batch_min=60,pair_gap=75,war=1,protect=1,s2_target=0.97`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE                                      8     €10,920   €1,313   95.5%  92.9%   8/8     346           —       
CANDIDATE:risk_max=0.13,eta_d=0.03             8     €11,256   €1,226   94.4%  91.8%   8/8     356        €336    2.3
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   8     €10,801   €1,980   93.7%  90.8%   8/8     353       €-118   -0.4
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   8     €10,601   €2,059   93.7%  91.4%   8/8     346       €-319   -0.9
CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,ba   8     €11,483   €1,690   93.6%  89.5%   7/8     345        €564    1.5
CANDIDATE:inv_k=0.1                            8     €10,762   €1,306   95.4%  92.0%   8/8     336       €-157   -0.6
CANDIDATE:inv_k=0.3                            8     €10,416   €1,467   95.5%  90.6%   8/8     320       €-503   -1.5
CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,ba   8     €11,002   €1,755   93.1%  90.5%   8/8     353         €83    0.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE                                      0.46    1.38     1.35     0.97     31.4    15     32    42      8
CANDIDATE:risk_max=0.13,eta_d=0.03             0.44    1.39     1.36     0.99     31.5    20     36    52      7
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   0.47    1.35     1.30     1.01     30.1    22     20    54     10
CANDIDATE:pair=1,batch_min=60,pair_gap=75,wa   0.47    1.34     1.30     1.01     30.2    21     20    51     10
CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,ba   0.43    1.38     1.36     1.02     33.0    21     24    51      9
CANDIDATE:inv_k=0.1                            0.44    1.38     1.36     0.97     31.8    15     34    43      7
CANDIDATE:inv_k=0.3                            0.42    1.41     1.36     0.97     32.2    14     30    38      7
CANDIDATE:risk_max=0.13,eta_d=0.03,pair=1,ba   0.45    1.37     1.32     1.02     30.8    24     25    57      9

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep23, seeds s23-*):** risk_max 0.13 + eta_d 0.03 **+€336 (t=2.3), 8/8** → consistent with sweep22 (+€346 / +€271) → **adopted into CANDIDATE2**. Pairing is inconsistent across seed sets (+684 vs −118) → dropped. A-S inventory skew (inv_k 0.1/0.3): −€157/−€503 → dropped (the risk model already captures load).
**Side boards (don't count for the final):** L7 €10.5k/wk (that board's top 10 ≈ €10.9k), L6 €4.4k/wk (House best €8.2k: our L8 price prior is wrong for low levels), L5 running.

## Sat 12:09 — RANKING RUNS — `CANDIDATE`
**Why:** Side leaderboard level 5 (does not count for the final) with the L8 CANDIDATE

- run 1: €4,417, on-time 97.0%, won 266
- run 2: €2,126, on-time 97.3%, won 148
- run 3: €8,105, on-time 97.2%, won 319
- run 4: €5,787, on-time 98.3%, won 300
- run 5: €3,261, on-time 96.7%, won 209
- **5 ranking runs: total €23,696 (€4,739/week), min on-time 96.7%**

## Sat 12:16 — RANKING RUNS — `CANDIDATE`
**Why:** Side leaderboard level 4 (does not count for the final) with the L8 CANDIDATE

- run 1: €2,900, on-time 95.9%, won 123
- run 2: €8,188, on-time 98.4%, won 305
- run 3: €3,388, on-time 96.2%, won 184
- run 4: €4,098, on-time 94.3%, won 228
- run 5: €4,874, on-time 95.5%, won 247
- **5 ranking runs: total €23,448 (€4,690/week), min on-time 94.3%**

## Sat 12:22 — tag `sweep24` — level 8, 8 seeds (s24-0..)
**Why:** Competitor exploitation from data analysis (COMPETITOR_ANALYSIS.md): war v2 (shift -0.06, freeze learning), Stackelberg shadow cost per win (EUR6-10 x mornings left, big dealers), beta 10.5 (we overprice ~4%), fast daily level, per-dealer EKF, lane-specific realised cost.

**Variants:** `CANDIDATE2`; `CANDIDATE2:war=1,war_shift=-0.06`; `CANDIDATE2:adapt_k=6`; `CANDIDATE2:adapt_k=10`; `CANDIDATE2:beta_override=10.5`; `CANDIDATE2:day_level=1`; `CANDIDATE2:ekf=1`; `CANDIDATE2:lane_cost=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     8     €13,247   €1,830   94.8%  90.2%   8/8     393           —       
CANDIDATE2:war=1,war_shift=-0.06               8     €13,143   €1,897   95.0%  91.7%   8/8     393       €-104   -0.6
CANDIDATE2:adapt_k=6                           8     €10,006   €3,120   95.3%  90.7%   8/8     228     €-3,241   -4.1
CANDIDATE2:adapt_k=10                          8      €7,922   €3,498   96.4%  93.2%   8/8     161     €-5,325   -5.3
CANDIDATE2:beta_override=10.5                  8     €12,801   €1,664   93.6%  90.3%   8/8     422       €-446   -1.7
CANDIDATE2:day_level=1                         8     €13,142   €1,519   94.7%  91.2%   8/8     392       €-105   -0.5
CANDIDATE2:ekf=1                               8     €12,933   €1,255   94.9%  92.6%   8/8     386       €-314   -1.2
CANDIDATE2:lane_cost=1                         8     €13,577   €1,551   95.2%  92.9%   8/8     403        €330    1.8

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.46    1.39     1.38     0.98     33.3    20     47    52     10
CANDIDATE2:war=1,war_shift=-0.06               0.46    1.38     1.37     0.98     33.0    18     48    50     10
CANDIDATE2:adapt_k=6                           0.26    1.55     1.43     0.96     43.6    10     24    26      5
CANDIDATE2:adapt_k=10                          0.19    1.67     1.44     0.96     48.0     5     14    15      4
CANDIDATE2:beta_override=10.5                  0.50    1.34     1.34     0.98     30.0    26     58    64     11
CANDIDATE2:day_level=1                         0.45    1.39     1.37     0.98     33.1    20     45    56     11
CANDIDATE2:ekf=1                               0.45    1.38     1.36     0.98     33.2    19     47    51      9
CANDIDATE2:lane_cost=1                         0.47    1.38     1.37     0.98     33.3    19     48    48     10

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep24, s24-*):** CANDIDATE2 €13.25k / 94.8% / 8/8. **The Stackelberg shadow cost adapt_k 6/10 is a disaster (−€3.2k/−€5.3k)**: the "big dealer" gate covered too many dealers, pricing us out (q/list 1.55–1.67). war v2 (−0.06), β 10.5, day_level and EKF are neutral to slightly negative. **lane_cost +€330 (t=1.8), safer (min 92.9%).** The data analyst's offline € estimates again didn't transfer: in-world tests are the only ground truth.
**Side boards:** L5 €4.7k/wk, L4 €4.7k/wk (the low-level price prior needs adapting; low priority).

## Sat 12:36 — tag `sweep25` — level 8, 8 seeds (s25-0..)
**Why:** Confirm lane_cost on new seeds; Stackelberg cost only for D01-size dealers (>=40 req/day) and small (EUR2/morning); pulsing rotation (farm competitor learning); 0.85 opening fee on deep metro gigs (cov>=40, P(late)<.08); faster lane cost (n0=4); war v2 and slower day level on top of lane_cost.

**Variants:** `CANDIDATE2`; `CANDIDATE2:lane_cost=1`; `CANDIDATE2:lane_cost=1,adapt_k=2,adapt_big=40,adapt_small_w=0`; `CANDIDATE2:lane_cost=1,pulse=1`; `CANDIDATE2:lane_cost=1,easy_f=0.85,easy_cov=40,easy_pl=0.08`; `CANDIDATE2:lane_cost=1,lane_n0=4`; `CANDIDATE2:lane_cost=1,war=1,war_shift=-0.06`; `CANDIDATE2:lane_cost=1,day_level=1,eta_day=0.03`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     8     €11,981   €1,752   94.5%  92.7%   8/8     376           —       
CANDIDATE2:lane_cost=1                         8     €12,092   €2,002   94.5%  91.8%   8/8     386        €110    0.7
CANDIDATE2:lane_cost=1,adapt_k=2,adapt_big=4   8     €11,985   €1,985   94.2%  93.2%   8/8     369          €3    0.0
CANDIDATE2:lane_cost=1,pulse=1                 8     €12,169   €2,173   92.5%  87.6%   7/8     367        €188    0.7
CANDIDATE2:lane_cost=1,easy_f=0.85,easy_cov=   8     €12,079   €2,020   93.4%  90.7%   8/8     383         €98    0.6
CANDIDATE2:lane_cost=1,lane_n0=4               8     €11,760   €2,041   93.8%  91.6%   8/8     384       €-221   -1.3
CANDIDATE2:lane_cost=1,war=1,war_shift=-0.06   8     €11,886   €1,961   94.1%  92.9%   8/8     386        €-95   -0.7
CANDIDATE2:lane_cost=1,day_level=1,eta_day=0   8     €11,963   €1,629   93.8%  93.0%   8/8     385        €-18   -0.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.45    1.41     1.39     0.97     31.6    20     41    54      9
CANDIDATE2:lane_cost=1                         0.47    1.40     1.38     0.97     31.0    20     45    55     10
CANDIDATE2:lane_cost=1,adapt_k=2,adapt_big=4   0.44    1.43     1.40     0.98     32.1    20     38    54     10
CANDIDATE2:lane_cost=1,pulse=1                 0.42    1.48     1.44     0.97     32.8    27     34    68      9
CANDIDATE2:lane_cost=1,easy_f=0.85,easy_cov=   0.46    1.40     1.37     0.96     31.2    24     38    70      9
CANDIDATE2:lane_cost=1,lane_n0=4               0.47    1.40     1.38     0.97     30.2    23     43    62     10
CANDIDATE2:lane_cost=1,war=1,war_shift=-0.06   0.47    1.39     1.38     0.98     30.5    22     42    59      9
CANDIDATE2:lane_cost=1,day_level=1,eta_day=0   0.46    1.40     1.38     0.98     30.8    23     46    61      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 12:37 — tag `batch_on` — level 8, 3 seeds (s24-0..)
**Why:** (not given)

**Variants:** `CANDIDATE2`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     3     €12,301   €1,062   94.3%  92.9%   3/3     374           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.43    1.38     1.38     0.98     32.6    20     44    52      8

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep25, s25-*):** Everything is within noise: lane_cost +€110 (not confirmed), the D01-only Stackelberg cost €0, pulsing +€188 but min OT 87.6%, 0.85 metro opening +€98, war v2 −€95, day_level −€18. **The candidate stays CANDIDATE2** (alias `CANDIDATE` now points to it; the old one is `CANDIDATE1`).
**Speed (organiser hint "a fast system plays a week with ~350 requests"):** request batching in the runner (after a new request, jump 12 min in one call; quotes still land inside their 15-min windows). **1,144 → ~490 requests/week, 100 s → 33 s/week (3× throughput), same results** (s24-0: €13,202 vs €13,200).

## Sat 12:37 — tag `batch_off` — level 8, 3 seeds (s24-0..)
**Why:** (not given)

**Variants:** `CANDIDATE2`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     3     €12,355   €1,606   93.7%  90.2%   3/3     379           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.44    1.38     1.38     0.98     32.2    22     42    56     10

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 12:43 — tag `sweep26` — level 8, 8 seeds (s26-0..)
**Why:** Maximise orders: leaders win 409-458 orders/wk; our policy is now much better at staffing, so re-test the volume frontier: looser risk gate, lower late cost, lower assumed fee, cheaper hard-order fee, and a max-volume combo.

**Variants:** `CANDIDATE2`; `CANDIDATE2:risk_max=0.16`; `CANDIDATE2:risk_max=0.20`; `CANDIDATE2:risk_max=0.16,late_cost=1.0`; `CANDIDATE2:fee_hat=0.95`; `CANDIDATE2:fee_hat=0.9,risk_max=0.16`; `CANDIDATE2:hard_k=2`; `CANDIDATE2:risk_max=0.2,late_cost=0.8,fee_hat=0.95`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     8     €13,997   €3,993   94.0%  92.6%   8/8     403           —       
CANDIDATE2:risk_max=0.16                       8     €13,862   €3,554   93.1%  91.3%   8/8     409       €-135   -0.5
CANDIDATE2:risk_max=0.20                       8     €13,949   €3,971   92.6%  90.1%   8/8     410        €-48   -0.2
CANDIDATE2:risk_max=0.16,late_cost=1.0         8     €13,960   €3,632   92.8%  91.0%   8/8     426        €-37   -0.1
CANDIDATE2:fee_hat=0.95                        8     €14,075   €3,927   93.5%  91.9%   8/8     422         €79    0.4
CANDIDATE2:fee_hat=0.9,risk_max=0.16           8     €13,792   €3,531   92.5%  90.7%   8/8     449       €-205   -0.8
CANDIDATE2:hard_k=2                            8     €14,407   €4,026   93.4%  90.8%   8/8     402        €410    1.9
CANDIDATE2:risk_max=0.2,late_cost=0.8,fee_ha   8     €13,548   €3,674   91.5%  89.3%   7/8     462       €-449   -1.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.49    1.44     1.42     0.99     33.8    23     54    62     10
CANDIDATE2:risk_max=0.16                       0.48    1.44     1.42     1.00     33.1    28     57    73     12
CANDIDATE2:risk_max=0.20                       0.46    1.46     1.43     1.01     33.1    29     54    74     11
CANDIDATE2:risk_max=0.16,late_cost=1.0         0.50    1.43     1.42     1.01     32.0    30     62    81     10
CANDIDATE2:fee_hat=0.95                        0.52    1.41     1.40     0.99     32.5    26     58    65     11
CANDIDATE2:fee_hat=0.9,risk_max=0.16           0.53    1.41     1.39     1.01     30.0    33     61    84     12
CANDIDATE2:hard_k=2                            0.48    1.44     1.42     0.97     34.9    25     48    69     10
CANDIDATE2:risk_max=0.2,late_cost=0.8,fee_ha   0.53    1.41     1.40     1.04     28.6    38     66    93      9

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep26, maximise orders, s26-*):** **The volume frontier is flat**: 403 → 462 orders gives the same or lower margin (max-volume combo −€449, 89.3% min OT). Extra orders are worth ≈ €0 after staffing. → Maximising orders is NOT the path; €/order is. hard_k 2 +€410 (t=1.9) → candidate tweak. (Sweep ran in 365 s thanks to batching.)
**MECHANICS.md** (statistical hunt): the dealer decision is a hard threshold per request; exact list = (20+0.25 km)·{1.075, 1, 0.93}; noise floor σ ≈ 0.16 log (β ≈ 11); bulk order at a low-driver yard → 52% late; Friday same_day 20.8% late; snow forecast 24 h ahead (drive ×1.23); posting clock matters. → sweep27 tests the bulk cap, same_day premium, Friday same_day, snow.

## Sat 12:49 — tag `sweep27` — level 8, 8 seeds (s27-0..)
**Why:** Mechanics from the statistical hunt: bulk-order cap (min(12, 0.1*yard drivers)), same_day premium 8%, Friday same_day +15%, snow handling (drive x1.25, +5% quote), plus hard_k 2 from sweep26.

**Variants:** `CANDIDATE2`; `CANDIDATE2:hard_k=2`; `CANDIDATE2:bulk=1`; `CANDIDATE2:sd_prem=0.08`; `CANDIDATE2:fri_sd=0.15`; `CANDIDATE2:snow=1`; `CANDIDATE2:hard_k=2,bulk=1,sd_prem=0.08,fri_sd=0.15,snow=1`; `CANDIDATE2:hard_k=2,bulk=1,fri_sd=0.15,snow=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     8     €13,005   €3,111   94.3%  92.4%   8/8     376           —       
CANDIDATE2:hard_k=2                            8     €13,010   €3,090   93.8%  92.1%   8/8     370          €5    0.0
CANDIDATE2:bulk=1                              8     €12,479   €3,336   94.3%  92.8%   8/8     362       €-526   -4.0
CANDIDATE2:sd_prem=0.08                        8     €12,558   €3,017   94.7%  93.3%   8/8     346       €-447   -1.4
CANDIDATE2:fri_sd=0.15                         8     €13,021   €3,178   94.8%  93.1%   8/8     374         €16    0.4
CANDIDATE2:snow=1                              8     €12,857   €3,319   94.1%  92.7%   8/8     371       €-148   -1.4
CANDIDATE2:hard_k=2,bulk=1,sd_prem=0.08,fri_   8     €12,485   €3,414   95.1%  93.3%   8/8     331       €-520   -2.1
CANDIDATE2:hard_k=2,bulk=1,fri_sd=0.15,snow=   8     €12,637   €3,699   94.2%  92.3%   8/8     351       €-368   -1.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.45    1.40     1.39     0.98     33.9    21     44    55      8
CANDIDATE2:hard_k=2                            0.44    1.40     1.38     0.96     34.4    22     40    61      8
CANDIDATE2:bulk=1                              0.45    1.41     1.38     0.98     33.7    20     40    54      7
CANDIDATE2:sd_prem=0.08                        0.41    1.40     1.40     0.97     35.6    17     36    51      8
CANDIDATE2:fri_sd=0.15                         0.45    1.40     1.39     0.98     34.1    19     43    51      9
CANDIDATE2:snow=1                              0.44    1.40     1.38     0.98     33.8    22     43    58      8
CANDIDATE2:hard_k=2,bulk=1,sd_prem=0.08,fri_   0.40    1.41     1.40     0.96     37.0    15     37    48      7
CANDIDATE2:hard_k=2,bulk=1,fri_sd=0.15,snow=   0.44    1.41     1.38     0.96     35.0    20     37    52      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep27, s27-*):** All mechanics fixes are neutral or negative: bulk cap −€526 (t=−4; the risk model already avoids the dangerous bulk wins, and a blunt cap drops profitable ones), same_day premium −€447, snow −€148, fri_sd +€16 (+0.5 pt on-time), hard_k 2 ±0. **CANDIDATE2 is a robust local optimum**: ~15 tweaks over 4 sweeps are all within noise.

## Sat 12:53 — RANKING RUNS — `CANDIDATE2`
**Why:** Sat 12:00 round with CANDIDATE2 (econ + risk v3 + risk_max .13 + eta_d .03 ...): bench EUR12-14k on fresh seeds, all 8/8 ranked. Board2 (09:00 round, CANDIDATE): EUR11.35k/wk, beat House best.

- run 1: €17,672, on-time 95.7%, won 464
- run 2: €17,137, on-time 95.1%, won 427
- run 3: €12,570, on-time 97.1%, won 411
- run 4: €16,304, on-time 96.4%, won 450
- run 5: €14,591, on-time 89.5%, won 400
- **5 ranking runs: total €78,273 (€15,655/week), min on-time 89.5%**

**Result (board3, Sat 12:00 round, CANDIDATE2):** €17,672 / €17,137 / €12,570 / €16,304 / €14,591 → **€78,273 (€15.65k/wk), but run 5 at 89.5% on time → NOT RANKED.** This round is easier: the leaders make €19.8k/wk at 97–98% OT; top 10 ≈ €17.7k. **Two gaps: (1) safety: we average ~95% with occasional <90% weeks, the leaders hold 97–98%; (2) margin −21% vs #1.** The final is one week, so a ~10% chance of an unranked week is unacceptable → **top priority: lift the on-time floor to ~97% without losing margin.**
**Late diagnosis (CANDIDATE-like, 3,054 orders, 6.2% late):** warned orders are 47% late (160 of 189 lates). **Trade-ins 33% late** (60 orders). Slack 2–5 h: 16% late. Friday 9%. → sweep28: decline trade-ins, a min slack gate, a stronger rescue for warned orders only, earlier late step.

## Sat 12:59 — tag `sweep28` — level 8, 10 seeds (s28-0..)
**Why:** SAFETY: board3 had a 89.5% week (unranked); leaders hold 97-98%. Target the on-time floor without losing margin: decline trade-ins (33% late), min slack gate (2-5h slack = 16% late), stronger rescue for warned orders only (47% late), earlier late step, Friday same_day premium.

**Variants:** `CANDIDATE2`; `CANDIDATE2:tradein_decl=1`; `CANDIDATE2:min_slack=300`; `CANDIDATE2:urgent_open=1.4,urgent_max=1.8`; `CANDIDATE2:late_h=6`; `CANDIDATE2:tradein_decl=1,min_slack=300,urgent_open=1.4,urgent_max=1.8`; `CANDIDATE2:tradein_decl=1,min_slack=300,urgent_open=1.4,urgent_max=1.8,fri_sd=0.15`; `CANDIDATE2:tradein_decl=1,min_slack=240,urgent_open=1.3,urgent_max=1.6,late_h=6`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE2                                     9     €11,866   €3,441   92.3%  88.2%   7/9     371           —       
CANDIDATE2:tradein_decl=1                      9     €11,897   €3,485   92.5%  88.2%   7/9     372         €31    0.6
CANDIDATE2:min_slack=300                       9     €11,953   €3,627   92.7%  88.7%   7/9     369         €87    0.6
CANDIDATE2:urgent_open=1.4,urgent_max=1.8      9     €11,712   €3,484   92.9%  89.6%   8/9     381       €-155   -0.7
CANDIDATE2:late_h=6                            9     €12,346   €3,940   93.4%  90.6%   9/9     380        €480    2.2
CANDIDATE2:tradein_decl=1,min_slack=300,urge   9     €11,463   €3,246   93.3%  88.5%   8/9     374       €-403   -1.4
CANDIDATE2:tradein_decl=1,min_slack=300,urge   9     €11,494   €3,266   93.4%  88.5%   7/9     373       €-373   -1.3
CANDIDATE2:tradein_decl=1,min_slack=240,urge   9     €12,379   €3,684   94.2%  90.6%   9/9     385        €512    1.7

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE2                                     0.44    1.41     1.39     0.98     31.4    29     50    78      6
CANDIDATE2:tradein_decl=1                      0.44    1.41     1.39     0.98     31.3    28     49    77      8
CANDIDATE2:min_slack=300                       0.44    1.41     1.39     0.98     31.9    28     47    71      7
CANDIDATE2:urgent_open=1.4,urgent_max=1.8      0.45    1.41     1.40     1.02     30.1    27     50    75      6
CANDIDATE2:late_h=6                            0.45    1.41     1.39     0.99     31.8    25     49    63      7
CANDIDATE2:tradein_decl=1,min_slack=300,urge   0.44    1.40     1.39     1.01     30.3    26     48    74      7
CANDIDATE2:tradein_decl=1,min_slack=300,urge   0.44    1.40     1.39     1.01     30.5    25     47    71      7
CANDIDATE2:tradein_decl=1,min_slack=240,urge   0.45    1.41     1.40     1.00     31.6    23     51    59      7

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep28, s28-*, 72 of 80 weeks; 8 lost to a server restart):** late_h 6 **+€480 (t=2.2), 9/9, min 90.6%**. Combo (trade-in decline + min_slack 240 + urgent 1.3→1.6 + late_h 6) **+€512, 94.2%, 9/9** → **CANDIDATE3** (alias `CANDIDATE`, used by the test-final bot). Alone, trade-in decline, min_slack and the stronger rescue are neutral. Still ~94% vs the leaders' 97% → push earlier, time-based escalation.

## Sat 13:07 — tag `sweep29` — level 8, 10 seeds (s29-0..)
**Why:** On-time floor: warned orders (no driver 3h before last pickup) cause ~85% of lates. Escalate earlier: late step 8/10h before lastPickupAt, time-based steps after 60-90 min unbooked, stronger projected-OT controller, tighter risk gate.

**Variants:** `CANDIDATE3`; `CANDIDATE3:late_h=8`; `CANDIDATE3:late_h=10`; `CANDIDATE3:step1_min=90,step1_f=1.15`; `CANDIDATE3:step1_min=60,step1_f=1.1,step2_min=180,step2_f=1.3`; `CANDIDATE3:s2_target=0.97,s2_k=40`; `CANDIDATE3:risk_max=0.11`; `CANDIDATE3:late_h=8,step1_min=90,step1_f=1.15,s2_target=0.97,s2_k=40`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE3                                    10     €11,447   €2,685   95.3%  90.6%  10/10    371           —       
CANDIDATE3:late_h=8                           10     €11,420   €3,007   95.4%  91.7%  10/10    374        €-28   -0.1
CANDIDATE3:late_h=10                          10     €11,402   €2,890   96.0%  91.8%  10/10    375        €-45   -0.3
CANDIDATE3:step1_min=90,step1_f=1.15          10     €10,450   €2,590   96.4%  94.3%  10/10    374       €-998   -6.3
CANDIDATE3:step1_min=60,step1_f=1.1,step2_mi  10     €10,069   €2,289   96.8%  94.2%  10/10    375     €-1,379   -5.8
CANDIDATE3:s2_target=0.97,s2_k=40             10     €11,371   €2,807   95.7%  91.6%  10/10    358        €-76   -0.3
CANDIDATE3:risk_max=0.11                      10     €11,356   €2,658   95.6%  91.7%  10/10    368        €-92   -1.0
CANDIDATE3:late_h=8,step1_min=90,step1_f=1.1  10     €10,200   €2,591   96.6%  95.3%  10/10    356     €-1,247   -6.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE3                                     0.43    1.35     1.34     1.00     30.2    18     45    47      8
CANDIDATE3:late_h=8                            0.44    1.36     1.34     1.01     29.9    17     44    42      9
CANDIDATE3:late_h=10                           0.44    1.36     1.34     1.01     29.6    15     44    41      9
CANDIDATE3:step1_min=90,step1_f=1.15           0.44    1.36     1.35     1.05     27.4    14     49    35     10
CANDIDATE3:step1_min=60,step1_f=1.1,step2_mi   0.44    1.36     1.35     1.08     26.4    12     50    31      9
CANDIDATE3:s2_target=0.97,s2_k=40              0.42    1.36     1.34     1.00     31.1    16     40    42      8
CANDIDATE3:risk_max=0.11                       0.44    1.35     1.34     0.99     30.2    16     43    45      8
CANDIDATE3:late_h=8,step1_min=90,step1_f=1.1   0.42    1.36     1.34     1.05     27.9    12     49    30      9

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep29, s29-*, 10 seeds):** CANDIDATE3 €11.45k / 95.3% / min 90.6% / 10/10. **late_h 10: 96.0%, min 91.8%, −€45 (free safety) → adopt.** Time-based escalation (60–90 min unbooked → 1.1–1.15×): **96.4–96.8%, min 94.2–95.3%, but −€1.0–1.4k** = the insurance frontier. s2 0.97 and risk_max 0.11: neutral. Next: a milder or later time step to find a cheaper insurance point.

## Sat 13:13 — tag `sweep30` — level 8, 10 seeds (s30-0..)
**Why:** Find cheap insurance: time-based steps that are milder (1.0-1.05) or later (180-240 min unbooked), or more opening fee on risky orders (hard_k 6), on top of late_h 10. Goal: min OT >= 93% at <= EUR300 cost.

**Variants:** `CANDIDATE3:late_h=10`; `CANDIDATE3:late_h=10,step1_min=120,step1_f=1.05`; `CANDIDATE3:late_h=10,step1_min=180,step1_f=1.1`; `CANDIDATE3:late_h=10,step1_min=90,step1_f=1.0`; `CANDIDATE3:late_h=10,step1_min=240,step1_f=1.15`; `CANDIDATE3:late_h=10,step1_min=120,step1_f=1.05,s2_target=0.97,s2_k=40`; `CANDIDATE3:late_h=10,hard_k=6`; `CANDIDATE3:late_h=10,hard_k=6,step1_min=180,step1_f=1.1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE3:late_h=10                          10     €13,241   €3,477   94.6%  90.2%  10/10    403           —       
CANDIDATE3:late_h=10,step1_min=120,step1_f=1  10     €12,554   €3,381   94.9%  91.4%  10/10    401       €-687   -3.3
CANDIDATE3:late_h=10,step1_min=180,step1_f=1  10     €12,512   €3,493   95.0%  92.3%  10/10    402       €-729   -5.9
CANDIDATE3:late_h=10,step1_min=90,step1_f=1.  10     €13,171   €3,427   95.2%  91.9%  10/10    403        €-70   -0.5
CANDIDATE3:late_h=10,step1_min=240,step1_f=1  10     €12,284   €3,383   94.9%  93.2%  10/10    402       €-957   -5.0
CANDIDATE3:late_h=10,step1_min=120,step1_f=1  10     €12,642   €3,523   94.8%  91.3%  10/10    395       €-599   -5.1
CANDIDATE3:late_h=10,hard_k=6                 10     €12,782   €3,275   94.9%  89.3%   9/10    403       €-458   -3.6
CANDIDATE3:late_h=10,hard_k=6,step1_min=180,  10     €12,347   €3,360   95.4%  91.3%  10/10    405       €-894   -6.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE3:late_h=10                           0.49    1.42     1.41     1.01     32.1    21     47    50     10
CANDIDATE3:late_h=10,step1_min=120,step1_f=1   0.48    1.41     1.40     1.03     30.7    20     50    50     10
CANDIDATE3:late_h=10,step1_min=180,step1_f=1   0.48    1.42     1.40     1.04     30.4    20     52    48     10
CANDIDATE3:late_h=10,step1_min=90,step1_f=1.   0.49    1.42     1.40     1.02     32.0    19     47    46     10
CANDIDATE3:late_h=10,step1_min=240,step1_f=1   0.48    1.42     1.40     1.05     29.8    20     52    48      9
CANDIDATE3:late_h=10,step1_min=120,step1_f=1   0.48    1.42     1.41     1.03     31.3    20     49    49     10
CANDIDATE3:late_h=10,hard_k=6                  0.48    1.42     1.40     1.03     31.1    20     46    48      9
CANDIDATE3:late_h=10,hard_k=6,step1_min=180,   0.49    1.42     1.41     1.05     29.9    18     53    44     10

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep30, s30-*, 10 seeds):** base (C3 + late_h 10) €13.24k / 94.6% / min 90.2%. **Cheap insurance: step to 1.0× after 90 min unbooked: −€70 (n.s.), +0.6 pt OT, min 91.9% → CANDIDATE4** (alias CANDIDATE; the test-final bot loads it). Every steeper or later step and hard_k 6 costs €450–950.

## Sat 13:18 — tag `sweep31` — level 8, 12 seeds (s31-0..)
**Why:** Note reader v3 (lab/notes.py): offline vs reveal truth catches 97% of delayed cars (old 39%), 1.1% false delays. All failed visits under CANDIDATE2 came from misread notes (~8/wk).

**Variants:** `CANDIDATE4`; `CANDIDATE4:notes3=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE4                                    12     €12,953   €3,421   94.8%  91.0%  12/12    399           —       
CANDIDATE4:notes3=1                           12     €13,252   €3,559   94.8%  91.9%  12/12    400        €298    2.8

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE4                                     0.48    1.43     1.41     1.02     31.7    20     55    51      9
CANDIDATE4:notes3=1                            0.48    1.43     1.41     1.03     32.4    20     56    48      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Note reader v3 (`lab/notes.py`):** all failed visits under the candidate came from misread notes (59 not_ready, 6 closed, 2 plates in 8 weeks). The new reader handles relative days, weekday names (2–6 days ahead), hours in words (FI/SV/EN working hours), "half three", corrections, "not before" phrasing, opening-hour ranges and delivery clauses. **Offline vs reveal truth (975 delayed cars, 9,686 not delayed): catches 97% of delays (old 39%), false delays 1.1% (old 0.9%).**
**Decision (sweep31, 12 seeds): +€298 (t=2.8), failed visits 9 → 3/week → CANDIDATE5** (alias CANDIDATE).

## Sat 13:20 — tag `sweep32` — level 8, 10 seeds (s32-0..)
**Why:** Posting clock: same_day gigs posted after 14:00 have median wait 20-24 min (59-73% booked within 60 min). Open those at 1.1/1.2 instead of 0.9.

**Variants:** `CANDIDATE5`; `CANDIDATE5:pm_sd_open=1.1`; `CANDIDATE5:pm_sd_open=1.2`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE5                                    10     €12,924   €2,734   96.5%  94.3%  10/10    387           —       
CANDIDATE5:pm_sd_open=1.1                     10     €12,624   €2,864   96.6%  94.8%  10/10    385       €-299   -1.7
CANDIDATE5:pm_sd_open=1.2                     10     €12,404   €2,712   96.6%  94.8%  10/10    385       €-520   -2.8

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE5                                     0.46    1.40     1.39     1.02     32.8    13     50    34      3
CANDIDATE5:pm_sd_open=1.1                      0.46    1.40     1.38     1.03     32.1    13     47    32      4
CANDIDATE5:pm_sd_open=1.2                      0.46    1.40     1.38     1.04     31.7    13     47    32      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 13:22 — tag `validate5` — level 8, 16 seeds (v5-0..)
**Why:** Robustness of CANDIDATE5 on 16 fresh seeds: distribution of weekly on-time (P(week<90%)).

**Variants:** `CANDIDATE5`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE5                                    16     €12,275   €2,625   96.1%  93.7%  16/16    377           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE5                                     0.46    1.41     1.40     1.02     31.9    14     48    38      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**sweep32:** afternoon same_day opening fee 1.1/1.2: −€299/−€520, no on-time gain → dropped.
**validate5 (CANDIDATE5, 16 fresh seeds v5-*):** €12.3k/wk, **96.1% on time, min 93.7%, 16/16 ranked** (weekly OT: 93.7, 94.5, 94.6, 94.9, 95.3, 95.8, 96.0, 96.4, 96.4, 96.6, 96.8, 97.0, 97.1, 97.2, 97.3, 98.3). **The safety goal (leader-level ~96–97%) is reached.** Next: margin.

**TEST FINAL 1 (Sat 14:00, live clock, starts Thursday with Mon–Wed played by nobody):** we won **12 orders, €143**; the leaders won ~160 orders (~€4k) at 97–99%. **Diagnosis from the reveal:** from Thu 10:00 our quotes were pinned at the grid max (2.15× list). **Bug:** peak smoothing's reference day = the average wins of the earlier days = 0 in a mid-week join → every win looked like a massive peak → huge cost. Fixed (only days with ≥20 quotes count; floor 40). A second bug fixed before the start: the rejoin replayed 536 never-quoted history requests as our losses (learning only now replays if we have orders or gigs). **New tool `lab.midweek_test`** reproduces test-final conditions in practice. With the fix, s24-0 mid-week: 85 won, €2.5k, 98.8%.

## Sat 14:24 — tag `sweep33` — level 8, 12 seeds (s33-0..)
**Why:** Peak smoothing limits volume after a mid-week join (103 vs 85 wins without it) and was neutral in sweep19; check on normal weeks whether dropping it costs anything (simpler + more robust).

**Variants:** `CANDIDATE5`; `CANDIDATE5:peak=0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE5                                    12     €12,933   €3,263   95.4%  91.5%  12/12    386           —       
CANDIDATE5:peak=0                             12     €13,228   €3,074   95.2%  91.3%  12/12    404        €295    1.6

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE5                                     0.47    1.42     1.40     1.02     32.9    17     43    42      2
CANDIDATE5:peak=0                              0.49    1.40     1.40     1.02     32.2    19     48    45      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (sweep33, 12 seeds):** dropping peak smoothing **+€295 (t=1.6)**, same safety (min 91.3%, 12/12), and robust to mid-week joins → **CANDIDATE6** (alias CANDIDATE).

## Sat 14:26 — tag `reveal6` — level 8, 8 seeds (r6-0..)
**Why:** Full-data runs of CANDIDATE6 to decompose fee costs and lateness under the current policy.

**Variants:** `CANDIDATE6`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE6                                     8     €14,464   €2,932   96.0%  94.6%   8/8     428           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE6                                     0.51    1.42     1.41     1.01     33.2    17     50    38      4

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**reveal6 (CANDIDATE6, 8 weeks, full data):** €14.5k/wk, 96.0%, min 94.6%, 428 won. Per week: revenue €41.7k, driver fees €26.5k, refunds €0.4k. **By option:** same_day €26.1/order (fee/typ 1.04, price/list 1.35), next_day **€41.5** (1.01, 1.46), within_3_days €38.7 (0.96, 1.52). By fee band: <0.95 → €39/order (40% of orders); 1.05–1.3 → €27.6 (29%); >1.3 → ~€0. → sweep34: option economics and hard-order fee level.

## Sat 14:38 — tag `sweep34` — level 8, 10 seeds (s34-0..)
**Why:** Per-order economics: same_day EUR26 vs next_day EUR41.5/order; 29% of orders opened above 1.05x earn only EUR27.6. Test option-specific costs (econ prices same_day higher -> steer to next_day), small same_day premium, hard-order fee level/threshold, lower late step.

**Variants:** `CANDIDATE6`; `CANDIDATE6:hard_k=2`; `CANDIDATE6:hard_k=6`; `CANDIDATE6:sd_prem=0.04`; `CANDIDATE6:opt_fee=1`; `CANDIDATE6:opt_fee=1,fee_sd=1.08,fee_nd=1.0,fee_w3=0.97`; `CANDIDATE6:hard_thr=0.08`; `CANDIDATE6:fee_late=1.0`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE6                                    10     €13,337   €3,223   95.8%  92.0%  10/10    414           —       
CANDIDATE6:hard_k=2                           10     €13,514   €3,298   95.6%  92.2%  10/10    409        €177    1.0
CANDIDATE6:hard_k=6                           10     €12,971   €3,132   96.2%  93.5%  10/10    416       €-366   -2.6
CANDIDATE6:sd_prem=0.04                       10     €13,287   €3,494   95.9%  93.1%  10/10    396        €-50   -0.3
CANDIDATE6:opt_fee=1                          10     €13,283   €3,199   96.2%  92.2%  10/10    384        €-54   -0.3
CANDIDATE6:opt_fee=1,fee_sd=1.08,fee_nd=1.0,  10     €13,315   €3,273   96.2%  92.4%  10/10    402        €-22   -0.1
CANDIDATE6:hard_thr=0.08                      10     €13,904   €3,635   95.9%  91.7%  10/10    411        €567    2.2
CANDIDATE6:fee_late=1.0                       10     €12,911   €3,422   95.2%  92.2%  10/10    400       €-426   -2.7

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE6                                     0.50    1.40     1.40     1.02     31.5    17     54    41      5
CANDIDATE6:hard_k=2                            0.49    1.40     1.40     1.00     32.3    17     53    42      4
CANDIDATE6:hard_k=6                            0.50    1.41     1.40     1.04     30.5    15     53    38      5
CANDIDATE6:sd_prem=0.04                        0.47    1.41     1.41     1.01     32.8    15     51    37      4
CANDIDATE6:opt_fee=1                           0.46    1.42     1.42     1.01     33.8    14     48    34      4
CANDIDATE6:opt_fee=1,fee_sd=1.08,fee_nd=1.0,   0.48    1.40     1.40     1.01     32.4    14     49    38      4
CANDIDATE6:hard_thr=0.08                       0.49    1.41     1.40     1.00     33.0    16     50    39      3
CANDIDATE6:fee_late=1.0                        0.48    1.40     1.39     1.01     31.5    18     51    52      5

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep34, s34-*, 10 seeds):** hard_thr 0.08 **+€567 (t=2.2)**, safety unchanged → **CANDIDATE7**. hard_k 2 +€177 (n.s.), hard_k 6 −€366, fee_late 1.0 −€426, opt_fee / sd_prem ≈ 0.
**Test-final analysis (user + our replay):** the winners won ~158 orders in Thu–Fri (~79/day ≈ normal-week leader pace). Ours (12) was the peak-reference bug; the fixed policy gives 85–103 in a Thursday-start practice replay. The real final starts Monday, so prioritise Monday-start performance.
**Plan (user's ranked bets):** (1) booking-hazard model h(fee, state) plus a drop model → small DP for the fee schedule (agent building it); (2) a portfolio SLA chance constraint with correlated shocks; (3) joint quote–fee cost from (1); (4) capacity-aware admission counting pending quotes / reusable driver-hours (Goyal–Iyengar–Udwani, Ma–Fang–Parkes).

## Sat 14:43 — tag `validate7` — level 8, 20 seeds (v7-0..)
**Why:** Confirm hard_thr .08 (+567, t 2.2 in sweep34) on 20 untouched paired weeks before making it the final candidate.

**Variants:** `CANDIDATE6`; `CANDIDATE7`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE6                                    20     €12,742   €2,087   96.4%  93.9%  20/20    408           —       
CANDIDATE7                                    20     €13,217   €2,169   96.3%  93.1%  20/20    408        €475    4.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE6                                     0.49    1.40     1.39     1.02     30.8    14     49    34      4
CANDIDATE7                                     0.49    1.40     1.39     1.00     32.0    15     47    36      4

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**validate7 (20 untouched paired weeks v7-*):** **CANDIDATE7 +€475 (t=4.4)** vs CANDIDATE6, €13.2k/wk, 96.3%, min 93.1%, 20/20 ranked. Confirmed.

## Sat 14:51 — tag `sweep35` — level 8, 12 seeds (s35-0..)
**Why:** Refine around CANDIDATE7: hard-order fee threshold/slope (hard_thr .08 was +475 t 4.4), more volume via risk_max .15, shorter lead time.

**Variants:** `CANDIDATE7`; `CANDIDATE7:hard_k=2`; `CANDIDATE7:hard_thr=0.10`; `CANDIDATE7:hard_thr=0.12`; `CANDIDATE7:risk_max=0.15`; `CANDIDATE7:hard_thr=0.10,risk_max=0.15`; `CANDIDATE7:lead_min=60`; `CANDIDATE7:hard_k=3,hard_thr=0.10`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                    12     €12,470   €3,182   94.2%  89.8%  11/12    394           —       
CANDIDATE7:hard_k=2                           12     €12,450   €3,343   94.0%  89.1%  11/12    396        €-20   -0.1
CANDIDATE7:hard_thr=0.10                      12     €12,564   €3,436   94.5%  89.7%  11/12    395         €93    0.4
CANDIDATE7:hard_thr=0.12                      12     €12,586   €3,498   94.4%  89.9%  11/12    394        €116    0.4
CANDIDATE7:risk_max=0.15                      12     €12,822   €3,375   94.4%  91.0%  12/12    400        €351    2.2
CANDIDATE7:hard_thr=0.10,risk_max=0.15        12     €12,694   €3,397   94.3%  89.8%  11/12    396        €224    1.5
CANDIDATE7:lead_min=60                        12     €12,470   €3,182   94.2%  89.8%  11/12    394           —       
CANDIDATE7:hard_k=3,hard_thr=0.10             12     €12,452   €3,433   94.4%  89.8%  11/12    392        €-18   -0.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.46    1.39     1.38     1.01     31.0    22     54    58      4
CANDIDATE7:hard_k=2                            0.46    1.39     1.38     1.01     30.7    23     53    60      4
CANDIDATE7:hard_thr=0.10                       0.46    1.39     1.38     1.01     31.0    21     54    57      3
CANDIDATE7:hard_thr=0.12                       0.46    1.39     1.38     1.01     31.1    21     52    57      3
CANDIDATE7:risk_max=0.15                       0.46    1.40     1.39     1.02     31.3    22     53    58      3
CANDIDATE7:hard_thr=0.10,risk_max=0.15         0.45    1.40     1.39     1.01     31.3    22     53    57      2
CANDIDATE7:lead_min=60                         0.46    1.39     1.38     1.01     31.0    22     54    58      4
CANDIDATE7:hard_k=3,hard_thr=0.10              0.46    1.39     1.38     1.01     31.0    21     51    55      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

## Sat 14:52 — tag `diag35` — level 8, 2 seeds (s35-6..)
**Why:** (not given)

**Variants:** `CANDIDATE7`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                     2     €11,200   €1,314   91.5%  89.8%   1/2     392           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.44    1.36     1.35     1.03     28.4    32     59    86      6

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep35, s35-*, 12 seeds):** CANDIDATE7 €12.5k / 94.2% / **one week 89.8% (s35-6)**. risk_max 0.15 +€351 (t=2.2), 12/12; hard_thr 0.10/0.12 and hard_k ±0. **Failing week diagnosis (s35-6):** Friday deadlines 16/91 late, metro short drives 14% late, warned 66% late (fee raises recruit nobody) → a driver shortage day late in the week (flu-like). The warning-based controller reacts too late → build a leading **flu detector** (today's 60-min booking hit rate vs earlier days).

## Sat 14:56 — tag `sweep36` — level 8, 12 seeds (s35-0..)
**Why:** Flu detector (leading indicator: today's 60-min booking hit rate vs previous days) to protect the failing-week case (s35-6 89.8%). Same seeds as sweep35 for direct comparison.

**Variants:** `CANDIDATE7`; `CANDIDATE7:flu=1`; `CANDIDATE7:flu=1,flu_mu=0.5`; `CANDIDATE7:flu=1,flu_ratio=0.85`; `CANDIDATE7:risk_max=0.15,flu=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                    12     €12,470   €3,182   94.2%  89.8%  11/12    394           —       
CANDIDATE7:flu=1                              12     €12,494   €3,147   94.3%  89.8%  11/12    393         €24    0.6
CANDIDATE7:flu=1,flu_mu=0.5                   12     €12,489   €3,244   94.6%  90.8%  12/12    392         €19    0.3
CANDIDATE7:flu=1,flu_ratio=0.85               12     €12,515   €3,404   94.5%  89.8%  11/12    392         €44    0.3
CANDIDATE7:risk_max=0.15,flu=1                12     €12,795   €3,390   94.4%  91.0%  12/12    398        €325    1.8

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.46    1.39     1.38     1.01     31.0    22     54    58      4
CANDIDATE7:flu=1                               0.46    1.39     1.38     1.01     31.1    22     53    57      3
CANDIDATE7:flu=1,flu_mu=0.5                    0.46    1.39     1.38     1.01     31.1    21     52    55      4
CANDIDATE7:flu=1,flu_ratio=0.85                0.46    1.39     1.37     1.01     31.1    21     50    54      3
CANDIDATE7:risk_max=0.15,flu=1                 0.45    1.40     1.39     1.01     31.4    22     53    56      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**sweep36 (flu detector, same seeds as sweep35):** flu ±€20 (n.s.); flu_mu 0.5 → 12/12, min 90.8%; risk_max 0.15 (+flu) +€325 (t=1.8), 12/12, min 91.0% (the 2nd positive on the same seeds) → needs fresh validation.
**Dealer option-choice model (16,204 wins with both same_day and next_day quoted):** P(same_day) = σ(2.46 − 9.77·log(p_sd/p_nd)); at the natural +7.5% list premium 84–86% choose same_day; it takes a ~+20% premium to reach 50%. With two negative blanket-premium tests (sd_prem 0.08 −€447, 0.04 −€50), **PLAN #4 (menu pricing) is deprioritised**: the dealers who need same_day go to the competitor.

## Sat 15:04 — RANKING RUNS — `CANDIDATE7`
**Why:** Sat 15:00 round with CANDIDATE7 (adds: late_h 10, 90-min 1.0x step, trade-in decline, min slack 240, note reader v3, no peak smoothing, hard_thr .08). Bench: ~96% OT, 16/16 ranked.

- run 1: €17,822, on-time 93.9%, won 446
- run 2: €18,266, on-time 97.1%, won 452
- run 3: €11,350, on-time 89.8%, won 381
- run 4: €12,910, on-time 94.3%, won 401
- run 5: €19,676, on-time 97.5%, won 487
- **5 ranking runs: total €80,023 (€16,005/week), min on-time 89.8%**

**Result (board4, Sat 15:00 round, CANDIDATE7):** €17,822 / €18,266 / €11,350 / €12,910 / €19,676 → **€80,023 (€16.0k/wk), but run 3 at 89.8% → NOT RANKED** (it would lead the 6 teams finished so far). **That's 2 failing weeks out of 10 on real ranking worlds vs ~1 in 70+ on our bench → the ranking worlds are harsher; the true weekly failure risk may be 10–20%.** An unranked final scores 0 → **safety beats ~€1k/wk of margin.** Next: a safety-first sweep (escalation after 60–90 min unbooked, flu detector, stronger controller, tighter gate), selected by worst-week OT on 20 seeds.

## Sat 15:05 — tag `validate8` — level 8, 20 seeds (v8-0..)
**Why:** PLAN #1: confirm risk_max .15 (+351/+325 on the same s35 seeds) and flu detector (safety) on 20 untouched paired weeks.

**Variants:** `CANDIDATE7`; `CANDIDATE7:risk_max=0.15`; `CANDIDATE7:risk_max=0.15,flu=1,flu_mu=0.5`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                    20     €14,771   €2,690   95.8%  93.4%  20/20    424           —       
CANDIDATE7:risk_max=0.15                      20     €14,870   €2,831   95.1%  92.1%  20/20    428        €100    0.9
CANDIDATE7:risk_max=0.15,flu=1,flu_mu=0.5     20     €14,821   €2,849   95.4%  93.3%  20/20    424         €50    0.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.51    1.43     1.43     1.01     34.3    17     53    44      2
CANDIDATE7:risk_max=0.15                       0.50    1.43     1.44     1.01     34.2    20     54    51      2
CANDIDATE7:risk_max=0.15,flu=1,flu_mu=0.5      0.50    1.43     1.43     1.01     34.4    19     53    48      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**validate8 (20 fresh seeds):** risk_max 0.15 +€100 (n.s.), less safe (min 92.1%) → rejected; flu adds nothing measurable. CANDIDATE7 €14.8k / 95.8% / min 93.4% / 20/20.
**Stress set** = the 12 seeds where any recent candidate had its worst on-time week (87.6–90.2%): s22-7, s25-2, s28-9, s28-3, s35-6, s26-3, s30-4, s23-3, val-8, val-9, s26-2, s26-7. Safety variants are judged on min OT and failures on this set.

## Sat 15:13 — tag `stress1` — level 8, 12 seeds (s22-7..)
**Why:** SAFETY-FIRST on the stress set (12 worst seeds): 2 of 10 real ranking weeks failed at 89.8%. Select the lever that lifts worst-week OT most per EUR.

**Variants:** `CANDIDATE7`; `CANDIDATE7:step1_min=90,step1_f=1.1`; `CANDIDATE7:step1_min=120,step1_f=1.05`; `CANDIDATE7:flu=1,flu_mu=0.5`; `CANDIDATE7:s2_target=0.97,s2_k=40`; `CANDIDATE7:risk_max=0.11`; `CANDIDATE7:flu=1,flu_mu=0.5,s2_target=0.97,s2_k=40,risk_max=0.11`; `CANDIDATE7:step1_min=90,step1_f=1.1,flu=1,flu_mu=0.5`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                    12     €13,665   €2,925   93.8%  89.8%  11/12    404           —       
CANDIDATE7:step1_min=90,step1_f=1.1           12     €12,999   €2,488   93.8%  90.5%  12/12    406       €-666   -3.5
CANDIDATE7:step1_min=120,step1_f=1.05         12     €13,176   €2,687   93.4%  90.8%  12/12    403       €-489   -3.7
CANDIDATE7:flu=1,flu_mu=0.5                   12     €13,661   €2,922   94.1%  90.8%  12/12    400         €-4   -0.1
CANDIDATE7:s2_target=0.97,s2_k=40             12     €13,440   €3,133   94.2%  91.2%  12/12    392       €-225   -1.3
CANDIDATE7:risk_max=0.11                      12     €13,280   €3,035   94.5%  91.6%  12/12    396       €-385   -2.5
CANDIDATE7:flu=1,flu_mu=0.5,s2_target=0.97,s  12     €13,115   €2,933   94.7%  92.3%  12/12    384       €-551   -4.3
CANDIDATE7:step1_min=90,step1_f=1.1,flu=1,fl  12     €13,045   €2,638   94.0%  90.2%  12/12    402       €-620   -4.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.48    1.41     1.41     1.01     33.3    24     59    59      3
CANDIDATE7:step1_min=90,step1_f=1.1            0.48    1.41     1.41     1.04     31.7    25     62    60      3
CANDIDATE7:step1_min=120,step1_f=1.05          0.48    1.41     1.41     1.02     32.2    26     62    58      3
CANDIDATE7:flu=1,flu_mu=0.5                    0.48    1.41     1.41     1.01     33.7    23     57    56      3
CANDIDATE7:s2_target=0.97,s2_k=40              0.47    1.41     1.41     1.00     33.7    22     54    52      2
CANDIDATE7:risk_max=0.11                       0.49    1.40     1.41     1.00     33.0    21     54    52      3
CANDIDATE7:flu=1,flu_mu=0.5,s2_target=0.97,s   0.48    1.41     1.41     1.00     33.6    20     52    47      3
CANDIDATE7:step1_min=90,step1_f=1.1,flu=1,fl   0.48    1.41     1.41     1.03     32.1    24     59    57      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (stress1, 12 hardest seeds):** CANDIDATE7 min 89.8% (3 weeks < 92%). Time-based escalation −€489/−€666 and still 3 weeks < 92%: an expensive, weak lever. **SAFE = flu(0.5) + s2 0.97/k40 + risk_max 0.11: min 92.3%, 0 weeks < 92%, −€551 (−4%)** → the best safety per €. Next: validate SAFE and SAFER on fresh seeds.

## Sat 15:22 — tag `validate9` — level 8, 16 seeds (v9-0..)
**Why:** Validate SAFE (stress-set winner) and SAFER on 16 untouched seeds: margin cost vs worst-week OT.

**Variants:** `CANDIDATE7`; `SAFE`; `SAFER`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE7                                    16     €13,037   €3,624   95.4%  90.9%  16/16    400           —       
SAFE                                          16     €12,879   €3,529   96.8%  92.6%  16/16    387       €-158   -1.0
SAFER                                         16     €12,442   €3,297   97.2%  94.2%  16/16    374       €-595   -4.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE7                                     0.47    1.39     1.39     1.01     31.8    18     54    44      2
SAFE                                           0.48    1.39     1.39     1.00     32.4    12     52    33      2
SAFER                                          0.47    1.39     1.38     0.99     32.4    10     49    28      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (validate9, 16 fresh seeds):** **SAFE −€158 (n.s.), 96.8% on time, min 92.6%, 16/16** (CANDIDATE7: 95.4%, min 90.9%). SAFER −€595, 97.2%, min 94.2%. → **CANDIDATE8 = SAFE** (alias CANDIDATE). Leader-level punctuality at ~no cost; the 18:00 ranking round tests it on harsh real worlds.
**Robustness (CANDIDATE8, seed v9-3):** restart at Wed 12:00 → €17,866 / 95.2% / 438 won vs uninterrupted €16,372 / 96.7% / 420 (state incl. trust 99 and 18 deferred orders restored). Thursday-start join → **167 orders, €5,881, 97.6%** (the 14:00 test-final winner had 158 / €4,023 on a different world).

## Sat 15:30 — tag `sweep38` — level 8, 12 seeds (s38-0..)
**Why:** Margin levers on top of SAFE (CANDIDATE8): late-cost and assumed-fee scale, lane-specific cost, hard-order fee slope, small EUR risk penalty. Safety must stay (min OT, 12/12).

**Variants:** `CANDIDATE8`; `CANDIDATE8:late_cost=1.2`; `CANDIDATE8:late_cost=1.8`; `CANDIDATE8:fee_hat=0.95`; `CANDIDATE8:fee_hat=1.05`; `CANDIDATE8:lane_cost=1`; `CANDIDATE8:hard_k=2`; `CANDIDATE8:mu_eur=15,risk_hard=0.6`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE8                                    12     €13,805   €3,659   96.0%  92.8%  12/12    401           —       
CANDIDATE8:late_cost=1.2                      12     €13,765   €3,525   96.2%  93.2%  12/12    409        €-40   -0.2
CANDIDATE8:late_cost=1.8                      12     €13,611   €3,516   96.4%  93.4%  12/12    392       €-194   -1.4
CANDIDATE8:fee_hat=0.95                       12     €13,650   €3,483   95.9%  92.3%  12/12    424       €-155   -0.8
CANDIDATE8:fee_hat=1.05                       12     €13,750   €3,448   96.4%  94.9%  12/12    380        €-56   -0.3
CANDIDATE8:lane_cost=1                        12     €13,728   €3,689   96.0%  93.4%  12/12    402        €-78   -0.6
CANDIDATE8:hard_k=2                           12     €13,755   €3,675   96.0%  93.4%  12/12    402        €-51   -0.7
CANDIDATE8:mu_eur=15,risk_hard=0.6            12     €14,803   €3,583   95.0%  92.8%  12/12    413        €997    4.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE8                                     0.50    1.42     1.41     1.00     33.6    16     54    44      3
CANDIDATE8:late_cost=1.2                       0.51    1.41     1.40     1.00     32.9    15     57    40      3
CANDIDATE8:late_cost=1.8                       0.49    1.43     1.41     1.00     34.0    14     54    39      3
CANDIDATE8:fee_hat=0.95                        0.53    1.40     1.39     1.00     31.4    17     63    44      3
CANDIDATE8:fee_hat=1.05                        0.47    1.45     1.44     1.00     35.4    13     52    36      2
CANDIDATE8:lane_cost=1                         0.50    1.43     1.41     1.00     33.4    16     55    43      3
CANDIDATE8:hard_k=2                            0.50    1.42     1.41     1.00     33.5    15     55    43      3
CANDIDATE8:mu_eur=15,risk_hard=0.6             0.45    1.46     1.43     1.02     35.2    20     59    51      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep38, s38-*, 12 seeds, on SAFE):** **mu_eur 15 + risk_hard 0.6 (soft € risk penalty instead of the hard 0.11 gate): +€997 (t=4.4), min 92.8%, 12/12** → promising. late_cost, fee_hat, lane_cost, hard_k: all within noise. → test the mu_eur scale and hard-gate level on the stress set AND fresh seeds (safety first).

## Sat 15:41 — tag `sweep39` — level 8, 24 seeds (s22-7..)
**Why:** Soft EUR risk penalty (mu_eur) vs hard gate on top of SAFE: scale 10/15/25 and hard cap 0.3/0.4/0.6. Seeds = 12-seed stress set + 12 fresh s39-* (safety + margin).

**Variants:** `CANDIDATE8`; `CANDIDATE8:mu_eur=10,risk_hard=0.6`; `CANDIDATE8:mu_eur=15,risk_hard=0.6`; `CANDIDATE8:mu_eur=25,risk_hard=0.6`; `CANDIDATE8:mu_eur=15,risk_hard=0.4`; `CANDIDATE8:mu_eur=15,risk_hard=0.3`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE8                                    24     €13,344   €2,659   95.5%  92.3%  24/24    391           —       
CANDIDATE8:mu_eur=10,risk_hard=0.6            24     €14,045   €2,905   94.2%  89.3%  23/24    402        €701    5.2
CANDIDATE8:mu_eur=15,risk_hard=0.6            24     €14,042   €2,894   94.3%  90.0%  24/24    399        €698    4.9
CANDIDATE8:mu_eur=25,risk_hard=0.6            24     €14,246   €2,707   94.8%  91.2%  24/24    396        €903    5.8
CANDIDATE8:mu_eur=15,risk_hard=0.4            24     €14,042   €2,894   94.3%  90.0%  24/24    399        €698    4.9
CANDIDATE8:mu_eur=15,risk_hard=0.3            24     €14,014   €2,863   94.3%  90.0%  24/24    399        €670    4.7

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE8                                     0.48    1.41     1.41     1.00     33.7    17     52    41      3
CANDIDATE8:mu_eur=10,risk_hard=0.6             0.44    1.44     1.43     1.02     34.4    23     55    56      3
CANDIDATE8:mu_eur=15,risk_hard=0.6             0.44    1.45     1.43     1.02     34.6    22     56    53      3
CANDIDATE8:mu_eur=25,risk_hard=0.6             0.43    1.46     1.44     1.02     35.5    20     52    49      3
CANDIDATE8:mu_eur=15,risk_hard=0.4             0.44    1.45     1.43     1.02     34.6    22     56    53      3
CANDIDATE8:mu_eur=15,risk_hard=0.3             0.44    1.45     1.43     1.02     34.5    22     56    54      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep39, 12 stress + 12 fresh seeds, on SAFE):** the soft € risk penalty replaces the hard gate. **mu_eur 25: +€903 (t=5.8)**, stress min 91.2% / fresh min 91.8%, 0 failures (SAFE: stress min 92.3%). mu 15: +€698, stress min 90.0%. mu 10: +€701 but one stress week at 89.3% ✗. The hard cap level (0.3–0.6) is irrelevant. → test mu 35/50 and the hazard-DP fee schedule (`haz`, booking model AUC 0.915; DP predicts P(booked before warning) 0.961 → 0.994).

## Sat 15:55 — tag `sweep40` — level 8, 24 seeds (s22-7..)
**Why:** Stronger soft risk penalties (35/50) for safety, and the hazard-DP fee schedule (bet #1) alone and combined. Stress set + fresh s40-*.

**Variants:** `CANDIDATE8`; `CANDIDATE8:mu_eur=25,risk_hard=0.6`; `CANDIDATE8:mu_eur=35,risk_hard=0.6`; `CANDIDATE8:mu_eur=50,risk_hard=0.6`; `CANDIDATE8:haz=1`; `CANDIDATE8:mu_eur=25,risk_hard=0.6,haz=1`; `CANDIDATE8:mu_eur=35,risk_hard=0.6,haz=1`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE8                                    24     €12,778   €2,489   95.9%  92.3%  24/24    380           —       
CANDIDATE8:mu_eur=25,risk_hard=0.6            24     €13,687   €2,764   94.9%  91.2%  24/24    385        €909    4.6
CANDIDATE8:mu_eur=35,risk_hard=0.6            24     €13,516   €2,991   95.0%  90.4%  24/24    378        €738    3.4
CANDIDATE8:mu_eur=50,risk_hard=0.6            24     €13,377   €2,796   95.5%  92.0%  24/24    367        €599    3.1
CANDIDATE8:haz=1                              24     €13,186   €2,519   96.8%  93.5%  24/24    383        €408    3.5
CANDIDATE8:mu_eur=25,risk_hard=0.6,haz=1      24     €13,908   €2,780   95.8%  92.0%  24/24    389      €1,130    5.7
CANDIDATE8:mu_eur=35,risk_hard=0.6,haz=1      24     €13,838   €2,780   95.7%  91.8%  24/24    384      €1,060    4.9

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE8                                     0.48    1.40     1.40     0.99     33.2    16     48    37      3
CANDIDATE8:mu_eur=25,risk_hard=0.6             0.42    1.45     1.43     1.02     35.0    19     50    47      3
CANDIDATE8:mu_eur=35,risk_hard=0.6             0.41    1.44     1.43     1.01     35.2    19     49    46      3
CANDIDATE8:mu_eur=50,risk_hard=0.6             0.40    1.45     1.43     1.01     35.9    16     46    40      3
CANDIDATE8:haz=1                               0.48    1.40     1.40     0.99     33.9    12     50    24      2
CANDIDATE8:mu_eur=25,risk_hard=0.6,haz=1       0.43    1.44     1.43     1.01     35.1    16     51    34      3
CANDIDATE8:mu_eur=35,risk_hard=0.6,haz=1       0.42    1.44     1.43     1.01     35.5    16     51    34      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep40, 12 stress + 12 fresh):** **hazard-DP fee schedule (`haz`) +€408 (t=3.5) and safer** (96.8% on time, min 93.5%, warnings 37 → 24/wk). **mu_eur 25 + haz: +€1,130 (t=5.7)**, min 92.0% on stress, 0 failures → **CANDIDATE9**. mu 35/50 add nothing over 25. The user's bet #1 (learn the booking process, optimise fee timing) is confirmed in closed loop.

## Sat 16:02 — tag `validate10` — level 8, 20 seeds (v10-0..)
**Why:** Confirm CANDIDATE9 (SAFE + soft risk penalty 25 + hazard-DP fees) on 20 untouched paired weeks; also the DP's alternative tables (late_high, no_learning).

**Variants:** `CANDIDATE8`; `CANDIDATE9`; `CANDIDATE9:haz_variant=late_high`; `CANDIDATE9:haz_variant=no_learning`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE8                                    18     €13,069   €3,314   96.3%  92.5%  18/18    382           —       
CANDIDATE9                                    18     €14,319   €3,553   95.9%  92.8%  18/18    388      €1,251    5.9
CANDIDATE9:haz_variant=late_high              18     €13,945   €3,689   95.8%  92.6%  18/18    390        €877    6.5
CANDIDATE9:haz_variant=no_learning            18     €13,720   €3,239   95.7%  93.0%  18/18    387      €1,048    5.8

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE8                                     0.48    1.41     1.40     0.99     33.5    14     46    34      2
CANDIDATE9                                     0.43    1.45     1.43     1.01     36.2    15     51    33      3
CANDIDATE9:haz_variant=late_high               0.43    1.45     1.43     1.03     35.0    16     50    29      2
CANDIDATE9:haz_variant=no_learning             0.43    1.44     1.42     1.02     34.9    16     48    31      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**validate10 (untouched v10-*, 18 paired weeks; 8 lost to a server restart):** **CANDIDATE9 +€1,251 (t=5.9)** vs CANDIDATE8, €14.3k/wk, 95.9%, min 92.8%, 18/18. The DP alternatives (late_high, no_learning) are positive but lower. → **CANDIDATE9 = current final candidate**; the 18:00 ranking round uses it.

**Fixes from user's research audit (Sat ~16:15):**
(1) notes: a delivery clause ("delivery by 16:00, correction…") was parsed as the earliest *pickup* → pickup forbidden until the delivery deadline. Fixed: delivery clauses never set pickup readiness unless they name the pickup. Offline vs truth: catches 96% of delays, **false delays 1.1% → 0.6%**.
(2) **SLA guard** (`sla_guard`): misses allowed = floor(N/10) − ledger-late − expected pending misses (warned+unbooked 0.6, warned+booked 0.25, past deadline 1.0, else 0.02); below guard_k → rescue mode (urgent fees 1.6 → 2.5×, re-price open urgent gigs, mu ≥ 0.4). Costs nothing in normal weeks; spends money only when the 90% floor is in danger.
(3) risk labels from the ledger (late_refund / undelivered) instead of timestamps (131 misses were labelled on time) → `risk_v4.json` (late rate 5.9%, AUC 0.72).
Board4 analysis (user): the failed week allowed 38 misses and had 39; we won more orders than #1 but delivered 20 fewer on time.

## Sat 16:24 — tag `sweep41` — level 8, 24 seeds (s22-7..)
**Why:** Refine CANDIDATE9: hard-order bump inside the DP schedule (0/2 vs 4), risk penalty 20/30, whether SAFE's stronger controller and flu detector are still needed with DP fees, DP opening floor 0.85.

**Variants:** `CANDIDATE9`; `CANDIDATE9:hard_k=0`; `CANDIDATE9:hard_k=2`; `CANDIDATE9:mu_eur=20`; `CANDIDATE9:mu_eur=30`; `CANDIDATE9:s2_target=0.96,s2_k=25`; `CANDIDATE9:flu=0`; `CANDIDATE9:fee_floor=0.85`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE9                                    24     €13,933   €2,584   95.4%  92.0%  24/24    387           —       
CANDIDATE9:hard_k=0                           24     €14,324   €2,676   95.0%  89.9%  23/24    386        €391    3.2
CANDIDATE9:hard_k=2                           24     €14,178   €2,601   95.2%  91.9%  24/24    387        €245    1.9
CANDIDATE9:mu_eur=20                          24     €14,058   €2,604   94.9%  91.5%  24/24    392        €124    1.2
CANDIDATE9:mu_eur=30                          24     €13,934   €2,581   95.4%  91.7%  24/24    387          €1    0.0
CANDIDATE9:s2_target=0.96,s2_k=25             24     €14,119   €2,556   95.0%  89.1%  22/24    399        €186    2.6
CANDIDATE9:flu=0                              24     €13,904   €2,569   95.1%  91.6%  24/24    392        €-29   -0.4
CANDIDATE9:fee_floor=0.85                     24     €13,933   €2,584   95.4%  92.0%  24/24    387           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE9                                     0.42    1.43     1.42     1.01     35.5    17     52    35      3
CANDIDATE9:hard_k=0                            0.42    1.43     1.42     1.00     36.6    19     51    38      3
CANDIDATE9:hard_k=2                            0.42    1.43     1.42     1.00     36.1    18     53    38      3
CANDIDATE9:mu_eur=20                           0.43    1.43     1.42     1.02     35.3    19     54    39      3
CANDIDATE9:mu_eur=30                           0.42    1.43     1.42     1.01     35.5    18     54    34      3
CANDIDATE9:s2_target=0.96,s2_k=25              0.43    1.43     1.42     1.02     34.9    20     56    41      3
CANDIDATE9:flu=0                               0.42    1.43     1.42     1.02     35.0    19     53    38      3
CANDIDATE9:fee_floor=0.85                      0.42    1.43     1.42     1.01     35.5    17     52    35      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (sweep41, stress + fresh, 24 weeks):** hard_k 2 **+€245 (t=1.9), 24/24, min 91.9%** → tweak candidate. hard_k 0 +€391 but one week 89.9% ✗; s2 0.96/k25 +€186 but **2 weeks < 90%** ✗ → SAFE's controls are load-bearing. mu 20/30, flu 0, fee_floor 0.85: ≈0.

## Sat 16:50 — tag `sweep42` — level 8, 24 seeds (s22-7..)
**Why:** HARD 90% enforcement: SLA budget guard with rescue spending (k 4/6/8), and risk v4 (ledger-true labels). Stress set + fresh s42-*. Notes delivery-clause fix in all variants.

**Variants:** `CANDIDATE9`; `CANDIDATE9:sla_guard=1`; `CANDIDATE9:sla_guard=1,guard_k=6`; `CANDIDATE9:sla_guard=1,guard_k=8,rescue_max=3.0`; `CANDIDATE9:risk_file=risk_v4.json`; `CANDIDATE9:risk_file=risk_v4.json,sla_guard=1,guard_k=6`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE9                                    24     €13,596   €2,832   95.4%  92.1%  24/24    389           —       
CANDIDATE9:sla_guard=1                        24     €13,511   €3,023   95.2%  91.3%  24/24    386        €-85   -0.8
CANDIDATE9:sla_guard=1,guard_k=6              24     €13,419   €2,990   95.5%  90.0%  24/24    384       €-177   -1.7
CANDIDATE9:sla_guard=1,guard_k=8,rescue_max=  23     €13,266   €3,045   95.6%  91.9%  23/23    380       €-244   -2.5
CANDIDATE9:risk_file=risk_v4.json             22     €13,479   €2,989   95.2%  90.2%  22/22    377       €-155   -1.2
CANDIDATE9:risk_file=risk_v4.json,sla_guard=  24     €13,440   €2,871   95.4%  92.2%  24/24    374       €-156   -1.5

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE9                                     0.43    1.44     1.42     1.02     34.3    17     53    36      2
CANDIDATE9:sla_guard=1                         0.42    1.44     1.42     1.02     34.4    18     51    38      3
CANDIDATE9:sla_guard=1,guard_k=6               0.42    1.44     1.43     1.02     34.3    16     52    35      2
CANDIDATE9:sla_guard=1,guard_k=8,rescue_max=   0.42    1.44     1.42     1.02     34.3    16     50    33      2
CANDIDATE9:risk_file=risk_v4.json              0.41    1.45     1.43     1.01     35.1    17     51    35      3
CANDIDATE9:risk_file=risk_v4.json,sla_guard=   0.41    1.46     1.43     1.01     35.4    17     49    33      2

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (sweep42):** the SLA guard is neutral or negative (−€85 to −€244), no better worst week (90.0–91.9% vs 92.1%) despite 57–82 rescue activations: **when an order is about to miss, no driver can be bought in time. Prevention at quote time (SAFE) works; last-minute cure doesn't.** Risk v4 (ledger labels) −€155, no safety gain. → keep CANDIDATE9 (stress min 92.1%, fresh min 92.1%, 24/24). Notes delivery-clause fix kept (correctness).

## Sat 16:59 — tag `sweep43` — level 8, 24 seeds (s22-7..)
**Why:** Firm up the last safe margin tweak: hard-order bump 2/3 (sweep41 +245, 24/24) inside the DP schedule, with mu 20 / DP no_learning table. Stress + fresh s43-*.

**Variants:** `CANDIDATE9`; `CANDIDATE9:hard_k=2`; `CANDIDATE9:hard_k=3`; `CANDIDATE9:hard_k=2,mu_eur=20`; `CANDIDATE9:hard_k=2,haz_variant=no_learning`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE9                                    24     €13,756   €2,885   95.3%  90.5%  24/24    388           —       
CANDIDATE9:hard_k=2                           24     €13,919   €2,815   95.0%  91.9%  24/24    386        €163    1.4
CANDIDATE9:hard_k=3                           24     €13,844   €2,898   95.2%  91.4%  24/24    386         €88    0.8
CANDIDATE9:hard_k=2,mu_eur=20                 24     €13,886   €2,962   95.2%  89.9%  23/24    388        €131    0.9
CANDIDATE9:hard_k=2,haz_variant=no_learning   24     €13,786   €2,904   95.4%  90.2%  24/24    387         €30    0.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE9                                     0.42    1.44     1.42     1.01     34.9    17     54    38      3
CANDIDATE9:hard_k=2                            0.42    1.44     1.42     1.00     35.4    19     53    41      3
CANDIDATE9:hard_k=3                            0.42    1.44     1.42     1.01     35.2    18     53    38      3
CANDIDATE9:hard_k=2,mu_eur=20                  0.42    1.44     1.42     1.00     35.2    18     53    39      3
CANDIDATE9:hard_k=2,haz_variant=no_learning    0.42    1.44     1.43     1.02     35.0    17     53    36      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (sweep43):** hard_k 2 +€163 and safer (min 91.9/92.0% vs C9's 90.5% on one fresh seed); positive in sweep41 too → **CANDIDATE10**. Note: in C9/C10 the mu_eur penalty disables SAFE's hard 0.11 gate (gate = risk_hard 0.6), so safety rests on the controller + flu + penalty → test stronger safety settings.

## Sat 17:14 — tag `sweep44` — level 8, 36 seeds (s22-7..)
**Why:** STRICT 90%: safety strength on CANDIDATE10 - stronger projected-OT controller (.975/60, .98/80), stronger flu response, higher risk penalty, hard gate at high risk. 12 stress + 24 fresh seeds; select on min OT and #weeks<91%.

**Variants:** `CANDIDATE10`; `CANDIDATE10:s2_target=0.975,s2_k=60`; `CANDIDATE10:s2_target=0.98,s2_k=80`; `CANDIDATE10:flu_mu=0.7`; `CANDIDATE10:mu_eur=35`; `CANDIDATE10:risk_hard=0.25`; `CANDIDATE10:s2_target=0.975,s2_k=60,risk_hard=0.3`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE10                                   35     €14,028   €3,349   95.3%  89.0%  34/35    386           —       
CANDIDATE10:s2_target=0.975,s2_k=60           35     €14,004   €3,502   95.9%  92.1%  35/35    377        €-24   -0.2
CANDIDATE10:s2_target=0.98,s2_k=80            34     €13,850   €3,544   96.1%  92.2%  34/34    369       €-207   -1.2
CANDIDATE10:flu_mu=0.7                        35     €14,006   €3,241   95.4%  89.1%  34/35    385        €-60   -1.1
CANDIDATE10:mu_eur=35                         35     €14,117   €3,400   95.6%  90.9%  35/35    384         €50    0.4
CANDIDATE10:risk_hard=0.25                    35     €14,042   €3,315   95.4%  89.0%  34/35    388        €-16   -0.3
CANDIDATE10:s2_target=0.975,s2_k=60,risk_har  35     €14,006   €3,459   96.0%  92.1%  35/35    380        €-53   -0.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE10                                    0.42    1.44     1.43     1.01     35.6    18     53    38      3
CANDIDATE10:s2_target=0.975,s2_k=60            0.42    1.45     1.43     1.00     36.3    15     51    32      2
CANDIDATE10:s2_target=0.98,s2_k=80             0.41    1.46     1.44     1.00     36.7    14     50    29      3
CANDIDATE10:flu_mu=0.7                         0.43    1.44     1.43     1.01     35.6    17     53    37      3
CANDIDATE10:mu_eur=35                          0.42    1.45     1.43     1.00     36.0    16     52    34      3
CANDIDATE10:risk_hard=0.25                     0.43    1.44     1.43     1.01     35.4    17     53    38      3
CANDIDATE10:s2_target=0.975,s2_k=60,risk_har   0.42    1.45     1.43     1.00     36.1    15     50    31      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep44, 12 stress + 23 fresh):** **CANDIDATE10 failed one fresh week (89.0%)**. Stronger controller **s2 0.975/k60: 35/35, min 92.1% (stress 92.5%), −€24 (n.s.) → CANDIDATE11**. s2 0.98/k80 is equally safe but −€207. flu_mu 0.7 and risk_hard 0.25 don't fix the fresh failure; mu_eur 35 is 90.9% min.

## Sat 17:30 — tag `sweep45` — level 8, 32 seeds (s22-7..)
**Why:** User cost ideas on CANDIDATE11: (1) reset emergency pricing when a reschedule leaves >=8h (R00475 lost EUR21 at urgent fees after 2 reschedules); (2) job-specific expected payout in quotes (fee_est = typical*(1+k*P(late)); 97 orders >=1.1x typical held 20 of 22 misses); (3) real cheaper DP opening 0.85/0.80 for easy gigs (P(late)<.05, coverage>=60, >=10h, not same_day/private).

**Variants:** `CANDIDATE11`; `CANDIDATE11:urgent_reset=1`; `CANDIDATE11:cost_pl_k=1`; `CANDIDATE11:cost_pl_k=2`; `CANDIDATE11:haz_easy_open=0.85`; `CANDIDATE11:haz_easy_open=0.8`; `CANDIDATE11:urgent_reset=1,cost_pl_k=1,haz_easy_open=0.85`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE11                                   31     €15,046   €3,495   95.9%  92.5%  31/31    393           —       
CANDIDATE11:urgent_reset=1                    31     €15,148   €3,508   95.6%  90.6%  31/31    395        €102    1.2
CANDIDATE11:cost_pl_k=1                       31     €14,563   €3,439   96.5%  93.1%  31/31    372       €-483   -3.2
CANDIDATE11:cost_pl_k=2                       31     €14,295   €3,414   97.0%  94.1%  31/31    358       €-751   -5.9
CANDIDATE11:haz_easy_open=0.85                32     €15,261   €3,493   95.8%  92.5%  32/32    396        €193    2.2
CANDIDATE11:haz_easy_open=0.8                 30     €15,299   €3,327   95.5%  90.5%  30/30    394         €90    0.9
CANDIDATE11:urgent_reset=1,cost_pl_k=1,haz_e  31     €14,995   €3,428   96.3%  94.2%  31/31    375       €-193   -1.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE11                                    0.43    1.46     1.44     1.00     37.5    16     53    34      3
CANDIDATE11:urgent_reset=1                     0.43    1.45     1.44     1.00     37.6    17     54    37      3
CANDIDATE11:cost_pl_k=1                        0.41    1.47     1.45     0.99     38.3    12     48    28      4
CANDIDATE11:cost_pl_k=2                        0.40    1.48     1.46     0.99     39.1    10     46    24      3
CANDIDATE11:haz_easy_open=0.85                 0.43    1.46     1.44     1.00     37.7    16     52    33      3
CANDIDATE11:haz_easy_open=0.8                  0.43    1.46     1.45     1.00     38.1    17     54    36      3
CANDIDATE11:urgent_reset=1,cost_pl_k=1,haz_e   0.42    1.47     1.45     0.98     39.2    13     49    28      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep45, 12 stress + ~19 fresh, user cost ideas):** **haz_easy_open 0.85 (cheaper DP opening on easy gigs) +€193 (t=2.2), same safety (min 92.5%) → CANDIDATE12.** cost_pl_k 1/2 (job-specific payout in quotes): min 93.1%/94.1% but −€483/−€751 = a safety knob. urgent_reset +€102 but min 90.6% → rejected. **FORTRESS** = reset + cost_pl_k 1 + easy 0.85: **min 94.2% on stress AND fresh**, −€193 → the insurance option for the final.
**Reality check (user):** €15k/wk × 5 = €75k < the ~€85k top-10 cutoff? Practice seeds ≠ ranking worlds. In the 15:00 round C7 made €16.0k/wk on real worlds vs €13.3k on practice (~+20% richer worlds). Paired C12 − C7 ≈ +€1.8k/wk → projected ≈ €89k on the 15:00 worlds (≈ #2), ≈ #10 on the 12:00 worlds. **Borderline top 10 → keep pushing margin.**
**Ops note:** killed the accidental 1-worker sweep46; `--cleanup` then also deleted validate12's 7 in-flight worlds (they're logged as FAILED; the paired analysis drops them). Rule: never run `--cleanup` while any bench is running.

## Sat 17:42 — tag `validate12` — level 8, 24 seeds (v12-0..)
**Why:** Untouched validation for the final choice: C11 vs C12 (easy .85) vs FORTRESS (safest) vs C12+cost_pl_k .5 (middle). 24 fresh paired weeks.

**Variants:** `CANDIDATE11`; `CANDIDATE12`; `FORTRESS`; `CANDIDATE12:cost_pl_k=0.5`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE11                                   22     €14,962   €4,219   96.4%  92.7%  22/22    390           —       
CANDIDATE12                                   22     €15,051   €4,387   96.4%  92.7%  22/22    389         €89    0.6
FORTRESS                                      23     €14,629   €4,334   96.7%  93.9%  23/23    371       €-195   -1.2
CANDIDATE12:cost_pl_k=0.5                     22     €15,063   €4,386   96.5%  94.3%  22/22    385         €83    0.4

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE11                                    0.43    1.46     1.43     1.00     37.2    14     49    29      3
CANDIDATE12                                    0.43    1.46     1.43     1.00     37.6    14     48    30      3
FORTRESS                                       0.41    1.46     1.44     0.99     38.2    12     45    25      2
CANDIDATE12:cost_pl_k=0.5                      0.43    1.46     1.44     0.99     38.0    13     46    28      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```
**Decision (validate12, 22–23 untouched weeks):** C12 +€89 vs C11 (same safety, min 92.7%). **C12 + cost_pl_k 0.5: +€83 and the best worst week (94.3%)** → **CANDIDATE13** (alias CANDIDATE; plays the 18:00 round). FORTRESS −€195, min 93.9%.

## Sat 17:52 — tag `sweep46` — level 8, 16 seeds (s46-0..)
**Why:** Margin push on CANDIDATE13 (borderline top-10): broader cheap DP openings, DP late_low table, risk penalty 20, faster world learning, lower Monday price prior.

**Variants:** `CANDIDATE13`; `CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30`; `CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30,haz_easy_h=6`; `CANDIDATE13:haz_variant=late_low`; `CANDIDATE13:mu_eur=20`; `CANDIDATE13:eta_w=0.04`; `CANDIDATE13:theta0=0.20`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE13                                   16     €15,412   €4,797   96.6%  95.6%  16/16    381           —       
CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30  15     €15,513   €4,949   96.7%  95.1%  15/15    381         €68    0.8
CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30  14     €15,322   €5,078   96.7%  95.1%  14/14    378         €63    0.7
CANDIDATE13:haz_variant=late_low              16     €15,047   €4,692   96.1%  94.0%  16/16    367       €-365   -1.8
CANDIDATE13:mu_eur=20                         15     €15,557   €4,777   96.5%  95.1%  15/15    384        €112    0.7
CANDIDATE13:eta_w=0.04                        15     €15,058   €4,778   96.7%  95.3%  15/15    375       €-387   -1.9
CANDIDATE13:theta0=0.20                       15     €15,445   €4,964   96.6%  95.6%  15/15    380           —       

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE13                                    0.42    1.46     1.44     0.99     39.3    12     46    26      3
CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30   0.42    1.46     1.44     0.99     39.5    12     46    23      3
CANDIDATE13:haz_easy_pl=0.10,haz_easy_cov=30   0.42    1.46     1.44     0.99     39.4    12     46    23      3
CANDIDATE13:haz_variant=late_low               0.41    1.45     1.44     0.97     39.9    14     42    34      3
CANDIDATE13:mu_eur=20                          0.42    1.46     1.45     0.99     39.4    13     45    25      2
CANDIDATE13:eta_w=0.04                         0.41    1.46     1.44     0.99     39.1    12     44    25      3
CANDIDATE13:theta0=0.20                        0.42    1.46     1.45     0.99     39.4    12     46    26      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep46, 16 fresh, on C13):** all within noise (easy-open broadening +€68, mu 20 +€112, late_low −€365, eta_w 0.04 −€387, theta0 0). **C13: 96.6% average, min 95.6%** → it has safety headroom to convert into volume (leaders ~450 orders/wk at ~€40; we ~385 at ~€38).

## Sat 18:06 — RANKING RUNS — `CANDIDATE13`
**Why:** Sat 18:00 round with CANDIDATE13 (C12 + payout-aware quotes k .5): validate12 22/22 ranked, every week >= 94.3%.

- run 1: €14,302, on-time 96.8%, won 377
- run 2: €16,630, on-time 97.8%, won 406
- run 3: €14,553, on-time 97.3%, won 367
- run 4: €11,283, on-time 96.6%, won 383
- run 5: €12,905, on-time 98.2%, won 382
- **5 ranking runs: total €69,673 (€13,935/week), min on-time 96.6%**

**RESULT board5 (Sat 18:00 round, CANDIDATE13):** €14,302 / €16,630 / €14,553 / €11,283 / €12,905 → **€69,673, ALL 5 RANKED, min on-time 96.6%** (96.8 / 97.8 / 97.3 / 96.6 / 98.2). **Rank 7 of 16 ranked** at 18:15 (#1 DaVinci €78.3k, #5 €71.4k). **The safety problem is solved on real worlds**; the gap is +2.5% to top 5 and +12% to #1 (a harder round: totals are lower for everyone).

## Sat 18:10 — tag `sweep47` — level 8, 28 seeds (s22-7..)
**Why:** VOLUME with safety headroom: C13 has min OT 94-96%; loosen the risk penalty / payout cost / controller target / assumed fee to win more orders; accept only if the stress-set worst week stays >= 92.5%.

**Variants:** `CANDIDATE13`; `CANDIDATE13:mu_eur=15`; `CANDIDATE13:mu_eur=15,cost_pl_k=0.25`; `CANDIDATE13:s2_target=0.97,s2_k=60`; `CANDIDATE13:mu_eur=15,s2_target=0.97,s2_k=60`; `CANDIDATE13:mu_eur=10,cost_pl_k=0.5`; `CANDIDATE13:fee_hat=0.95`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
CANDIDATE13                                   27     €14,451   €3,451   95.8%  92.5%  27/27    373           —       
CANDIDATE13:mu_eur=15                         27     €14,356   €3,360   95.4%  90.6%  27/27    378        €-94   -0.8
CANDIDATE13:mu_eur=15,cost_pl_k=0.25          27     €14,267   €3,262   95.3%  91.6%  27/27    378       €-183   -1.5
CANDIDATE13:s2_target=0.97,s2_k=60            27     €14,549   €3,369   95.4%  91.3%  27/27    378         €98    0.7
CANDIDATE13:mu_eur=15,s2_target=0.97,s2_k=60  27     €14,431   €3,459   95.2%  90.7%  27/27    385        €106    0.7
CANDIDATE13:mu_eur=10,cost_pl_k=0.5           27     €14,272   €3,442   95.2%  90.7%  27/27    382        €-68   -0.5
CANDIDATE13:fee_hat=0.95                      27     €14,384   €3,429   95.5%  90.8%  27/27    395         €43    0.3

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
CANDIDATE13                                    0.42    1.46     1.44     1.00     38.0    15     49    30      3
CANDIDATE13:mu_eur=15                          0.42    1.45     1.44     1.00     37.3    17     50    33      3
CANDIDATE13:mu_eur=15,cost_pl_k=0.25           0.42    1.45     1.43     1.00     37.1    17     51    35      3
CANDIDATE13:s2_target=0.97,s2_k=60             0.42    1.46     1.44     1.00     37.8    17     48    33      3
CANDIDATE13:mu_eur=15,s2_target=0.97,s2_k=60   0.43    1.45     1.44     1.00     36.8    18     52    36      3
CANDIDATE13:mu_eur=10,cost_pl_k=0.5            0.43    1.46     1.44     1.00     36.6    18     51    36      3
CANDIDATE13:fee_hat=0.95                       0.44    1.44     1.42     1.00     35.8    17     53    34      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (sweep47, volume via safety headroom):** loosening (mu 15/10, cost_pl_k 0.25, s2 0.97, fee_hat 0.95) adds +5 to +22 orders but no margin (−€183 … +€106, n.s.), and the min OT drops to 90.6–91.6% → extra orders are break-even after staffing. **C13 is the best margin AND safety → FROZEN as `FINAL`** (explicit params, `lab/final_config.json`, model checksums).

## Sat 18:25 — tag `validate_final` — level 8, 40 seeds (final-val-0..)
**Why:** Robustness evidence for the jury and the final: FINAL on 40 untouched weeks (weekly on-time distribution, failure count) vs the kit starter on the same weeks.

**Variants:** `FINAL`; `starter`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
FINAL                                         40     €14,143   €3,217   96.7%  93.3%  40/40    375           —       
starter                                       40    €-64,969  €14,969   52.7%  39.6%   0/40    895    €-79,111  -32.1

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
FINAL                                          0.42    1.45     1.43     0.99     37.0    12     47    25      2
starter                                        0.88    1.00     1.00     1.61    -71.5   407    308  1006     26

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**validate_final (40 untouched weeks):** **FINAL €14,143/wk, 96.7% on time, min 93.3%, 40/40 ranked**; kit starter on the same weeks −€64,969, 52.7% → **+€79.1k/wk (t=−32)**. 0 failures in 40 weeks → 95% upper bound on the weekly failure rate ≈ 7.5% (rule of three). Headline numbers for the jury.
**Real round 18:00 final standings check (user):** FINAL-equivalent C13 = #13 of 26 (€69.7k); #10 €71.2k (+2%), #5 €73.2k (+5%), #1 €78.3k (+12%). → Optuna `final_tune` around FINAL (12 knobs, 7 fixed seeds/trial, J penalises any week < 92.5%).

## Sat 18:52 — tag `validate_tune` — level 8, 24 seeds (s22-7..)
**Why:** Validate the top-3 Optuna trials around FINAL (T17 +1.5k, T38, T18 on tuning seeds; all loosen safety: cost_pl_k~0, s2 .96, easy open .82, fee_hat ~.95) on the stress set + fresh s48-*. Adopt only if margin up AND worst week holds.

**Variants:** `FINAL`; `FINAL:mu_eur=20.4675,late_cost=1.2273,cost_pl_k=0.0089,hard_k=0.5169,hard_thr=0.1082,s2_target=0.9641,haz_easy_open=0.8183,eta_d=0.021,fee_hat=0.9476,theta0=0.1328,risk_hard=0.4115,eta_w=0.0119`; `FINAL:mu_eur=26.2301,late_cost=1.2149,cost_pl_k=0.0418,hard_k=0.3385,hard_thr=0.1407,s2_target=0.9613,haz_easy_open=0.8168,eta_d=0.0192,fee_hat=0.9293,theta0=0.0981,risk_hard=0.4561,eta_w=0.0147`; `FINAL:mu_eur=28.1062,late_cost=1.2695,cost_pl_k=0.0741,hard_k=1.1557,hard_thr=0.1038,s2_target=0.9661,haz_easy_open=0.8411,eta_d=0.0221,fee_hat=0.9535,theta0=0.1357,risk_hard=0.3516,eta_w=0.0133`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
FINAL                                         24     €14,829   €2,997   96.1%  92.9%  24/24    380           —       
FINAL:mu_eur=20.4675,late_cost=1.2273,cost_p  24     €15,347   €3,263   93.6%  89.2%  23/24    437        €518    2.9
FINAL:mu_eur=26.2301,late_cost=1.2149,cost_p  24     €15,508   €3,128   93.5%  89.7%  23/24    448        €680    3.5
FINAL:mu_eur=28.1062,late_cost=1.2695,cost_p  24     €15,247   €3,208   94.2%  89.0%  23/24    426        €419    2.0

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
FINAL                                          0.42    1.47     1.45     0.99     38.4    14     49    28      3
FINAL:mu_eur=20.4675,late_cost=1.2273,cost_p   0.48    1.42     1.41     1.01     34.5    27     60    55      3
FINAL:mu_eur=26.2301,late_cost=1.2149,cost_p   0.49    1.42     1.41     1.01     34.0    28     64    56      3
FINAL:mu_eur=28.1062,late_cost=1.2695,cost_p   0.47    1.43     1.41     1.00     35.2    24     57    49      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (validate_tune, 12 stress + 12 fresh):** the tuned T17/T38/T18 gain +€325–902/wk (fresh) and +€421–512 (stress), but **each fails one stress week (89.0–89.7%)**; FINAL holds 92.9% → **rejected; FINAL stays.** Lesson (3rd time): tuning on easy seeds buys margin by giving up safety → robust tuner `tune3` with 4 hardest + 3 fresh seeds in every trial.

## Sat 19:18 — tag `adaptive1` — level 8, 24 seeds (s22-7..)
**Why:** ADAPTIVE aggressiveness: start as FINAL; once projected on-time >= 96.5% (from Tue, >=60 orders, controller idle) switch to the T38-like volume profile (mu 20, no payout cost, fee_hat .95, s2 .965); revert if the projection drops. Goal: T38's +EUR1.3k on easy worlds without its stress-week failures.

**Variants:** `FINAL`; `FINAL:adaptive=1`; `FINAL:adaptive=1,adapt_ot=0.97`; `FINAL:adaptive=1,adapt_mu_eur=15,adapt_fee_hat=0.93`

```

variant                                        n   margin/wk      ±sd  on-time  min OT  ranked   won   Δ vs base      t
-----------------------------------------------------------------------------------------------------------------------
FINAL                                         23     €14,217   €2,950   95.9%  92.9%  23/23    372           —       
FINAL:adaptive=1                              23     €14,505   €2,895   95.0%  89.7%  22/23    397        €185    2.0
FINAL:adaptive=1,adapt_ot=0.97                23     €14,286   €2,910   95.0%  88.8%  22/23    392         €69    0.5
FINAL:adaptive=1,adapt_mu_eur=15,adapt_fee_h  23     €14,428   €2,850   94.5%  89.9%  22/23    403         €21    0.2

variant                                       won/q  q/list won/list  fee/typ  €/order  late  drops  warn  fails
FINAL                                          0.41    1.46     1.43     0.99     37.7    15     50    28      3
FINAL:adaptive=1                               0.44    1.44     1.43     1.00     36.1    19     55    39      3
FINAL:adaptive=1,adapt_ot=0.97                 0.43    1.45     1.43     1.00     36.0    19     54    38      3
FINAL:adaptive=1,adapt_mu_eur=15,adapt_fee_h   0.44    1.44     1.42     1.01     35.3    22     56    43      3

Δ = mean paired margin difference vs the first variant on the same seeds; |t| > 2 ≈ significant.
```

**Decision (adaptive1, stress + fresh):** adaptive aggressiveness turned on in 20/23 weeks (almost every week looks easy through Tuesday; hard-world trouble like flu or Friday shortages comes later) → +€185 but **one stress week at 88.8–89.9% → rejected.** Across 5 experiments, every volume lever crosses the safety floor on the hardest worlds: **FINAL is on the efficient frontier**; gains must come from raising the frontier (structural), not trading along it. Resumed the robust tuner (stress seeds in every trial).
