# Official final: no participation after host sleep

The official final ended with **EUR0 margin, zero won orders and no rank**.
All **1,034 requests were unquoted**. This was an availability failure: the
local runner survived as a process but never joined the final while it was active.
It is not a measured failure of the quoting strategy on that secret week.

## Confirmed timeline

All times below are **15 November 2026, Helsinki (UTC+2)**.

| Time | Evidence |
|---|---|
| 04:33 | Frozen FINAL runner started from commit `34dfc5d`; credentials and model fingerprints passed preflight. |
| 06:23:17 | Last regular waiting log before the outage. |
| 06:23:36 | macOS recorded `Clamshell Sleep` while on battery. |
| 06:50 onward | The runner logged address/DNS failures during brief maintenance wake-ups. |
| 09:00-09:34:18 | The official final ran. The host's sleep/wake history and runner log show no sustained connectivity during this window. |
| 15:25:17 | A full lid/activity wake was recorded. The runner later resumed polling, after the final had ended. |
| After investigation | The now-unneeded waiting runner and its own keep-awake helper were stopped. |

The start was 07:00 UTC: **09:00 Helsinki / 08:00 Central European Time**.
The client followed the API announcement; it did not have a 09:00 start timer.
The 08:00/09:00 display distinction was not the cause.

## What the evidence establishes

- The team had a final world: `fbcee268ddd35efae2244`.
- Official reveal: 1,034 requests, 1,034 `unquoted`, no recorded quotes.
- Snapshot: no orders and no gigs. Events: requests and losses, no delivery ledger.
- Official score and public leaderboard agree on zero margin, zero orders and
  `ranked=false`.
- The original process was still alive during investigation and its frozen
  source/model fingerprints still matched. There was no recorded join, strategy
  exception or source-hash rejection for the final.

The machine's clamshell sleep and network errors explain why a surviving process
was insufficient. `caffeinate` did not prevent the observed sleep or provide
network availability.

## Deployment gaps

We relied on a local laptop for unattended execution. Readiness checks proved
that the process and connection worked at the time of inspection, not throughout
the competition. No independent outage alert or always-on fallback was configured.
Network failures were logged, but a waiting heartbeat was not an end-to-end
participation guarantee.

For another event, deployment should be on a verified always-on host with
external connectivity/heartbeat alerts, an explicit missed-start alarm and a
tested recovery procedure. Any standby must enforce one active writer for the
team to avoid duplicate actions. These are lessons, not retroactive fixes or a
claim that the strategy would otherwise have reached the top ten.

## Can the final be rerun?

Not through the supported participant API. Final worlds cannot be advanced or
forked, and restarting a client does not rewind the server clock. A new practice
week would not count and would not reproduce the undisclosed final seed.
Only the organisers could authorise a new official run; none is assumed here.

## Evidence and privacy

[`results/final-outcome.json`](results/final-outcome.json) archives the read-only
official result. [`lab/collect_final_outcome.py`](lab/collect_final_outcome.py)
can refresh it while that same final remains available.

The selected host-event times were checked against `pmset -g log` and the local
runner log. Full host logs, credentials and runtime files are not published.
The API reports `onTimeShare=1` for the empty order set; our presentation displays
**N/A**, not a meaningful 100% delivery rate.
