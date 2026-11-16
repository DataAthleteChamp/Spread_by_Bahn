# Live operations

**The 2026 final is over.** The runner has been stopped after a sleep/network
outage prevented participation. See [the postmortem](../POSTMORTEM.md).
The instructions below describe operation for a future authorised run, not a
way to replay the ended final.

Use **`FINAL`**, not `CANDIDATE` or an experimental preset. The explicit policy
and overrides are frozen in [`lab/final_config.json`](../lab/final_config.json);
the override SHA-256 begins `bbc9e2932686`. Historical metadata in that file is
not a guarantee of current performance.

## Start early

Follow the [organisers' latest announcement](https://spread.bahnexpress.com/judging).
The runner uses the platform API, **not a hardcoded 08:00 or 09:00 launch timer**.
It can start waiting well before the final; ended test worlds are ignored.

After the [quick start](../README.md#quick-start), run in a persistent terminal
or supervised service:

```sh
.venv/bin/python -m lab.live FINAL --check
mkdir -p results/final-runtime

# macOS: keep the machine powered, online and its lid open.
caffeinate -dis .venv/bin/python -u -m lab.live FINAL \
  >> results/final-runtime/final-live.log 2>&1
```

On Linux, omit `caffeinate -dis`. Preflight verifies frozen policy/model hashes
and authenticated API access, and fetches the public map when its cache is absent.
It sends no game actions and creates no practice worlds.

The runner exits after the next final ends. Do not launch another actor,
including from another machine or an old scheduled launcher. Do not start new
experiments or edit frozen files during the final.

## Inspect the actual process

```sh
tail -n 5 results/final-runtime/final-live.log
.venv/bin/python -m json.tool results/final-runtime/startup.json
.venv/bin/python -m json.tool results/final-runtime/state.json
```

| Runtime file | Meaning |
|---|---|
| `startup.json` | PID, code commit, explicit parameters, source/model hashes and dependency versions |
| `active.json` | Joined world and parameters resolved after loading models |
| `state.json` | Waiting/running/ended status and heartbeat |
| `result.json` | Settled score after completion |

These files are ignored by Git. A per-checkout file lock prevents two updated
`lab.live` processes from acting together; it cannot block another checkout or
machine using the same team key.

## Recover safely

After a crash, restart the same command. To rejoin explicitly, use the **current**
world ID from `active.json`, never a previous rehearsal's ID:

```sh
.venv/bin/python -u -m lab.live FINAL --world CURRENT_WORLD_ID
```

The runner rebuilds from the snapshot and event history. An interrupted stream
is not treated as a completed week.

Parameters are loaded once. Editing a preset does not update an existing runner;
source/model changes before joining are detected and require a restart. A
documentation-only commit does not alter the running policy.

## After the final

Confirm the outcome against the official leaderboard. This event's verified
record is [`results/final-outcome.json`](../results/final-outcome.json).
Follow [`SUBMISSION.md`](../SUBMISSION.md) for the archived handoff.
Pushing code and running the agent do **not** submit the Junction form.
