# Spread: research notes

- Part A: Bahn Express and the industry (pending, wave 1 agent)
- Part B: algorithm literature survey

The game mechanics themselves are in `docs/` and summarised in `ALGORITHMS.md`.

---

## Part A: Bahn Express and the car-transport industry

**No company publishes its dispatch or pricing algorithms.** What we know publicly is business models, how drivers are paid, and companies' own claims.

### A1. Bahn Express (the challenge partner)

| | |
|---|---|
| Legal entity | OY Bahn Express AB, Business ID 3414813-4, Helsinki |
| Founded | 2024, by Matias Blomberg (CEO) and Leevi Jäkälä (CTO) |
| Funding | €920k pre-seed (H2 2024); **€5M seed, Dec 2025**, led by node.vc with Trind VC and Innovestor. Angels include Wolt's CPO and founders of Swappie and Smartly |
| Size | ~30 staff; offices in Copenhagen and Berlin |
| Markets | FI, SE→FI, DE→FI (2024), DK (2025), DE team (2025) |
| Customers | Kamux, Aampere, Autohuset Vestergaard; claims 100–400+ dealers and 15k+ deliveries/yr (self-reported; figures inconsistent) |
| Product | Dealer portal, API, email or Excel booking; live tracking; inspection photos; digital CMR. "Bahn Driver" app. Also a "Fill your trucks" carrier side |
| Claims | 86% of branch transfers moved within a day; 98% of domestic orders arrive within 2 days; insurance up to €100k per car |

**Pricing to dealers.** "Fixed and confirmed when you order, no auctions or surcharges." No public price list. This matches the game's quote-then-commit model.

**Drivers**
- Freelancers paid via Truster (3.5% fee). The default shown is **€50 per domestic gig**, paid weekly. Drivers choose gigs freely in the app.
- **Domestic return trips are not reimbursed. Bahn chains gigs instead**, so the driver gets a return car or a bundled return gig. This is exactly the game's mechanic: the cost of public transport home is the driver's problem, and chains make gigs cheap.
- Cross-border gigs pay for the return trip, hotels and fuel.
- A rising fee schedule, bonuses or a dispatch algorithm is **not** described publicly. These seem specific to the simulation, or internal to Bahn.

**Takeaway.** The game is a model of Bahn's real operation: a fixed quote to the dealer, then a gig marketplace where drivers choose, where chaining matters most. The jury likely values ideas they can use for real, e.g. chaining, reading notes, and how they treat drivers.

### A2. Competitors and comparable companies

| Company | Market | Model | Pricing / pay | Matching / dispatch |
|---|---|---|---|---|
| **Flovi** (formerly Biila) | FI (incumbent), SE, PL | Managed driver network; ~€12M revenue, 100k+ transfers/yr, average 22 h delivery in FI | Instant price to the customer; driver pay not published | "AI optimisation" cuts empty trips; near-real-time assignment; drivers set city/route alerts; **most active drivers get priority on good gigs** |
| **ONLOGIST** | DE/EU | Marketplace; 10k+ "Carmovers", 400k+ transfers in 2024 | The client sets an offer price; **drivers can propose their own price** (bidding) | Drivers choose; "smart route planning" |
| **Hiflow** | FR | Private driver / pro convoyeur / truck | Not published | Not published |
| **HopDrive** | US, short local dealer moves | Portal + DMS integration, GPS | Not published | Real-time notifications for nearby moves; **free rideshare back is booked automatically when no return move exists** |
| **RunBuggy** | US marketplace | Sets central prices for shippers and drivers | "Torque" AI pricing (weather, traffic, history) | Order weighting; driver ratings (ETA accuracy, inspections, **penalty for un-claiming**); top drivers get premium orders; order pooling |
| Team DriveAway / ATC | US long-haul | Per-mile | ~$0.55–1.55/mile; return often unpaid | — |

### A3. What this means for our design
1. **Chaining and return legs are the core of the real business** (Bahn, Flovi's "empty trips", HopDrive's return rides). Our design should treat where drivers finish as supply.
2. **Driver quality and reliability tiers** (RunBuggy, Flovi): in the game, the roster shows rating, completed gigs and drops. Use it to prefer reliable drivers for direct offers.
3. **Fixed dealer prices with dynamic driver pay** is the real-world split, and it is exactly the game's structure.
4. No public algorithm to copy, so there is room for a **creative** idea, which the jury rewards.

