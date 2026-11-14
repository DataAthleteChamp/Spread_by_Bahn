# Industry analogues: what to steal (research wave 3B)

[mem] = unverified.

## Mapping: who has our problem

| Spread sub-problem | Same problem in industry | Their method |
|---|---|---|
| Quote vs a hidden competitor, win/lose only | **Ad-tech first-price bid shading**; **TAC SCM** customer RFQs; freight instant quotes | Censored win-rate model + argmax (v − b)·W(b) |
| Win only what capacity can deliver | **TAC SCM** factory capacity; airline RM | Greedy "profit per scarce unit", phantom future demand, bid prices |
| Hire a driver before the deadline | **Uber Freight** carrier pricing; **Amazon Flex** block surge; nurse shift platforms | Backward-induction MDP from a terminal cost; monotone P(book) |
| Drivers wait for raises | **Amazon Flex "wait for the surge"** | Open near the clearing price; few, unpredictable steps |
| Where the driver ends up matters | **DiDi** value-function dispatch; carsharing **jockeys** | Edge weight = r + V(dest) − V(origin); the return trip is the binding cost |
| Chaining cars | DoorDash batching; OR-Tools PDPTW | Batch matching every tick; insertion + local search |

---

## 1. TAC SCM: the closest analogue (sealed first-price reverse auction on customer RFQs, limited factory capacity)

### TacTex-06 (2006 winner)
https://www.cs.utexas.edu/~TacTex/dpardoe/papers/TacTexChapter.pdf

- **Winning-price distribution:** a Normal per product, tracked with a **particle filter** (100 particles, each a mean and variance). Each day the particles drift and are reweighted on observed wins and losses. P(win | b) = 1 − CDF.
- **Day factors (self-calibration):** multiply predicted P(win) by **actual wins ÷ expected wins** over recent offers, per segment. This keeps the order count on target.
- **Price-trend predictor:** regression trained on self-play games.
- **Bidding under capacity:**
  - Treat P(win) as winning a *fraction* of the order.
  - Add **phantom predicted future RFQs** for the next 10 days.
  - Start every bid at the reserve price.
  - Greedy loop: repeatedly take the RFQ and price cut with the **largest profit gain per unit of scarce resource**, and stop when nothing fits.
  - Result: very few late deliveries.

### CMieux (CMU)
https://www.site.uottawa.ca/~nelkadri/CSI5389/Papers/26-CMieux.pdf

- A regression "distribution tree" predicts a Normal winning-price distribution per RFQ.
- Bidding is a **continuous knapsack** `max Σ x·G⁻¹(x)` subject to capacity, solved exactly by binary search on the marginal value.

### Botticelli (Brown)
https://cs.brown.edu/people/amy/papers/botti.pdf

- Start with low bids, schedule production, and raise the bids that don't fit.
- **Sorting by profitability beat sorting by win probability.**

### Others
- DeepMaize: a Bayesian posterior over demand parameters.
- MinneTAC [mem]: **classifies regimes** (scarcity, balanced, glut) and prices per regime.

**Steal:** the TacTex loop, i.e. a competitor price model updated by wins and losses, the wins ÷ predicted calibration factor, phantom future requests, and greedy margin per scarce driver-hour.

## 2. Ride-hailing (Uber, Lyft, DiDi)

- **Batched matching** every few seconds (Hungarian / min-cost flow) instead of greedy nearest-driver. Uber: greedy waits "really added up". https://www.uber.com/at/de/marketplace/matching/
- **DiDi value-function dispatch:**
  - learn V(time, zone) by TD learning;
  - edge weight = `r + γ^Δt·V(dest) − V(origin)`;
  - Hungarian matching every 2 s.
  - CVNet: https://arxiv.org/abs/2106.04493. V1D3 won KDD Cup 2020: https://arxiv.org/abs/2105.08791
- **Surge** = f(open requests ÷ available drivers) per hex, smoothed [mem]. **Quests / Power Zones** incentives [mem].
- Lyft simulator: https://arxiv.org/pdf/2603.21531

