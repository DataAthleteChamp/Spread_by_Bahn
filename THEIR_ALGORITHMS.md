# How Bahn's algorithms work (what we can actually see)

There are three "Bahn algorithms":

| Algorithm | Can we see it? | Source |
|---|---|---|
| **Bahn Express in real life** (production dispatch) | ❌ Not public. Only the business model is known | `RESEARCH.md` Part A |
| **House starter** (the kit's `starter.py`) | ✅ Full code, ~200 lines of logic | `/kit/spread-0.1.0-py3-none-any.whl` → `spread/starter.py` |
| **House best** (Bahn's best system) | ❌ Code is secret, ✅ **scores are public** | `GET /v1/leaderboards/practice?level=8` (no key needed) |

---

## 1. House starter: what the code does, step by step

The whole system is one loop: **wait for an event → react → send actions with the next clock step.**

```
loop:
    advance the world until one of these events:
        price_request, order_won, order_changed, order_cancelled,
        visit_failed, gig_expired, deadline_close
    for each event: handle it (queue actions in an "outbox")
    send the outbox together with the next advance   (1 HTTP request per step)
```

### 1a. Quoting (`quote`): no intelligence at all
```python
first = request["options"][0]
quote = { first.kind : first.listPriceCents }   # list price, first option only
```
- It always quotes the **list price**, and only for the **first** delivery option.
- It never declines, never looks at cost, never thinks about capacity.
- At level 8 the competitor is 26–54% above list, so **the starter wins almost everything**, including jobs it can't staff.

### 1b. Posting a gig (`win` → `post`)
As soon as an order is won:
- **One gig per order.** A trade-in becomes one gig with 2 cars. If it breaks the 12 h rule, it is split into 2 gigs.
- **Audience:** `experienced = True` if any car is premium (avoids the €150 fine). Otherwise everyone.
- **Stops:** pickup → delivery per leg. Adds `withCharging` if the car is electric with <30% charge.
- **Windows:** the order's windows, narrowed by what the note parser finds (1d).
- **No chaining across orders.** It never combines different orders into one gig.

### 1c. Fee schedules: the two "ramps"
```
fee = typicalFee × (cars in gig / cars in order)

rising (normal):   1.0 → 1.1 → 1.2 → 1.3 → 1.4 → 1.5 × fee     one step every hour
steep  (urgent):   1.5 → 1.75 → 2.0 → 2.25 → 2.5 × fee         one step every 30 min
```
- **steep** kicks in after a `deadline_close` warning (no driver 3 h before the last possible pickup). It reprices every open gig of that order.
- The schedule is predictable and always rising. The handbook warns this **teaches drivers to wait**.

### 1d. Note reading (`window_from_note`): regex keywords
- Finds clock times (`klo 14`, `14:30`) and ranges (`9-16`).
- Looks within ±16 characters for keywords:
  - **AFTER**: jälkeen, alkaen, after, from, not before, valmis, ready, efter, klar…
  - **BEFORE**: ennen, mennessä, before, by, latest, före, senast…
- Uses **DELIVERY** words (toimit, deliver, arrive, leverera…) to decide whether the time is about pickup or delivery.
- What it **misses**: weekday names, tomorrow/huomenna/i morgon, "half three", hours written as words, corrections ("not 3pm"), manual gearbox, no plates, summer tyres, tighter deadlines on other days.

### 1e. Repair after something goes wrong
| Event | Starter's reaction |
|---|---|
| `visit_failed: not_ready / closed` | Repost the car with pickup from now + 2 h (or later if the deadline moved) |
| `visit_failed: licence` | Repost with audience `manualLicence = True` |
| `visit_failed: no_plates` | Repost with `withPlates = True` |
| `gig_expired` | Repost with no stop windows (the car may still go, late) |
| `order_changed` | Withdraw the gig and post again (only if no driver has booked it) |
| `deadline_close` | Switch the order to the **steep** ramp |
| `order_cancelled` | Forget the order |

So it learns from failed visits **one by one, after paying for them**. It doesn't prevent them.

### 1f. Robustness (`rejoin`): the good part, worth copying
In the final it rebuilds everything from `snapshot()` + `events()`: open gigs, which are booked, urgent orders, failed visits without a new gig, and open requests. It survives restarts and server outages (waits 5 s, then rebuilds).

### What the starter never uses
- Direct offers.
- The driver list (homes, ratings, licences, drops).
- Where our drivers finish.
- Multi-order chaining.
- Win/loss history.
- Dealer trust.
- The forecast.
- `reprice` except at the deadline warning.
- Declining requests.

---

## 2. Scoreboard: House starter vs House best vs the teams

Level 8, ranking round "Saturday 00:00" (5 identical secret weeks for everyone, fetched 2026-11-14).

| Team | Margin (5 weeks) | Per week | On time | Orders won / week |
|---|---|---|---|---|
| #1 Juhus | **€80,030** | ~€16.0k | 97.5% | ~370 |
| #2 Bob the builders | €73,388 | ~€14.7k | 98.0% | ~300 |
| **House best** | **€71,790** | ~€14.4k | 96.9% | **~365** |
| #10 Cookiezi | €56,661 | ~€11.3k | 94.5% | — |
| #20 | €35,132 | ~€7.0k | — | — |
| **House starter** | **−€349,434** | ~−€70k | **47.7%** | **~910** |

119 teams are registered, 24 have played all 5 weeks, 22 are ranked. In the previous round (Fri 20:00), #10 was only €27k, so the field is improving fast.

### What the numbers tell us about House best
- **It wins about 40% as many orders as the starter (365 vs 910).** Order selection and higher quotes are the main thing. House best declines or prices out ~60% of requests.
- **~€40 margin per order** (€14.4k ÷ 365).
- **~97% on time**, a safe buffer above the 90% minimum. It never plays close to the line.
- Very **stable across weeks** (€12.2k–15.5k), so it is robust, not lucky.
- Bob the builders wins fewer orders (~300) at a similar margin, so its margin per order is higher (~€50). Two different strategies both work.

### Implied targets for us
- **Top 10 currently ≈ €11k+/week at ≥95% on time**, but expect the bar to rise by Sunday.
- **Win roughly 250–400 orders a week, not 900.**
- Keep on-time at **≥95%**: a safety margin for the final, where one bad week means not ranked.

---

## 3. What House best probably does (inference from rules + numbers, not confirmed)
1. **Quotes above list** (the competitor is +26–54% at level 8), probably adjusted per lane, dealer and day from wins and losses.
2. **Declines requests it can't staff**: few drivers near the pickup, evening or weekend, a long trip home, risky notes.
3. **Better fees** than the starter's ramp: probably opens nearer the clearing fee and uses direct offers.
4. **Reads notes properly** to avoid failed visits.
5. Keeps a **~97% on-time buffer**.

To learn more: the Bahn booth gives hints "one step at a time", and the House best runs on the leaderboard are a moving benchmark.
