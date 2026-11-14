# Spread — by Bahn Express

**Event:** Junction 2026: European Tech Renaissance
**Partner:** [Bahn Express](https://www.bahnexpress.com/)
**Challenge page:** https://hackjunction.app/participate/45/challenges/349

---

## TL;DR

Run a simulated car-transport company in Finland for one week. Quote prices to dealers (against a competitor), win jobs, then post each drive as a gig to freelance drivers and pick the fee.

**Score = gross margin** = what dealers pay us − what we pay drivers.
**Hard constraint:** at least **90% of cars must arrive by their deadline**.

---

## The Business (real world)

- Bahn moves cars for **car dealers**.
- A **freelance driver** drives each car on its own wheels from A to B.
- Spread is a simulation of that work: a full week in Finland, with its dealers, cars, deadlines and drivers.

## What We Build

A system that runs the company for the week:

1. **Quoting (win the job).** A dealer asks us for a price and also asks a competitor.
   - Quote too high → we lose the car.
   - Quote too low → we win, but the margin is thin.
2. **Dispatch (get it driven).** Once we win a car, we post the drive as a **gig** in the drivers' app and **choose the fee**.
   - Fee too low → no driver takes it in time → the car arrives **late**.
   - Fee too high → the margin is gone.
3. **Stay above the 90% on-time rate** while maximising margin.

## Core Trade-offs

| Decision | Too low | Too high |
|---|---|---|
| Quote to dealer | Win, but little margin | Lose the car to the competitor |
| Fee to driver | No taker → late delivery → risk to the 90% SLA | Margin eaten |

---

## Getting Started

- **Join:** https://spread.bahnexpress.com/join
- **Event code:** `spread-kmu9z6`
- **Everything is on the site:** handbook, rules, API reference, TypeScript and Python kits, leaderboard
- **For AI agents:** https://spread.bahnexpress.com/llms.txt

---

## Timeline and Format

| When | What |
|---|---|
| **Fri 19:30** | Ranking rounds open. Every team plays the same secret weeks. The leaderboard shows standings. Bahn's own best system plays every round (the baseline to beat). |
| **Sun 07:30** | Registration for the final closes. |
| **Sun 08:00** | **Final.** Each team plays its own copy of one secret week, which runs autonomously for about **34 minutes**. |
| After the final | The **top 10 by margin** present to the jury. |

## Judging

- **Stage 1: margin.** The top 10 teams by margin qualify.
- **Stage 2: jury.** 5–10 slides or a short video. Criteria:
  - **Elegance**
  - **Clarity**
  - **Creativity**
  - **Robustness**
- Once you're in the top 10, **margin no longer counts**.

## Prizes

| Place | Prize |
|---|---|
| 1st | €2000 |
| 2nd | €1000 |
| 3rd | €500 |

---

## Support

- Visit the **Bahn booth**: ask about the rules, the world, real dispatch, or ask for a hint.