**Steal:** value the end town of a driver, `V(end town) − V(home)`, and re-assign over all open jobs each tick.

## 3. Delivery and gig couriers

- **DoorDash DeepRed** (https://careersatdoordash.com/?p=5342):
  - offer generation → ML estimates (prep time, travel time, **acceptance probability**) → MIP;
  - batching;
  - ruin-and-recreate routing.
- **Amazon Flex:**
  - unclaimed blocks get **stepwise raises toward the start** ($72 → $84 → $96 → $108, from a third-party guide);
  - **drivers openly wait for the surge**. That is exactly our learning-driver problem.

**Steal:** P(accept | driver, fee) inside the optimiser; avoid predictable raise ladders.

## 4. Digital freight brokerage: Uber Freight carrier pricing MDP

https://www.uber.com/blog/freight-markov

- Each load is perishable. At each lead time, choose the posted price.
- P(book | p, state, lead time) comes from a **monotone-constrained XGBoost** model.
- **Backward Bellman recursion from a terminal fallback cost** (manual coverage, or a relationship penalty).
- Censored data handling, UCB exploration, and a **PID controller on booking speed**.
- Shipper side (Convoy, Transfix, Loadsmart): predicted carrier cost + markup from a win-probability curve [mem].

**Steal:** compute our fee schedule by backward induction from the deadline. Terminal cost = an expensive direct offer, or the late penalty.

## 5. Ad-tech bid shading (= our quote)

- **Verizon Media WR** (https://arxiv.org/abs/2009.09259):
  - a logistic win-rate model W(b) learned from win/lose only;
  - `b* = argmax (v − b)·W(b)`;
  - cost about 55% of unshaded bids, +4.3% surplus.
- Censored-likelihood ML: https://pdf.arxiv.org/pdf/2009.01360
- Deep distribution network: https://arxiv.org/abs/2107.06650
- **Recipe:**
  - censored likelihood (win → competitor > q, loss → competitor < q);
  - log-normal or logistic per segment;
  - maximise expected surplus;
  - small exploration.

## 6. Revenue management and relocation

- **EMSR-b** protection levels; **bid-price control** (accept if revenue ≥ Σ shadow prices); overbooking newsvendor [mem].
- **Carsharing jockeys:**
  - Bruglieri et al., operators on folding bikes: https://arxiv.org/pdf/1504.02163
  - NSGA-II over relocation: https://doaj.org/article/55747a308846437cad760852602c1746
  - Jorge, Correia & Barnhart: https://dspace.mit.edu/handle/1721.1/112401
  - **The jockey's trip back is the binding cost.** Same as our driver's ticket home.

## 7. OR-Tools routing

- First solution: cheapest arc, parallel cheapest insertion, or savings. Then local search with **Guided Local Search** (it needs a time limit).
- PDPTW via `AddPickupAndDelivery` + a time dimension.
- 1–10 s for hundreds of nodes [mem].

**Use:** only for multi-car chains. Cheapest insertion live; plain assignment is otherwise enough.

---

## Top 8 transferable ideas (impact ÷ effort)
1. **Censored win-probability model + surplus maximisation** for quotes (bid shading, TacTex, CMieux).
2. **Rolling calibration factor:** actual wins ÷ predicted wins per segment (TacTex). About 10 lines.
3. **Bid price for driver capacity** λ(town, day), with phantom future demand (TacTex, RM).
4. **Backward-induction fee schedule** from a terminal cost, with a monotone P(book) (Uber Freight) + PID on time-to-fill.
5. **Raise schedules that can't be gamed:** open near clearing, few steps, direct offers (Amazon Flex failure mode).
6. **Chance-constrained on-time:** quote only if P90(hire delay + travel) fits; aim for 93–95% internally.
7. **Batched assignment with value-function weights** (Uber, Lyft, DiDi): V(end town).
8. **Self-play simulation for tuning** across behaviour models (TacTex, Lyft).
