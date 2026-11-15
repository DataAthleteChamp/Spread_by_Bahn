# Final submission handoff

## Submit on Junction by Sunday 15 November, 10:00 Helsinki

1. **Submission hash:** copy it directly from the authenticated
   [team page](https://spread.bahnexpress.com/team). Do not put the team API key
   or submission hash into Git.
2. **Code:** https://github.com/DataAthleteChamp/Spread_by_Bahn
   - This repository is private by choice. Arrange reviewer access.
   - Record the final commit with `git rev-parse HEAD`; use a commit-pinned link
     if Junction accepts it.
3. **Presentation:** open `submission/slides.html`, review all eight slides and
   replace the final-result placeholder after the 09:00 run settles. Print to
   landscape PDF if a PDF upload is required.

No Junction form has been submitted by this repository tooling.

## Suggested project description

The Delusionals built a dispatcher that jointly prices dealer requests and
recruits voluntary drivers. An online win model estimates the price/volume
trade-off; a booking-and-drop model informs fee schedules. Execution respects
pickup readiness, multilingual notes and charging requirements. A delivery-risk
controller protects the 90% on-time qualification threshold.

We evaluate policy changes on paired simulator weeks, separate known stress
cases from previously unseen scenarios, and report full-week profit confidence
intervals. We retain failed experiments rather than presenting only favourable
seeds. The production configuration is frozen and its running process records
the code, parameter and model identities.

## Evidence and limitations

| Evidence | Result | Interpretation |
|---|---|---|
| Booking/drop fee DP, `sweep40` | +EUR407.90/week over CANDIDATE8 on 24 paired development weeks | Effect of that ablation, not a promised final uplift |
| Best recorded qualifying ranking round, `board6` | EUR77,245.49; 2,016 orders; every week >=95% on time | Five-week ranking total, not comparable to a single final week |
| 01:00 live rehearsal | EUR9,725.15; 319 orders; 96.24% on time | Rehearsal, not the real final |
| Latest experimental screens | 396 L8 practice runs | Calendar, ratio-credit and selective-concession variants were not promoted |
| Known failure | `c17-52`: FINAL 89.90% on time | Qualification and top-10 placement are not guaranteed |

Reproduce these numbers with `python -m lab.submission_report`. Source results,
world IDs, predefined seed sets and experiment manifests are in `results/`.
Private driver costs and competitor prices are never revealed by the simulator;
the system estimates them indirectly, rather than claiming privileged access.

## Final morning checklist

- Before 08:30: verify team registration and private-repository reviewer access.
- Before 09:00: confirm exactly one `FINAL` process is waiting or joined, with
  a fresh heartbeat and the intended Git/model/parameter identity.
- Keep the machine powered and connected until the world ends, approximately
  09:35. Keep the Mac lid open; keep the process/session alive.
- After completion: read `results/final-runtime/result.json`, verify the world
  and official [leaderboard](https://spread.bahnexpress.com/leaderboard), then
  add the real result to the presentation.
- By 10:00: submit the hash, accessible code link and presentation on Junction.

The [official schedule](https://spread.bahnexpress.com/judging) says **09:00**,
not the older 08:00 time found in archived research and kit documents.
