# lab: parallel test bench for Spread algorithms

Runs policy variants × seeds on **practice** worlds in parallel and compares them **paired on the same seeds**.
It never creates ranking runs, so nothing here is a submission.

## Setup (once per machine)
```sh
uv venv .venv  # or: python3 -m venv .venv
.venv/bin/pip install https://spread.bahnexpress.com/kit/spread-0.1.0-py3-none-any.whl numpy pandas scipy scikit-learn
# .env holds SPREAD_URL and SPREAD_KEY (the team key). Never commit it.
```

## Run
```sh
.venv/bin/python -m lab.bench starter markup --seeds 8                 # A/B on bench-0..7
.venv/bin/python -m lab.bench markup markup:mult=1.45,min_drivers=12   # parameter variants
.venv/bin/python -m lab.bench markup --seed-list spread-1 --reveal     # save reveal/events to data/runs/
.venv/bin/python -m lab.bench --cleanup                                # free slots after a crash
```
The output gives, per variant: mean margin per week, sd, mean and min on-time, weeks ranked, orders won, and the **paired Δ vs the first variant with a t-stat** (|t| > 2 ≈ real). Every run is appended to `results/runs.jsonl`.

## Write a new algorithm
1. Create `lab/policies/myalgo.py`:
   ```python
   from ..desk import Desk
   class MyAlgo(Desk):
       NAME = "myalgo"
       DEFAULTS = {"mult": 1.4}           # every tunable number goes here -> settable from the CLI
       def price_quote(self, request):    # -> {option_kind: cents}; return self.decline(request) to pass
           ...
       def fee_schedule(self, order, cars, urgent):   # -> [{"at": minute, "feeCents": cents}, ...] non-decreasing
           ...
   ```
2. Register it in `lab/policies/__init__.py`.
3. `python -m lab.bench markup myalgo --seeds 16`

Hooks (see `lab/desk.py`): `price_quote`, `fee_schedule`, `audience_for`, `on_event` (sees every event: use it for learning), `on_start`.
Available state:
- `self.ctx`: map (`minutes(a,b)`, `km(a,b)`), roster, `drivers_in[town]`.
- `self.requests`, `self.orders`, `self.urgent`, `self.now`, `self.p` (params).
- `self.count(key)` for custom stats, which show up in `runs.jsonl`.

## Facts
- `starter` reproduces the handbook exactly (level 8, `spread-1` → −€72,612.51), so the refactor is faithful.
- Throughput: ~11 weeks/min with 8 workers at a server limit of 250 req/s. It falls when many teams practise and drops to **20 req/s during test finals (Sat 14:00, 20:00) and the final**. Don't plan big sweeps then.
- **The team shares 8 practice slots and one rate limit.** If two people run benches at once, each waits for slots. Coordinate, or use `--workers 4` each.
- Seeds: compare variants on the same seeds. Use a fresh `--seed-prefix` to check a winner on unseen weeks.