### Sources (Part A)
1. https://www.bahnexpress.com/
2. https://news.cision.com/san-francisco-oy/r/bahn-express-raises--5m-to-rapidly-scale-its-automotive-logistics-platform-across-europe,c4282838
3. https://www.bahnexpress.fi/careers
4. https://www.bahnexpress.fi/about
5. https://www.bahnexpress.de/agb
6. https://www.bahnexpress.fi/drivers
7. https://techfundingnews.com/bahn-express-raises-5m-europe-car-logistics/
8. https://tech.eu/2025/10/02/finnish-car-logistics-pioneer-flovi-rolls-into-poland/
9. https://www.verkkouutiset.fi/a/suomalaisyritys-siirtaa-yli-100000-autoa-vuodessa-nyt-kohti-keski-eurooppaa/
10. https://antyweb.pl/jezdzisz-cudzym-autem-i-zarabiasz-szukaja-kierowcow-w-calej-polsce
11. https://www.autohaus.de/nachrichten/autohandel/fahrzeugtransport-onlogist-mit-neuer-doppelstrategie-3719742
12. https://www.onlogist.com/en/vehicletransfer-app
13. https://www.hopdrive.com/driver-overview
14. https://autoremarketing.com/?p=62273
15. https://runbuggy.com/data-science-to-improve-the-runbuggy-digital-marketplace/

---

## Part B: algorithm literature survey

### B1. Quoting against an unknown, adapting competitor (binary win/lose feedback)

**The problem.** Each quote is a first-price sealed-bid procurement auction with censored feedback: a loss only tells us the competitor was cheaper than our quote.

**Approach.**
- Model P(win | r = quote/list, context) with a logistic or survival curve.
- Pick the r that maximises P(win) · (price − cost − opportunity cost).
- Thompson sampling gives exploration. A discount or sliding window lets the model track a non-stationary competitor.

**Evidence from freight.** Carriers bid from their own cost plus a distribution of the lowest competing bid. In one study, human bidders earned about 35% less profit than optimisation models.

**Refs**
- Ferreira, Simchi-Levi & Wang (2018), *Online Network RM using Thompson Sampling*, Operations Research.
- Han et al., *Optimal No-regret Learning in Repeated First-price Auctions*, arXiv 2003.09795.
- *Learning to Bid in Non-Stationary Repeated First-Price Auctions*, arXiv 2501.13358.
- Kuyzu et al. (2015), TR-B 73.
- MDPI *Logistics* 8(3):72.
- Yuan/Powell, arXiv 1802.08976.
- Dynamic Pricing Challenge, arXiv 1804.03219.

**For us**
- Bayesian logistic on log(quote/list). Features: option, lane/region, number of legs, dealer offset (hierarchical), trust, day.
- Refit with a Laplace approximation every few minutes.
- Thompson sampling over r ∈ [0.8, 1.8]. Discount old data with γ≈0.97 per order, or use a 1–2 day window.
- CUSUM on the win rate by day and region. When it fires, widen the posterior: this catches the **price war** and the **outage** (raise toward about 1.3×).
- Cap the per-dealer win rate at about 50–60% so the competitor doesn't cut its prices for that dealer.
- Protect trust: never take an order from a high-trust dealer if it might arrive late.

### B2. Accepting orders when capacity is scarce

**The idea.** Revenue management with **bid-price control**: accept an order only if its margin is greater than the shadow price of the driver capacity it uses.
- Bid prices come from the dual values of an LP over forecast demand. They are asymptotically optimal when set well.
- The 90% on-time rule is a chance constraint. Handle it with a Lagrangian penalty and a safety buffer.

**Refs**
- Talluri & van Ryzin (1998), Management Science 44(11).
- Slotnick (2011), *Order Acceptance and Scheduling*, EJOR 212.

**For us**
- Capacity ledger per region and day: expected driver-hours minus committed hours.
- λ(region, day) = expected fee for one more order at the current tightness + penalty · P(late).
- Quote cost = F̂ + λ. Prices then rise naturally when capacity is tight.
- **SLA guard.** If the Wilson lower bound of the projected on-time rate falls below 92%, raise λ sharply or stop quoting same_day.
- Prefer `within_3_days` when unsure: the slack makes chaining possible.

### B3. Driver fees with strategic, learning drivers

**The idea.** We are a buyer posting a rising price to strategic sellers. This is a **reversed Coase / durable-goods problem**: if fees always rise, drivers wait, and we end up paying the top of the schedule.
- With patient strategic agents, the optimal policy is **cyclic** or randomised, not monotone (Besbes & Lobel).
- Crowdshipping papers model acceptance as logistic in (compensation − detour cost).
- Surge economics: underpaying when supply is thin leads to long deadheads ("wild goose chase") and drivers dropping out.

