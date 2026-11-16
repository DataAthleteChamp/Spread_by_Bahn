# Presentation sources and claim boundaries

Public sources checked on **15 November 2026**. Company statements below are
self-reported, not measurements made by our team.

## Company and challenge

| ID | Primary source | What it supports |
|---|---|---|
| S1 | [Bahn home](https://www.bahnexpress.com/) and [about](https://www.bahnexpress.com/about) | Fixed upfront prices/ETAs, dealer and fleet use cases, portal/API ordering, photos and delivery documents; operations in Finland, Denmark and Germany. The company also mentions truck transport. |
| S2 | [Bahn drivers](https://www.bahnexpress.com/drivers) | Drivers choose app offers with route and pay visible; pickup photos and completion/payment workflow. The page advertises 5K+ registered drivers and 25 collection countries, not 5K active drivers at any moment. |
| S3 | [Bahn's Kamux case study](https://www.bahnexpress.com/stories/kamux) | A customer account of imports changing from about two weeks to about three days from Sweden and five from Germany. This is a testimonial, not a controlled study or an effect of our system. |
| S4 | [Spread rules](https://spread.bahnexpress.com/kit/RULES.md) and [API](https://spread.bahnexpress.com/kit/API.md) | Ledger scoring, per-week 90% qualification, isolated scenario copies, hidden competitor/driver values, events and rate limits. |
| S5 | [Judging requirements](https://spread.bahnexpress.com/judging) | 5-10 slides; idea/why/effect; matched-week margin and on-time comparisons; final and ranking results; limitations. |

**A source discrepancy was not papered over:** the home page advertises 400+
dealerships and brokers; the about page says more than 100 dealerships. The
definitions or update dates may differ. The slides do not assert one precise
active-customer count. Similarly, route-specific transit claims vary across
pages and case studies; none is presented as a universal SLA.

## Technical research for the proposed roadmap

| ID | Primary source | Use and limitation |
|---|---|---|
| R1 | [Ma, Fang & Parkes: Spatio-Temporal Pricing for Ridesharing Platforms](https://arxiv.org/abs/1801.04015) | Motivates capacity value by location and time. Its complete-information mechanism and equilibrium guarantees do not transfer directly to our uncertain, voluntary-driver simulator or to a production deployment. |
| R2 | [Romano, Patterson & Candes: Conformalized Quantile Regression](https://arxiv.org/abs/1905.03222), [full text](https://arxiv.org/html/1905.03222v1) | Motivates calibrated delivery-time intervals. Standard coverage relies on exchangeability; marginal prediction-interval coverage is not a guarantee of 90% weekly on-time delivery, especially under temporal or regional shift. |

These are **future design references**, not algorithms claimed to have been
deployed in FINAL. No company operational data was used to train new models for
this presentation.

## Reproducible project evidence

`submission/build_evidence.py` derives `submission/evidence.json` from recorded
worlds. It does not fit models, create worlds or send game actions.

| ID | Data/code | Claim |
|---|---|---|
| E1 | `sweep40`, `lab/policies/econ.py` | Soft risk-priced admission vs the hard risk gate, on 24 matched development weeks. |
| E2 | `sweep40`, `lab/fit_hazard.py`, `lab/models/hazard.json`, `lab/policies/smart.py` | Booking/drop fee-DP ablation on the same 24 weeks. Serving uses a compressed lookup table, not a full online solve for every gig. Standalone effects are not additive. |
| E3 | `c14val`, `lab/fit_ref.py`, `lab/models/ref.json` | Fee denoising on 53 matched weeks, with the 40 new weeks reported separately from 13 stress cases. |
| E4 | `dil2`, `lab/policies/econ.py` | Safe-win bonus: 63 complete pairs plus the named c15-25 example. One baseline server failure is excluded from paired means. |
| E5 | `ratio1`, `struct1`, `results/ratio1_economics.json` | Higher-volume and pairing ideas that were not promoted; accounting effects are not an oracle for independent counterfactual gains. |
| E6 | `results/final-outcome.json`, `POSTMORTEM.md`, `results/quote_audit-final0100.json`, `results/submission-report.json` | Actual zero-order final outcome, availability incident, separate 01:00 rehearsal and best recorded fully qualifying five-week ranking round. |
| E7 | `results/runs.jsonl`, frozen model JSON files, `docs/API.md` | Recorded simulation/model sizes and API limits, not measured production throughput. Reused seed labels and gig exposure rows are not independent examples. |

Margin is the simulator's settled ledger contribution, not Bahn's corporate
profit. On-time values in comparison tables are **unweighted means over the same
paired weeks**. Confidence intervals use 50,000 whole-week paired bootstrap
samples; they are not multiple-testing-adjusted production guarantees.

Historical ablations have parameter/seed records but do not all have per-run
code/model fingerprints. The newer campaigns and current live deployment record
those identities. The reference-fee model lacks a complete training-world
manifest; provenance should be strengthened before a production ML rollout.

The real final ended with zero quotes/orders and no rank. Its official record
is archived separately from the rehearsal and research results. The local host
sleep/network timeline is documented in `POSTMORTEM.md`; full host logs remain
local. Review every slide and speaker note before sharing.
