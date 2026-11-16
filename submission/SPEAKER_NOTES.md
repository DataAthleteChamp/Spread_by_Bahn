# Speaker notes

Review every claim before presenting. Source IDs resolve in [SOURCES.md](SOURCES.md).

## 1. ML-guided dispatch: profit with a delivery constraint

Open with the measured answer. Use the real-final card only after checking the settled result against the official leaderboard; never replace a pending result with a rehearsal number. Best recorded ranking round is board6: EUR77,245.49 over five distinct weeks, 2,016 won orders, each week at least 95% on time. The 01:00 rehearsal earned EUR9,725.15 on 319 orders, 96.238% on time. These are ledger margins in the simulator, not Bahn's corporate profit. We are not claiming top-10 placement. The actual official final ended with EUR0, zero orders and all 1,034 requests unquoted. The local Mac entered clamshell sleep at 06:23 Helsinki and logged network/DNS failures through the 09:00-09:34 final. The runner never joined; this was an availability failure, not a measured strategy result. With zero orders, on-time is undefined, not a meaningful 100%. See POSTMORTEM.md and results/final-outcome.json. Restarting cannot replay the ended final.

Sources: E6.

## 2. Bahn sells delivery speed and certainty

Sources S1-S3 were checked on 15 November 2026. Bahn, formerly Bahn Express, describes direct car delivery and also truck transport. Domestic operations are described in Finland, Denmark and Germany. Its driver page advertises 5K+ registered drivers and 25 collection countries; registration is not active supply. The Kamux case is a company-published testimonial, not a controlled comparison or a result of our code. The homepage says 400+ dealerships/brokers and the about page says 100+ dealerships, so we avoid one precise customer-count claim. Proposed production work needs actual fuel, ferry, insurance and support costs, not just the simulator's driver-fee ledger.

Sources: S1, S2, S3.

## 3. Learn offline; decide quickly from live events

The deployed policy is a hybrid of statistical models and hand-coded operational rules, not an end-to-end neural agent. Its win model uses a lane prior and online week/dealer intercept updates. The fixed late-risk classifier has 17 features and 15,568 historical training orders. Hazard training used 686,245 exposure rows from 22,877 gig spells: exposure rows are not independent bookings. The fee prior contains 2,021 lane/private-status cells. The live process uses event streaming and compressed fee-table lookups; fitting and full DP construction happen offline. FINAL does not enable multi-order pairing and declines trade-in requests. The journal contains 7,110 completed L8 practice worlds over 823 reused seed labels, not that many independent validation draws.

Sources: E7, S4.

## 4. Price risk instead of only using a hard cutoff

This is a specific ablation, not a claim that the entire pricing model added EUR909. sweep40 compares CANDIDATE8's hard risk gate against mu_eur=25,risk_hard=0.6, on the same 24 development weeks (12 historical stress and 12 new). Existing route, deadline and feasibility checks remain. The online win model is sigmoid(beta*(week + dealer + lane + trust - log(quote/list))), with beta about 7.84. Its week and dealer offsets update from win/loss residuals. The quote grid contains 53 list-price multipliers. Paired margin 95% interval: EUR 541 to 1,294. The mean on-time share falls from 95.85% to 94.94%; both variants qualified on all 24 tested weeks. These development results are not a guarantee on an unseen final.

Sources: E1.

## 5. Pay for a retained booking, not a cheap first offer

The hazard model estimates a booking probability for a 10-minute exposure period. The DP also accounts for drop/re-hiring risk, terminal deadline cost and a penalty for teaching drivers to wait for raises. A driver who drops is not simply paid the completed-gig fee. Deployed schedules use a compressed table indexed by hours to lastPickupAt and home-driver coverage near pickup, with the hard-order premium retained. The rich fitted model is therefore not solved online for every gig. Adding haz=1 to CANDIDATE8 yielded a paired margin interval of EUR 185 to 635. Total driver fees did not necessarily decrease: better fills and fewer late outcomes can raise net margin. The combined pricing+fee change earned EUR 13,908/week on these weeks, so the two standalone uplifts must not be added together.

Sources: E2.

## 6. Denoise the typical fee before pricing the job