**Refs**
- Barbosa, Pedroso & Viana (2023), C&OR.
- arXiv 2305.01317.
- Besbes & Lobel (2015), Management Science 61(1).
- Hörner & Samuelson.
- Castillo, Knoepfle & Weyl, *Surge Pricing Solves the Wild Goose Chase*.

**For us**
- Reservation-fee estimate per driver = drive time + public transport to the pickup + ticket home, from their home town, plus a learned outside-option offset.
- A **view without a booking** means the fee was below that driver's reservation fee. Use it as censored data.
- **Direct offers** for critical gigs: take-it-or-leave-it to the 1–3 cheapest feasible drivers at cost + a margin. The margin must be big enough to avoid drops. Offers don't teach drivers to wait for raises.
- Open posts:
  - Open near the clearing fee and use few steps.
  - Randomise the shape across gigs: flat, late jump, or early full price.
  - Sometimes hold the fee flat and fall back on a direct offer.
- Pay a premium on gigs with a deadline today: a late order costs far more than the overpayment.

### B4. Dispatch and routing

**The idea.** A dynamic pickup-and-delivery problem (PDPTW) with chaining.
- Practice: **rolling-horizon re-optimisation**, with insertion plus local search (ALNS). Commit only near-term actions.
- Anticipation: cost-function approximations (e.g. a bonus for ending near future demand) or rollouts.

**Refs**
- Hildebrandt, Thomas & Ulmer, arXiv 2103.00507.
- Ulmer (2017), *ADP for Dynamic Vehicle Routing*.
- Ropke & Pisinger (2006), ALNS for PDPTW.

**For us**
- Greedy chain builder every 15–30 min, earliest deadline first. Add a leg to an existing chain if:
  - its last drop-off is near the leg's pickup (backhaul / trade-in),
  - the chain stays at ≤12 h of driving,
  - every deadline still holds with about 20% buffer.
  Otherwise start a new gig.
- Score each chain by fee saved per extra hour.
- Where our drivers finish counts as supply.
- Never re-plan a booked gig.

### B5. Simulation-based optimisation (the forkable, deterministic simulator)

- **Rollout (Bertsekas):** for each candidate decision, fork the world, run the base policy forward H hours, and pick the best. It reliably improves on the base policy.
  - Note: fork uses one of our 8 practice slots and is closed in the final. So rollout is a **research tool**, not something we can use live.
- **Policy search:** CMA-ES, cross-entropy or random search over 5–10 knobs:
  - price multiplier,
  - λ scale,
  - fee opening ratio,
  - schedule shape,
  - SLA buffer.
- Score each setting on the **same seeds** (common random numbers) and include stress seeds.
- **Refs:** Ulmer (2017); Bertsekas, *Rollout, Policy Iteration, and Distributed RL* (2020); Soeffker, Ulmer & Mattfeld (2021), EJOR.

### Suggested split for three people

| Person | Area | Work |
|---|---|---|
| A | Pricing | Logistic win model, Thompson sampling, discounting, change detection |
| B | Capacity and fees | Capacity ledger, bid prices, driver cost model, direct offers, fee schedules |
| C | Dispatch and tuning | Chain builder, simulation harness, parameter tuning |

### Sources (Part B)
- https://dspace.mit.edu/handle/1721.1/125757
- https://arxiv.org/pdf/2003.09795
- https://arxiv.org/pdf/2501.13358
- https://arxiv.org/pdf/2109.03173
- https://arxiv.org/pdf/1802.08976
- https://faculty.washington.edu/yingfei/truckload_bidding.pdf
- https://mdpi.com/2305-6290/8/3/72
- https://ideas.repec.org/a/eee/transb/v73y2015icp34-58.html
- https://drum.lib.umd.edu/bitstream/handle/1903/1432/umi-umd-1475.pdf
- https://ar5iv.arxiv.org/html/1804.03219
- https://pubsonline.informs.org/doi/10.1287/mnsc.44.11.1577
- https://ideas.repec.org/a/eee/ejores/v212y2011i1p1-11.html
- https://www.econbiz.de/Record/a-data-driven-compensation-scheme-for-last-mile-delivery-with-crowdsourcing-barbosa-miguel/10013485775
- https://arxiv.org/html/2305.01317v5
- https://pages.stern.nyu.edu/~ilobel/Intertemporal%20Price%20Discrimination.pdf
- https://www.game.kier.kyoto-u.ac.jp/2009/090820Horner.pdf
- https://www.uber.com/blog/research/surge-pricing-solves-the-wild-goose-chase
- https://arxiv.org/pdf/2103.00507.pdf
- https://link.springer.com/978-3-319-55511-9

