# Status snapshot (Sat ~17:20)

## Why so few real L8 runs
- Ranking (board) runs: **5 weeks per level per round**; rounds every 3 h (09, 12, 15, 18, 21, 00, 03, 06). We play every round.
- Practice weeks are unlimited, using the same L8 simulator on our own seeds: ~2,500 weeks so far.
- Parallelism is capped: 8 open worlds per team and one shared rate limit (organisers: "8 weeks in parallel are not faster than 8 sequentially"). We run 7–8 at a time; batching cut requests per week from ~1,150 to ~490.

## Candidate scoreboard (L8 practice; compare via paired Δ in EXPERIMENTS.md)

| Config | Weeks | €/week | On-time | Worst | Weeks < 90% | €/order |
|---|---|---|---|---|---|---|
| CANDIDATE2 | 47 | 12,736 | 93.9% | 88.2% | 2 | 33.3 |
| CANDIDATE7 | 94 | 13,341 | 95.1% | 89.8% | 4 | 32.9 |
| CANDIDATE8 (SAFE) | 78 | 13,177 | 95.8% | 92.3% | 0 | 34.1 |
| CANDIDATE9 | 90 | 13,873 | 95.5% | 90.5% | 0 | 35.8 |
| CANDIDATE10 | 35 | 14,028 | 95.3% | 89.0% | 1 | 36.4 |
| **CANDIDATE11** | 28 | **14,991** | 95.8% | **92.5%** | **0** | **38.1** |

## Real ranking rounds
- 00:00 €40.8k (smart, rank 45/56)
- 09:00 €56.7k (beat House best)
- 12:00 €78.3k (1 week 89.5% → unranked)
- 15:00 €80.0k (1 week 89.8% → unranked; would be ~#12)
- **18:00: CANDIDATE11**, first real test of the SAFE-family fixes.