c14val compares historical FINAL13 against ref_w=0. The 53 matched weeks contain 40 new c14-* weeks plus 13 known stress weeks. Do not call all 53 unseen. Across all 53, mean margin rises from EUR13,523.28 to EUR13,809.70 and mean weekly on-time share from 95.44% to 96.07%; all weeks qualify. The all-53 margin interval is EUR 14 to 548. On the 40 new weeks alone, margin rises from EUR13,334.51 to EUR13,545.85 and on-time from 95.46% to 96.28%, but the margin interval crosses zero. This is directional evidence, not a conclusive fresh-only profit gain. The deployed ref_w=0 formula still retains per-request information through n/(n+4) shrinkage. The current model contains 83,145 reference observations and residual log-noise SD about 0.123. The legacy fit lacks a complete training-world manifest; better provenance belongs in the production roadmap.

Sources: E3.

## 7. Sometimes qualification costs immediate margin

The official condition is late_orders <= floor(0.1*noncancelled_won_orders), and every leg must be on time. The deployed safe-win bonus activates only when projected on-time is below 0.93, applies to predicted lateness below 0.05, tapers with risk and is capped at EUR20 per expected win. It is not a blanket price reduction. dil2 has 64 attempted seeds, but one baseline server failure leaves 63 complete pairs. In those pairs, mean margin delta is EUR -11.76; 95% interval EUR -48 to 13. Mean weekly on-time rises only 0.045 percentage points. The c15-25 example costs EUR1,004.01 to move from unqualified to qualified. It is one development case. The later c17-52 failure remains. Tighter note/private-appointment deadlines, late bookings and correlated regional shortages can break nominal-deadline or average-risk assumptions.

Sources: E4.

## 8. More fills did not mean more dependable profit

This row is ratio1 on its 24 fresh screening weeks, not the stress cases. The moderate credit won 452.17 orders/week versus 377.33, but net margin only rose EUR331.64 with an interval spanning zero and a new qualification failure. The larger credit was worse. The accounting decomposition on the same 24 pairs found EUR2,980.15 of added-order net, EUR2,005.36 lost on retained orders and EUR642.42 of displaced baseline net. It is an identity under two closed-loop policies, not proof the new orders can be gained independently. Drivers and the competitor react. Pairing in struct1 is a separate 24-week experiment; its point-estimate margin fell EUR125.01 and on-time fell 1.53 points. We therefore do not claim batching cars is a deployed gain. These results motivate cost-aware acquisition and better capacity forecasts, not indiscriminate undercutting.

Sources: E5.

## 9. Predict the operational outcomes that change decisions

These are proposed next steps, not completed features or measured production gains. First, use a survival or competing-risk model so unbooked/censored gigs and post-booking drops are handled explicitly. Fee-response estimates from observational data are confounded by job difficulty and policy decisions; safe controlled experiments are needed before interpreting effects causally. Second, predict delivery-time quantiles and calibrate intervals on later, held-out data. R2's standard conformal guarantee relies on exchangeability and is marginal, not a per-route or weekly-SLA guarantee. Third, learn execution contribution and capacity value by actual pickup time and region. R1 motivates spatio-temporal values but assumes complete information; its welfare/equilibrium guarantees do not transfer. Our failed static capacity surcharge is evidence against deploying a guessed penalty without better state estimation. Company integration requires permitted access to operational events; raw driver-location and customer data must be minimised and protected.

Sources: R1, R2, E7.

## 10. Scale the evidence before scaling the automation

The repository is a simulator prototype, not a proven production dispatcher. A production design should persist events and as-of features, keep action and model identities, coordinate shared-driver reservations and use one writer/idempotent action handling. Partitioning inference does not make driver capacity independent. Shadow evaluation precedes a limited pilot; consider region/time-clustered experiments because pricing changes affect other jobs and driver behaviour. Measure settled contribution per completed order, promise adherence, booking latency, drop rates and human interventions, including real operating costs. Require data access, retention rules and privacy/security review with Bahn. Monitoring should detect miscalibration and region/time shift, with bounded actions and rollback. No production ROI or top-10 guarantee is claimed. The actual final outcome and availability incident must remain distinct from rehearsal and practice evidence.

Sources: S1, S2, R1, R2.