Cited from memory, not checked online: Ropke & Pisinger (2006), Bertsekas (2020), Garivier & Moulines (discounted UCB, arXiv 0805.3415).

---

## Part C: Deep dive (wave 2), formulas we can implement

Tags: [mem] = cited from memory, not checked online. The formulas were derived by the research agent; the binomial and power numbers were computed with scipy.

### C1. Learning the competitor's price from win/loss (censored probit)

**Model**
- Competitor's log price: `log q = log list + a_lane + b_day + w_world + d_dealer,t + ε`, with `ε ~ N(0, σ²)`.
- `P(win | p) = Φ((xᵀθ − log p)/σ)`.
- Fit it as an ordinary GLM, `y ~ Φ(αᵀx − γ·log p)`. Then `θ = α/γ` and `σ = 1/γ`, so we also get the **steepness of the dealer's curve**.
- Add the option kind as a feature: the dealer's speed value shows up as an offset per option.

**Data budget**
- Each observation is most informative near P = 0.5: Fisher information ≈ 0.64/σ².
- With σ = 0.05, 100 observations pin a shared offset to about ±0.6%. **The world level and the day factor are learned within hours.** The lane × dealer terms are where data runs short.

**Hierarchical lanes**
- Prior `a_lane ~ N(ā_lane_const, τ²)`. Learn **ā_lane_const offline by pooling practice worlds** (that part of the lane factor is the same in every world). Online, learn only each world's deviation.
- In practice: an L2-penalised GLM whose offset is the prior mean.

**Making it robust**
- Dealer offsets with forgetting (half-life of a few days), or regress `d_dealer` on our lagged win share at that dealer.
- CUSUM on daily residuals:
  - **price war**: shift −0.22 everywhere;
  - **outage**: shift +0.26 in the region.
- Add ±2–3% price jitter so we keep learning; greedy MLE alone can get stuck (Broder & Rusmevichientong). The closest practical template is Javanmard & Nazerzadeh's RMLP.

**Refs**
- Javanmard & Nazerzadeh: https://arxiv.org/abs/1609.07574
- Broder & Rusmevichientong 2012: https://ideas.repec.org/a/inm/oropre/v60y2012i4p965-980.html
- Cohen, Lobel & Paes Leme: https://pages.stern.nyu.edu/~ilobel/Ellipsoids-sigecom.pdf
- Kleinberg & Leighton: https://www.cs.cornell.edu/~rdk/papers/oppa.pdf

### C2. Optimal markup

**Formulas** (logistic curve `P = 1/(1+e^{β(p−θ)})`)
- First-order condition: **`p − c = 1/(β(1 − P(p)))`**.
- Closed form: `p* = c + [1 + W(e^{β(θ−c)−1})]/β`, where W is the Lambert W function.
- In practice: a 1-D golden-section search per request on the **posterior-predictive** curve `Φ((θ̂ − log p)/√(σ² + s²))`. Uncertainty flattens the curve, so the markup goes up.

**The full objective per request**
```
p* = argmax_p (p − c − λ_town,day − μ_dealer + V_trust) · P̃(p)
```

| Term | Meaning |
|---|---|
| `c` | Expected driver fee |
| `λ` | Bid price (shadow cost) of driver capacity in the pickup town and day |
| `μ_d` | Penalty for winning too much from one dealer. Update: `μ_d ← [μ_d + η(ŵ_d − X)]⁺` |
| `V_trust` | `≈ 0.01 × future revenue from this dealer until the cap × P(on time)`. It is 0 once the dealer is at the cap |

### C3. Paying strategic drivers

**Theory**
- **Coase conjecture** [mem]: if you cannot commit and you raise often, you end up paying the top of your schedule.
- **Commitment** (Stokey [mem]): a **constant price is optimal** when sellers are patient.
- The shortage makes this worse. Drivers rarely fear that another driver will grab the gig, so waiting costs them little (Liu & van Ryzin [mem]).
- A driver's value of waiting ≈ `(r̄_j − 1)·fee·P(still open)`, where `r̄_j` is that driver's mean booked/first-viewed ratio. **We control r̄ directly.**

