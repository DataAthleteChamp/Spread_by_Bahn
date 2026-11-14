# Pain point research: staffing ~450 orders a week (rules-based ideas, agent report, Sat)

**Main point:** we post every gig the moment we win the order. Under the rules ("a driver hears of each order once"; "most only know the next day"; no notifications 23:00–07:00; "a car that you post again keeps the age of its first posting"), that throws away each order's one notification, ages the gig, invites drops, and teaches drivers to wait.

## Ranked mechanisms (impact)
1. **Post just in time (HIGH).** Defer posting until the day before pickup at 08:00, never between 22:00 and 07:00.
2. **Pair opposite-direction orders into one gig (HIGH).** A→B→A removes the trip home; it's the only way above ~1 order per driver per day. Discount quotes that complement open orders.
3. **Steer dealers to slack options and Monday deadlines (HIGH).** `same_day_mult` ≈ 1.2–1.3, `w3_mult` ≈ 0.85–0.9; Thursday/Friday → Monday uses idle capacity.
4. **Stop teaching waiting (HIGH/MED).** Open hard gigs flat at the fee they'll need. One jump at the warning instead of a ladder. Or a Dutch auction: open 1.2× and reprice down; reprices don't notify.
5. **Rebuild direct offers around our own working drivers (MED-HIGH).** On `picked_up`/`delivered`, offer gigs near that driver's delivery town, 07:00–21:00, at the app fee or 0.9×; cascade on decline.
6. **Our own early warning, aimed at daytime (MED).** Escalate at min(lastPickupAt − travel − 2h, 19:00 the day before); never at night.
7. **Notification coverage** = drivers within 30 km straight line of the pickup. Few drivers → open the fee higher (MED).
8. **Dealer trust (MED):** track on-time count per dealer; price up; protect high-trust dealers.
9. **Outage detector** (regional win spike → +20% until 18:00) (MED). 10. **Price-war day** (LOW-MED): freeze learning; maybe 0.85× on easy requests.
11. **React to `gig_dropped` / `no_show` / `driver_late`** (wake on them; release a late driver for free if they can't make the deadline) (MED-LOW).
12. **Read notes at first post:** plates → `withPlates`, manual → `manualLicence` (LOW-MED). 13. **Experienced-driver supply gate for premium cars** (LOW-MED). 14. **Per-dealer win-share cap ~60%** (LOW; conflicts with trust).

## Bugs found in our code
1. Offers at 1.7× go out in the same batch as an app reprice to 1.9×, so the offer always loses to the app.
2. `WAKE_ON` lacks `offer_answered`, `gig_dropped`, `no_show`, `driver_late`, `picked_up`, `delivered`, so reactions wait for the next request.
3. `repost` strips every window, including valid "not before" note windows, which causes `not_ready` failures.
4. A charging stop is added for every EV under 30%; the rule only needs it on routes **over 200 km**. That wastes 40 min.
5. The urgent ladder teaches big raises, and the late step can land at night.
6. The risk model ignores load (backlog per town/day) and the pickup-day offset.
7. `reach` ≠ notification coverage (30 km straight line).
8. Offer candidates include drivers busy on our gigs and home drivers who were already notified.

**Method tip:** fork at a single `order_won` to A/B post-now vs deferred without seed noise.
