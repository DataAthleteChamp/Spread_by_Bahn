# Spread

**Autonomous delivery dispatch, driven by probability and measured trade-offs.**

Built by **The Delusionals** for the [Bahn Express challenge](https://spread.bahnexpress.com/)
at Junction 2026. Spread prices car-delivery requests, recruits freelance drivers,
and manages execution while targeting profitable, on-time deliveries.

[Leaderboard](https://spread.bahnexpress.com/leaderboard) | [Quick start](#quick-start) | [How it works](#how-it-works) | [Results](#results) | [Documentation](#documentation)

## How it works

```text
Dealer request -> price and risk estimate -> quote -> recruit driver -> deliver
                         ^                                |
                         +------- learn from outcomes ----+
```

| Component | What it does |
|---|---|
| **Pricing** | Learns win probabilities online and chooses quotes by expected contribution, not order count alone. |
| **Recruitment** | Uses booking/drop models and dynamic programming to choose driver-fee schedules. |
| **Execution** | Handles readiness notes in Finnish, Swedish and English, charging rules, bookings and retries. |
| **Risk control** | Tracks projected delivery performance against the challenge's 90% on-time qualification threshold. |
| **Research lab** | Compares policies on paired weeks, separates stress cases from unseen seeds, and records uncertainty. |
| **Live operations** | Checks frozen model identities, prevents duplicate local runners and rebuilds state after disconnects. |

The simulator gives each team its own scenario copy. Competitor prices and
private driver costs stay hidden; our system learns from observable
outcomes. This repository contains the dispatcher and research tools, **not an
offline copy of the simulator**.

## Quick start

Requires **Python 3.14** (tested environment), macOS/Linux, and a Spread team key.
The competition has ended; starting the client cannot replay the completed final.

```sh
git clone https://github.com/DataAthleteChamp/Spread_by_Bahn.git
cd Spread_by_Bahn
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Set SPREAD_KEY in .env; never commit or share it.
.venv/bin/python -m lab.live FINAL --check
```

Preflight authenticates and verifies the frozen configuration without sending
game actions. Then choose **practice** or **live**, not both during a final:

```sh
# Four level-8 practice worlds.
.venv/bin/python -m lab.bench FINAL --level 8 --seeds 4 --workers 2

# Wait for the platform's next final announcement, then play it.
.venv/bin/python -u -m lab.live FINAL
```

`FINAL` is the frozen production policy. Experimental presets are not promoted
automatically. Run only one live actor per team and keep its code/models unchanged.
See the [operations guide](docs/OPERATIONS.md) for keep-awake, identity and recovery instructions.

## Results

| Recorded evidence | Result |
|---|---|
| Official final | **EUR0; 0 orders; not ranked.** All 1,034 requests were unquoted during a host sleep/network outage. |
| 01:00 live rehearsal | **EUR9,725.15** margin; **319 orders**; **96.24%** on time |
| Best recorded qualifying ranking round | **EUR77,245.49** over five weeks; each week **at least 95%** on time |
| Latest three experimental screens | **396 level-8 practice runs**; no candidate justified replacing `FINAL` |

The official-final failure was operational: the local execution host slept and
could not stay connected. The policy was not evaluated through submitted quotes
in that final. Rehearsal and practice results must not be substituted for it.
[Final postmortem](POSTMORTEM.md) | [Official outcome](results/final-outcome.json) |
[Experiment journal](EXPERIMENTS.md) | [Reproducible evidence](results/submission-report.json)

## Documentation

| Location | Contents |
|---|---|
| [`lab/`](lab/README.md) | Policy development, benchmarks and analysis commands |
| [`lab/policies/`](lab/policies/) / [`lab/models/`](lab/models/) | Dispatch strategies and saved models |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Live deployment, monitoring and recovery |
| [`results/`](results/) | Recorded runs, manifests and comparisons |
| [`SUBMISSION.md`](SUBMISSION.md) / [`submission/`](submission/README.md) | Submission checklist, ten-slide PDF/PowerPoint and source notes |

## Development and release

Add policies as `Desk` subclasses and register them in `lab/policies/__init__.py`.
Include reproducible paired comparisons, unseen-week results and qualification
failures with proposed changes. Keep credentials and local runtime state out of Git.

**Public research repository:** no open-source license has been selected.
Public visibility alone does not grant reuse rights for the code or bundled
challenge materials.
