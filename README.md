# Spread by Bahn Express - The Delusionals

An autonomous dispatcher for the Spread challenge: quote dealers, recruit
freelance drivers, and maximise settled ledger margin while delivering at least
90% of won orders on time.

## Final deployment

**Sunday 15 November 2026, Helsinki time: final at 09:00; registration closes
08:30; Junction submission closes 10:00.** The final moved from 08:00.
The [official schedule](https://spread.bahnexpress.com/judging) is authoritative.

Use **`FINAL`**, not `CANDIDATE` or an experimental preset. Its explicit policy
and overrides are frozen in [`lab/final_config.json`](lab/final_config.json).
The override SHA-256 begins `bbc9e2932686`. That file also contains historical
evidence/metadata; the runtime manifest records the actual loaded configuration.

Tested with Python 3.14 on macOS; the live runner's file lock supports macOS/Linux.

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Fill SPREAD_KEY in .env locally. Never commit or share the key.
.venv/bin/python -m lab.live FINAL --check
```

Preflight verifies the frozen policy/model fingerprints and authenticated API
access, and downloads the public map when the local cache is absent. It sends
no game actions and creates no practice worlds.

Start before 09:00 in a persistent terminal or supervised service:

```sh
mkdir -p results/final-runtime
# macOS: keep the Mac powered, online, and its lid open.
caffeinate -dis .venv/bin/python -u -m lab.live FINAL \
  >> results/final-runtime/final-live.log 2>&1
```

On Linux, omit `caffeinate -dis`. Starting early only waits for the organisers'
announcement; it does not start the simulation. Ended test worlds are ignored.
The process exits after the next final ends. Do not run a second live actor,
including from another machine or an old scheduled launcher.

## Verify what is running

```sh
tail -n 5 results/final-runtime/final-live.log
.venv/bin/python -m json.tool results/final-runtime/startup.json
.venv/bin/python -m json.tool results/final-runtime/state.json
```

`startup.json` records the PID, Git commit, explicit parameters, source hashes,
model hashes and dependency versions. `active.json` adds the joined world and
parameters resolved after model loading. `state.json` is updated while waiting
and during play; `result.json` contains the settled final score after completion.
These runtime files are ignored by Git and contain no team credential.

The per-checkout lock prevents two updated `lab.live` processes from acting
together. It cannot stop actors in other checkouts or on other machines.
Parameters are loaded once: editing `FINAL` on disk does not update a running
process. Source/model changes before joining are detected and require a restart.

After a crash, restart the same command. To rejoin explicitly, use the **current**
world ID from `active.json`, never a previous test's ID:

```sh
.venv/bin/python -u -m lab.live FINAL --world CURRENT_WORLD_ID
```

## Solution and evidence

- **Pricing:** online win-probability learning and expected-profit quotes, with
  job-specific execution cost, trust and delivery-risk penalties.
- **Recruitment:** a booking/drop-probability dynamic program sets fee schedules;
  predictable raises account for drivers learning to wait.
- **Execution:** delayed posting, multilingual readiness notes, charging rules,
  booking/drop handling and snapshot/event reconstruction after disconnects.
- **Risk:** a projected-delivery controller and limited safe-order bonus.
  These are heuristics, **not a guarantee** of qualification or a top-10 finish.

The 01:00 rehearsal settled at **EUR9,725.15**, **319 orders**, **96.24% on time**.
The highest recorded fully qualifying ranking round earned **EUR77,245.49**
across five weeks, each at least 95% on time. Neither is the real final result.

[`EXPERIMENTS.md`](EXPERIMENTS.md) records the comparisons and rejected ideas.
The latest calendar, ratio-credit and selective-concession campaigns contain
396 L8 practice runs; none justified replacing `FINAL`.

```sh
# Generates evidence from existing results only; no fitting or simulator actions.
.venv/bin/python -m lab.submission_report > results/submission-report.json
```

The [lab guide](lab/README.md) covers practice benchmarks. Do not start new
experiments or modify frozen files during the final.

## Submission

Follow [`SUBMISSION.md`](SUBMISSION.md). The eight-slide presentation is
[`submission/slides.html`](submission/slides.html): open it in a browser to
present, or print/save as a landscape PDF. Update its final-result placeholder
after the real final has settled.

The repository remains **private**. Grant the judges access before submitting
the code link. Commit/push and a running agent do **not** submit the Junction form.