**Practical recommendation**
1. Post the right fee first, from the cost model.
2. Make **public raises rare, late and few**, so r̄ stays ≈ 1.0.
3. **Don't randomise raises.** They keep the expected raise above zero.
4. Make urgent top-ups through **direct offers**, not public raises. (To check: does an offer booking change drivers' beliefs? Test it in practice.)

**Sequential offers (Chawla et al.)**
- DP over candidates: `W_i = max_f [F_i(f)(V − f) + (1 − F_i(f))·W_{i+1}]`.
- The optimal fee satisfies `V − f − W_{i+1} = F_i(f)/F_i′(f)`.

**Refs**
- Board & Skrzypacz (JPE 2016): https://web.stanford.edu/~skrz/dynamic_auction.pdf
- Chawla et al.: https://arxiv.org/abs/0907.2435

### C4. Driver costs and choosing whom to offer

**Structural cost**
- `c_jo` = drive time + transit to the pickup + ticket home + extras (evening, weekend).
- Driver j's net reservation is `R_j` = outside option + waiting premium.

**Learning R_j from views**
Each `gig_viewed` event at fee f gives one observation:

| What happened | What we learn |
|---|---|
| The driver booked | `R_j < f − c` |
| The driver viewed, didn't book, and the gig stayed open | `R_j ≥ f − c` |
| Someone else took the gig | Nothing |

- Keep a grid posterior per driver (~50 points), with prior `R_j ~ N(μ_town, τ²)`.
- Views also tell us **which drivers are active today**.
- Drops: `logit P(drop) = a − b·(f − c)/c`.

**Pandora's box (Weitzman 1979) for direct offers**
- Index per driver: **`z_i = max_f [V − f − k_i/F_i(f)]`**, where `F_i(f) = P(R_i < f − c_io)`.
- `k_i` = the cost of one offer: 10 minutes of deadline time plus the shadow price of one of the driver's 3 daily offers.
- Send offers in descending `z_i`. Stop when public posting beats every remaining `z_i`.
- Ref: https://scholar.harvard.edu/sites/scholar.harvard.edu/files/weitzman/files/optimalsearchbestalternative.pdf

### C5. The 90% rule (n ≈ 350 orders; we need ≥315 on time)

| True on-time rate | 0.90 | 0.91 | 0.92 | 0.93 | 0.94 | 0.95 |
|---|---|---|---|---|---|---|
| P(ranked) | 0.545 | 0.776 | 0.926 | 0.986 | 0.999 | ~1 |
| 5th-percentile realised share | 87.4% | 88.3% | 89.4% | 90.6% | 91.7% | 93.1% |

- **Lateness clusters** (bad days, bad towns), which inflates the variance by about 1.45×. At a 93% plan, P(ranked) drops to about 0.97.
- → **Plan for 93–94% (95% for the final).**
- Run a sequential controller: `buffer = on_time − 0.9 × accepted`. When the buffer is thin, raise prices and use direct offers. When it is comfortable, take margin.
- Hoeffding and Bernstein bounds are too loose to use; use the exact binomial or our own empirical distribution across weeks.
- Ref: Brown, Cai & DasGupta 2001: https://projecteuclid.org/euclid.ss/1009213286

### C6. Policy search on the deterministic simulator

**Seeds needed** to detect a +€500/week improvement (σ = €1500, α = 0.05, power 80%), with paired seeds:

| Correlation between variants on the same seed | 0 (unpaired) | 0.5 | 0.8 | 0.9 | 0.95 |
|---|---|---|---|---|---|
| Seeds per arm | 141 | 71 | 28 | 14 | 7 |

- **Measure the correlation first.** It is likely ≥0.8, so about 15–30 seeds is enough.
- Budget: 8 workers × ~1.5 s per week ≈ 19k weeks/hour on a quiet server. That favours **CMA-ES** (population 10–12, log-scaled parameters). TPE is better below ~200 evaluations or with categorical parameters.
- Rules:
  - Use the same seeds within a generation and rotate them between generations.
  - Prune early with successive halving (4 → 16 → 64 seeds).
  - Re-test the top 3–5 on 100+ **held-out** seeds to correct the winner's curse.
- Ref: Hansen's CMA-ES tutorial, https://arxiv.org/abs/1604.00772

### C7. Should we build a local "digital twin"?

- **Not a full twin for policy search.** The real simulator is fast, parallel, forkable and exact. A twin adds bias, policies exploit its errors, and the errors compound over long rollouts (Janner et al. MBPO, https://arxiv.org/abs/1906.08253).
- **Do build component models.** The final can't be forked, so we need them online anyway:
  - competitor probit,
  - driver reservation and drop model,
  - town supply forecast.
  Validate them against practice logs with calibration plots, and use them for short-horizon lookahead.
- **Metamodels over policy parameters** (Kleijnen, EJOR 2017) show sensitivities cheaply: https://econpapers.repec.org/RePEc:eee:ejores:v:256:y:2017:i:1:p:1-16
