# Competitor and driver behaviour (data analysis of 64 L8 worlds, ~66k requests, ~33k gigs)

## Competitor adaptation (identified via seeds played by several policies)
- Each morning, for a dealer: **Δlog c = +0.026 − 0.10 × our win share** (D01: +0.002 − 0.078·share).
  - Neutral at share ≈ 0.26.
  - The cuts are **cumulative and persistent**.
  - By share band: <0.1 → +1.3%; 0.3–0.6 → −3.7%; >0.9 → −9.6%.
- **Stackelberg response:** each win costs a shadow ≈ b·β·P(1−P)·margin ≈ **€8 per remaining morning** (Mon €32 … Fri 0).
  - Apply it at full weight for big dealers or trust ≥ 20.
  - Optimal D01 pricing: +0.12–0.20 log on Monday, tapering → +€230–500/wk at D01.
- Trust pricing is confirmed (coefficient 1.07–1.19× theory). Trust at D01 saturates within about a day.
- **β ≈ 12.3** with world-day effects held fixed. The optimal pricing β given online uncertainty is ≈ 10–11 (win.json uses 7.84 → we overprice ~4%).

## Price war
- The lowest day effect is −0.12 to −0.33 log.
- **Detection:** LR test of a −0.20 shift, threshold log 99 → detects after a median of 10 quotes (by ~09:20); 8% false triggers.
- **Our current behaviour:** we follow it down (wins 23–33%); **after 18:00 we win 84–90%** and the **next morning 71–78%**, i.e. we underprice.
- **Best response:** shift only −0.05 to −0.08, freeze learning, restore at 18:00 and the next morning.

## Outages
- Visible (shift +0.15 to +0.24), but online detection only works in big regions (≥30 quotes/day). Small upside.

## Day level
- No reliable weekday pattern (sd 4–8%/day). Learn it each morning.
- A random short-vs-long reshape each day (tilt sd 3–9%).
- After 18:00 the competitor is +4–7%.

## Drivers
- Depth (viewers before booking) is 7–8 in metro towns. It rises from 4 at 09–11h to 9–12 at 15–17h.

| Opening fee / typical | Median wait | p75 wait | Depth |
|---|---|---|---|
| ≤ 0.9 | 5 min | 98 min | 6 |
| 1.0–1.1 | 2 min | 22 min | 3 |
| 1.1–1.25 | 1 min | 13 min | 2 |

- Drops are ~11% and barely fee-dependent.
- 92% of bookings happen at the opening fee. **There is no evidence that econ taught drivers to wait** (the old smart ladder did, mildly).

## Ranked changes
1. War v2 (shift −0.06, freeze, restore) +€300–500
2. Stackelberg shadow cost adapt_k €6–8 × mornings left (big dealers) +€300–700
3. Split world level vs a daily level reset +€200–400
4. β 10.5 +€150–300
5. Opening fee 0.85 on deep metro gigs 09–17 (hold 20 min) +€300–500
6. Outage mode for big regions +€100–250
