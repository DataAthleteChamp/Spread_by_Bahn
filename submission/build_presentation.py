"""Export one evidence-linked ten-slide story to editable PPTX, PDF and HTML.

Run with the isolated presentation environment after build_evidence.py.
All layouts share measured text wrapping and fixed 16:9 coordinates.
"""
from __future__ import annotations

import hashlib
import html
import importlib.metadata
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
W, H = 960, 540
NAVY, BLUE, TEAL = "#132D46", "#315EEA", "#008C7D"
MUTED, PALE, WHITE, AMBER, RED = "#53677A", "#EDF3F8", "#FFFFFF", "#A65E00", "#B63D45"


def money(value, signed=False, decimals=0):
    sign = "+" if signed and value >= 0 else ""
    return f"{sign}EUR {value:,.{decimals}f}"


def percent(value):
    return f"{100 * value:.2f}%"


def interval(values):
    return f"{values[0]:,.0f} to {values[1]:,.0f}"


def wrapped(value, font, size, width):
    lines = []
    for paragraph in str(value).split("\n"):
        line = ""
        for word in paragraph.split():
            if stringWidth(word, font, size) > width:
                raise ValueError(f"Unbreakable text exceeds its box: {word}")
            candidate = f"{line} {word}".strip()
            if line and stringWidth(candidate, font, size) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


class Slide:
    def __init__(self, number, label, title, sources, status="DEPLOYED IDEA", dark=False):
        self.number, self.title, self.sources = number, title, sources
        self.dark, self.items, self.notes = dark, [], ""
        self.rect(0, 0, W, H, NAVY if dark else WHITE)
        self.rect(42, 28, 876, 5, TEAL)
        self.text(42, 48, 700, 20, label.upper(), 12, True, "#98DAD1" if dark else TEAL)
        self.rect(770, 46, 148, 25, "#25455F" if dark else PALE)
        self.text(780, 51, 128, 17, status, 10, True, WHITE if dark else MUTED)
        self.text(42, 83, 876, 84, title, 32, True, WHITE if dark else NAVY)
        self.text(42, 514, 555, 16, "THE DELUSIONALS  |  SPREAD  |  " + sources, 10, False,
                  "#BBCFDF" if dark else MUTED)
        self.text(868, 512, 50, 18, f"{number:02d} / 10", 11, True, "#BBCFDF" if dark else MUTED)

    def rect(self, x, y, w, h, color, radius=0):
        self.items.append({"kind": "rect", "x": x, "y": y, "w": w, "h": h, "color": color, "radius": radius})

    def text(self, x, y, w, h, value, size=18, bold=False, color=NAVY, mono=False):
        font = "Courier" if mono else "Helvetica-Bold" if bold else "Helvetica"
        lines = wrapped(value, font, size, w)
        leading = size * 1.18
        if len(lines) * leading > h + 0.1:
            raise ValueError(f"Slide {self.number}: text needs {len(lines)*leading:.1f}pt, has {h}pt: {value}")
        if x < 0 or y < 0 or x + w > W + .1 or y + h > H + .1:
            raise ValueError(f"Slide {self.number}: text outside the canvas")
        self.items.append({"kind": "text", "x": x, "y": y, "w": w, "h": h, "lines": lines,
                           "size": size, "leading": leading, "font": font, "bold": bold, "color": color})

    def arrow(self, x, y, w=18, h=12):
        self.items.append({"kind": "arrow", "x": x, "y": y, "w": w, "h": h, "color": TEAL})

    def paragraph(self, x, y, w, heading, body, h=93):
        self.text(x, y, w, 20, heading.upper(), 12, True, TEAL)
        self.text(x, y + 26, w, h - 26, body, 18)

    def card(self, x, y, w, h, label, value, detail, dark=False):
        self.rect(x, y, w, h, "#20425E" if dark else PALE, 8)
        self.text(x + 18, y + 17, w - 36, 20, label.upper(), 11, True, "#BCD2E3" if dark else MUTED)
        self.text(x + 18, y + 48, w - 36, 76, value, 28, True, WHITE if dark else NAVY)
        self.text(x + 18, y + h - 48, w - 36, 39, detail, 15, False, "#D4E4EF" if dark else MUTED)

    def table(self, x, y, widths, headers, rows, row_h=48, size=18):
        width = sum(widths)
        self.rect(x, y, width, 34, NAVY)
        offset = x
        for w, header in zip(widths, headers):
            self.text(offset + 10, y + 9, w - 20, 20, header, 12, True, WHITE)
            offset += w
        for i, row in enumerate(rows):
            yy = y + 34 + i * row_h
            self.rect(x, yy, width, row_h - 1, PALE if i % 2 == 0 else "#F8FAFC")
            offset = x
            for w, value in zip(widths, row):
                self.text(offset + 10, yy + 10, w - 20, row_h - 14, value, size, i == len(rows) - 1)
                offset += w


def effect_table(slide, item, x=510, y=182, labels=("Without", "With")):
    a, b = item["before"], item["after"]
    slide.table(x, y, [125, 155, 128], ["Same weeks", "Margin / week", "Mean on-time"],
                [[labels[0], money(a["margin_eur_per_week"]), percent(a["mean_week_on_time"])],
                 [labels[1], money(b["margin_eur_per_week"]), percent(b["mean_week_on_time"])]])
    cohort = "53 paired weeks (40 new + 13 stress)" if item["id"] == "denoising" else f"{a['weeks']} paired development weeks"
    slide.text(x, y + 142, 408, 43, cohort + "\n"
               f"Qualified {a['qualified_weeks']}/{a['weeks']} -> {b['qualified_weeks']}/{b['weeks']}", 15, False, MUTED)
    slide.text(x, y + 187, 408, 20,
               f"95% paired margin delta CI: EUR {interval(item['margin_delta_95'])}/week", 12, False, MUTED)


def story(e):
    ex, scale = e["experiments"], e["scale"]
    slides = []
    s = Slide(1, "Measured results, not an untested claim",
              "ML-guided dispatch: profit with a delivery constraint", "E6",
              "FINAL RESULT" if e["final_result"] else "FINAL PENDING", True)
    final = e["final_result"]
    final_value = money(final["score"]["marginCents"] / 100) if final else "PENDING"
    if final is None:
        final_detail = "Fill only after the real final settles"
    elif final["score"]["wonOrders"] == 0:
        final_detail = "0 orders | not ranked | on-time: N/A"
    else:
        final_detail = f"{final['score']['wonOrders']} orders | {percent(final['score']['onTimeShare'])} on time"
    s.card(42, 190, 276, 162, "Real final", final_value, final_detail, True)
    r = e["rehearsal"]["score"]
    s.card(342, 190, 276, 162, "01:00 live rehearsal", money(r["marginCents"] / 100),
           f"{r['wonOrders']} orders | {percent(r['onTimeShare'])} on time", True)
    b = e["highest_qualifying_round"]
    s.card(642, 190, 276, 162, "Best recorded ranking round", money(b["margin_eur"]),
           f"5 weeks | every week >= {100*b['min_on_time']:.0f}% on time", True)
    s.text(42, 383, 876, 60, "Three levers: risk-priced quotes, timed driver fees, and a less noisy cost estimate.",
           25, True, WHITE)
    final_note = ("Official final: 1,034 requests unquoted after host sleep/network loss. See POSTMORTEM.md."
                  if final and final.get("participation") == "no_quotes_submitted"
                  else "The ranking total spans five weeks. The rehearsal is not the real final. Frozen policy: FINAL.")
    s.text(42, 462, 876, 36, final_note, 15, False, "#CCDDEB")
    s.notes = ("Open with the measured answer. Use the real-final card only after checking the settled result against "
               "the official leaderboard; never replace a pending result with a rehearsal number. Best recorded ranking "
               "round is board6: EUR77,245.49 over five distinct weeks, 2,016 won "
               "orders, each week at least 95% on time. The 01:00 rehearsal earned EUR9,725.15 on 319 orders, 96.238% on time. "
               "These are ledger margins in the simulator, not Bahn's corporate profit. We are not claiming top-10 placement.")
    if final and final.get("participation") == "no_quotes_submitted":
        s.notes += (" The actual official final ended with EUR0, zero orders and all 1,034 requests unquoted. "
                    "The local Mac entered clamshell sleep at 06:23 Helsinki and logged network/DNS failures through "
                    "the 09:00-09:34 final. The runner never joined; this was an availability failure, not a measured "
                    "strategy result. With zero orders, on-time is undefined, not a meaningful 100%. "
                    "See POSTMORTEM.md and results/final-outcome.json. Restarting cannot replay the ended final.")
    slides.append(s)

    s = Slide(2, "Business context", "Bahn sells delivery speed and certainty", "S1, S2, S3", "COMPANY CONTEXT")
    s.paragraph(42, 180, 525, "Fixed quote, uncertain execution",
                "Customers see price and ETA up front. Recruiting and completing the trip still consumes uncertain capacity.")
    s.paragraph(42, 287, 525, "A driver chooses the job",
                "The app shows route and pay before acceptance. Pickup photos and delivery documents close the operational loop.")
    s.paragraph(42, 394, 525, "The business payoff",
                "Faster stock arrival releases dealer capital. Reliability, customer handover and actual trip costs matter together.")
    s.card(607, 179, 311, 156, "Company-reported network", "5K+ drivers", "Registered, not simultaneously available")
    s.text(625, 356, 277, 110, "Kamux case: about two weeks before; about three days from Sweden with Bahn.", 21, True)
    s.text(607, 470, 311, 29, "Customer account, not our system's effect.", 12, False, MUTED)
    s.notes = ("Sources S1-S3 were checked on 15 November 2026. Bahn, formerly Bahn Express, describes direct car delivery "
               "and also truck transport. Domestic operations are described in Finland, Denmark and Germany. Its driver page "
               "advertises 5K+ registered drivers and 25 collection countries; registration is not active supply. "
               "The Kamux case is a company-published testimonial, not a controlled comparison or a result of our code. "
               "The homepage says 400+ dealerships/brokers and the about page says 100+ dealerships, so we avoid one precise "
               "customer-count claim. Proposed production work needs actual fuel, ferry, insurance and support costs, not "
               "just the simulator's driver-fee ledger.")
    slides.append(s)

    s = Slide(3, "Current system and technical scale", "Learn offline; decide quickly from live events", "E7, S4", "DEPLOYED SYSTEM")
    nodes = [("Request", "Dealer, route,\noption, note"), ("Features", "Lane, slack,\nload, trust"),
             ("Quote", "Win model +\nrisk / cost"), ("Gig", "Fee lookup +\nexecution rules"),
             ("Delivery", "Booked, drop,\narrival"), ("Feedback", "Ledger +\nwin / loss")]
    for i, (title, detail) in enumerate(nodes):
        x = 42 + i * 150
        s.rect(x, 182, 126, 102, PALE, 7)
        s.text(x + 12, 195, 102, 26, title, 18, True)
        s.text(x + 12, 232, 104, 44, detail, 14)
        if i < 5:
            s.arrow(x + 130, 225, 16, 12)
    s.card(42, 320, 276, 134, "Late-risk classifier", f"{scale['risk_features']} features",
           f"{scale['risk_training_orders']:,} training orders")
    s.card(342, 320, 276, 134, "Booking-hazard model", f"{scale['hazard_exposure_rows']/1000:.0f}k intervals",
           f"{scale['hazard_spells']:,} gig spells | 10-minute exposure")
    s.card(642, 320, 276, 134, "Typical-fee prior", f"{scale['reference_lane_cells']:,} cells",
           f"{scale['reference_observations']:,} reference-fee observations")
    s.text(42, 467, 876, 36,
           f"{scale['recorded_completed_l8_practice_worlds']:,} recorded L8 runs over {scale['distinct_seed_labels']:,} reused seed labels. "
           "Live limits: 20 actions/s, 50 reads/s. Simulator scale, not company throughput.", 15, False, MUTED)
    s.notes = ("The deployed policy is a hybrid of statistical models and hand-coded operational rules, not an end-to-end "
               "neural agent. Its win model uses a lane prior and online week/dealer intercept updates. The fixed late-risk "
               "classifier has 17 features and 15,568 historical training orders. Hazard training used 686,245 exposure rows "
               "from 22,877 gig spells: exposure rows are not independent bookings. The fee prior contains 2,021 lane/private-"
               "status cells. The live process uses event streaming and compressed fee-table lookups; fitting and full DP "
               "construction happen offline. FINAL does not enable multi-order pairing and declines trade-in requests. "
               f"The journal contains {scale['recorded_completed_l8_practice_worlds']:,} completed L8 practice worlds over "
               f"{scale['distinct_seed_labels']:,} reused seed labels, not that many independent validation draws.")
    slides.append(s)

    s = Slide(4, "Idea 1 | risk-priced dealer quotes", "Price risk instead of only using a hard cutoff", "E1", "PAIRED ABLATION")
    s.paragraph(42, 183, 425, "The idea",
                "Keep feasibility checks. Online logistic P(win) and learned P(late) score each eligible quote.", 102)
    s.paragraph(42, 294, 425, "Why",
                "A hard lateness threshold can discard profitable work. A soft penalty lets price express the trade-off.", 95)
    effect_table(s, ex["pricing"], labels=("Hard gate", "Risk-priced"))
    s.rect(42, 394, 876, 49, PALE, 6)
    s.text(58, 406, 844, 30, "score(p) = P(win | p) * [p - expected driver fee - risk costs]", 18, False, NAVY, True)
    s.text(42, 460, 876, 43,
           f"{money(ex['pricing']['margin_delta_eur'], True)}/week; "
           f"on-time {ex['pricing']['on_time_delta_pp']:+.2f} percentage points. Profit improved; punctuality fell.", 18, True)
    s.notes = ("This is a specific ablation, not a claim that the entire pricing model added EUR909. "
               "sweep40 compares CANDIDATE8's hard risk gate against mu_eur=25,risk_hard=0.6, on the same 24 development weeks "
               "(12 historical stress and 12 new). Existing route, deadline and feasibility checks remain. The online win "
               "model is sigmoid(beta*(week + dealer + lane + trust - log(quote/list))), with beta about 7.84. Its week and "
               "dealer offsets update from win/loss residuals. The quote grid contains 53 list-price multipliers. "
               f"Paired margin 95% interval: EUR {interval(ex['pricing']['margin_delta_95'])}. "
               "The mean on-time share falls from 95.85% to 94.94%; both variants qualified on all 24 tested weeks. "
               "These development results are not a guarantee on an unseen final.")
    slides.append(s)

    s = Slide(5, "Idea 2 | driver-fee timing", "Pay for a retained booking, not a cheap first offer", "E2", "PAIRED ABLATION")
    s.paragraph(42, 183, 425, "The idea",
                "Fit booking/drop hazards; solve the fee path offline. Serve a time-to-pickup / driver-coverage lookup online.", 102)
    s.paragraph(42, 294, 425, "Why",
                "A low fee can mean waiting, drops or an expensive rescue. Predictable increases also teach drivers to wait.", 95)
    effect_table(s, ex["hiring"], labels=("Legacy", "Fee DP"))
    s.rect(42, 394, 876, 49, PALE, 6)
    s.text(58, 406, 844, 30, "Choose the fee path with the lowest expected booking + delay + re-hiring cost.", 18)
    s.text(42, 460, 876, 45,
           f"{money(ex['hiring']['margin_delta_eur'], True)}/week; on-time "
           f"{ex['hiring']['on_time_delta_pp']:+.2f} points on the same 24 weeks.", 19, True, TEAL)
    s.notes = ("The hazard model estimates a booking probability for a 10-minute exposure period. The DP also accounts for "
               "drop/re-hiring risk, terminal deadline cost and a penalty for teaching drivers to wait for raises. A driver "
               "who drops is not simply paid the completed-gig fee. Deployed schedules use a compressed table indexed by "
               "hours to lastPickupAt and home-driver coverage near pickup, with the hard-order premium retained. "
               "The rich fitted model is therefore not solved online for every gig. Adding haz=1 to CANDIDATE8 yielded "
               f"a paired margin interval of EUR {interval(ex['hiring']['margin_delta_95'])}. "
               "Total driver fees did not necessarily decrease: better fills and fewer late outcomes can raise net margin. "
               f"The combined pricing+fee change earned {money(ex['combined']['after']['margin_eur_per_week'])}/week "
               "on these weeks, so the two standalone uplifts must not be added together.")
    slides.append(s)

    s = Slide(6, "Idea 3 | a better execution-cost input", "Denoise the typical fee before pricing the job", "E3", "MIXED COHORT")
    s.paragraph(42, 183, 425, "The idea",
                "Shrink each noisy typical-fee signal toward its lane and private-address bucket's historical log-mean.", 102)
    s.paragraph(42, 294, 425, "Why",
                "The benchmark is not the cheapest driver's cost. Request-level noise can distort both quotes and gig fees.", 95)
    effect_table(s, ex["denoising"], labels=("Raw typical", "Denoised"))
    s.rect(42, 394, 876, 49, PALE, 6)
    s.text(58, 406, 844, 30, "fee_hat = exp[a * lane_log_mean + (1-a) * log(raw_fee)];  a = n/(n+4)", 17, False, NAVY, True)
    s.text(42, 456, 876, 45,
           f"53 matched weeks: {money(ex['denoising']['margin_delta_eur'], True)}/week. "
           f"40 new weeks alone: {money(ex['denoising_fresh']['margin_delta_eur'], True)}, "
           f"95% CI EUR {interval(ex['denoising_fresh']['margin_delta_95'])}.", 17, True)
    s.notes = ("c14val compares historical FINAL13 against ref_w=0. The 53 matched weeks contain 40 new c14-* weeks plus "
               "13 known stress weeks. Do not call all 53 unseen. Across all 53, mean margin rises from EUR13,523.28 to "
               "EUR13,809.70 and mean weekly on-time share from 95.44% to 96.07%; all weeks qualify. "
               f"The all-53 margin interval is EUR {interval(ex['denoising']['margin_delta_95'])}. "
               "On the 40 new weeks alone, margin rises from EUR13,334.51 to EUR13,545.85 and on-time from 95.46% to 96.28%, "
               "but the margin interval crosses zero. This is directional evidence, not a conclusive fresh-only profit gain. "
               "The deployed ref_w=0 formula still retains per-request information through n/(n+4) shrinkage. "
               "The current model contains 83,145 reference observations and residual log-noise SD about 0.123. "
               "The legacy fit lacks a complete training-world manifest; better provenance belongs in the production roadmap.")
    slides.append(s)

    s = Slide(7, "Delivery-share protection", "Sometimes qualification costs immediate margin", "E4", "SAFETY TRADE-OFF")
    s.text(42, 178, 876, 52,
           "When projected on-time falls below 93%, a limited bonus favours options predicted below 5% late risk.", 21)
    case = ex["safety_stress"]
    s.table(42, 249, [132, 155, 129], ["c15-25", "Margin", "On-time"],
            [["Bonus off", money(case["before"]["margin_eur_per_week"]), percent(case["before"]["mean_week_on_time"])],
             ["Bonus on", money(case["after"]["margin_eur_per_week"]), percent(case["after"]["mean_week_on_time"])]],
            row_h=52, size=17)
    s.text(42, 407, 416, 61, "279 -> 314 wins. The extra denominator rescued this week, at a cost of EUR1,004.", 18)
    a, b = ex["safety"]["before"], ex["safety"]["after"]
    s.text(514, 251, 404, 47, "Across 63 completed pairs", 23, True)
    s.text(514, 309, 404, 90,
           f"Margin: {money(a['margin_eur_per_week'])} -> {money(b['margin_eur_per_week'])}/week\n"
           f"Mean on-time: {percent(a['mean_week_on_time'])} -> {percent(b['mean_week_on_time'])}\n"
           "Qualified: 62/63 -> 63/63", 18)
    s.text(514, 421, 404, 65, "Limit: FINAL still fails c17-52 at 89.90%. This is not a hard 90% guarantee.", 18, True, RED)
    s.notes = ("The official condition is late_orders <= floor(0.1*noncancelled_won_orders), and every leg must be on time. "
               "The deployed safe-win bonus activates only when projected on-time is below 0.93, applies to predicted lateness "
               "below 0.05, tapers with risk and is capped at EUR20 per expected win. It is not a blanket price reduction. "
               "dil2 has 64 attempted seeds, but one baseline server failure leaves 63 complete pairs. In those pairs, "
               f"mean margin delta is {money(ex['safety']['margin_delta_eur'], True, 2)}; 95% interval EUR "
               f"{interval(ex['safety']['margin_delta_95'])}. Mean weekly on-time rises only 0.045 percentage points. "
               "The c15-25 example costs EUR1,004.01 to move from unqualified to qualified. It is one development case. "
               "The later c17-52 failure remains. Tighter note/private-appointment deadlines, late bookings and correlated "
               "regional shortages can break nominal-deadline or average-risk assumptions.")
    slides.append(s)

    s = Slide(8, "What we did not ship", "More fills did not mean more dependable profit", "E5", "REJECTED EXPERIMENT")
    item = ex["volume"]
    a, b = item["before"], item["after"]
    s.table(42, 181, [176, 156, 158, 171, 215],
            ["24 fresh weeks", "Wins / week", "Margin / week", "Mean on-time", "Qualified weeks"],
            [["Frozen FINAL", f"{a['wins_per_week']:.0f}", money(a["margin_eur_per_week"]), percent(a["mean_week_on_time"]), "24/24"],
             ["Ratio credit", f"{b['wins_per_week']:.0f}", money(b["margin_eur_per_week"]), percent(b["mean_week_on_time"]), "23/24"]],
            row_h=50, size=18)
    s.text(42, 337, 876, 52, f"+20% wins; margin gain {money(item['margin_delta_eur'])}/week, "
           f"95% CI EUR {interval(item['margin_delta_95'])}. Not promoted.", 21, True, RED)
    s.text(42, 399, 876, 51, "Added orders earned about EUR2,980/week, but retained and displaced work lost about EUR2,648.",
           20)
    pair = ex["pairing"]
    s.text(42, 470, 876, 34, "Pairing also stayed off: 24 matched weeks, margin EUR14,050 -> EUR13,925; "
           "on-time 95.98% -> 94.45%.", 14, False, MUTED)
    s.notes = ("This row is ratio1 on its 24 fresh screening weeks, not the stress cases. The moderate credit won 452.17 "
               "orders/week versus 377.33, but net margin only rose EUR331.64 with an interval spanning zero and a new "
               "qualification failure. The larger credit was worse. The accounting decomposition on the same 24 pairs "
               "found EUR2,980.15 of added-order net, EUR2,005.36 lost on retained orders and EUR642.42 of displaced baseline "
               "net. It is an identity under two closed-loop policies, not proof the new orders can be gained independently. "
               "Drivers and the competitor react. Pairing in struct1 is a separate 24-week experiment; its point-estimate "
               "margin fell EUR125.01 and on-time fell 1.53 points. We therefore do not claim batching cars is a deployed gain. "
               "These results motivate cost-aware acquisition and better capacity forecasts, not indiscriminate undercutting.")
    slides.append(s)

    s = Slide(9, "Future ML | not yet implemented", "Predict the operational outcomes that change decisions", "R1, R2, E7", "PROPOSED ROADMAP")
    cards = [
        ("Retained booking", "Survival / competing-risk model",
         "Inputs: fee exposure, route, pickup window, booking and drop history.",
         "Output: P(booked and retained before pickup); expected re-hiring cost."),
        ("Arrival uncertainty", "Quantile model + calibration",
         "Inputs: readiness, route, observed travel times, weather and site hours.",
         "Output: arrival intervals; flag promises with little deadline headroom."),
        ("Marginal order value", "Cost + capacity-value model",
         "Inputs: settled fees/refunds, feasible driver supply, future pickup workload.",
         "Output: expected contribution and a location/time capacity charge."),
    ]
    for i, (title, model, inputs, output) in enumerate(cards):
        x = 42 + 300 * i
        s.rect(x, 180, 276, 267, PALE, 8)
        s.text(x + 17, 197, 242, 48, title, 23, True)
        s.text(x + 17, 259, 242, 43, model, 16, True, TEAL)
        s.text(x + 17, 314, 242, 62, inputs, 16)
        s.text(x + 17, 387, 242, 54, output, 15)
    s.text(42, 465, 876, 34, "No company-data model has been trained here. Calibration under shift and safe action limits are required.", 15, True, AMBER)
    s.notes = ("These are proposed next steps, not completed features or measured production gains. First, use a survival "
               "or competing-risk model so unbooked/censored gigs and post-booking drops are handled explicitly. Fee-response "
               "estimates from observational data are confounded by job difficulty and policy decisions; safe controlled "
               "experiments are needed before interpreting effects causally. Second, predict delivery-time quantiles and "
               "calibrate intervals on later, held-out data. R2's standard conformal guarantee relies on exchangeability "
               "and is marginal, not a per-route or weekly-SLA guarantee. Third, learn execution contribution and capacity "
               "value by actual pickup time and region. R1 motivates spatio-temporal values but assumes complete information; "
               "its welfare/equilibrium guarantees do not transfer. Our failed static capacity surcharge is evidence against "
               "deploying a guessed penalty without better state estimation. Company integration requires permitted access "
               "to operational events; raw driver-location and customer data must be minimised and protected.")
    slides.append(s)

    s = Slide(10, "Production path | proposed", "Scale the evidence before scaling the automation", "S1, S2, R1, R2", "PROPOSED ROLLOUT")
    stages = [("Event log", "Quote / gig /\nledger"), ("As-of features", "Only facts known\nat decision time"),
              ("Model registry", "Versions +\ncalibration"), ("Decision API", "Constraints +\none action writer"),
              ("Dispatcher", "Exceptions +\noverrides")]
    for i, (title, detail) in enumerate(stages):
        x = 42 + i * 180
        s.rect(x, 180, 156, 98, PALE, 7)
        s.text(x + 12, 193, 132, 28, title, 16, True)
        s.text(x + 12, 231, 132, 37, detail, 13)
        if i < 4:
            s.arrow(x + 160, 220, 15, 12)
    s.paragraph(42, 313, 268, "1 | Shadow",
                "Time-split, region-held-out forecasts. Audit labels and calibration before any action.", 118)
    s.paragraph(346, 313, 268, "2 | Controlled pilot",
                "Bounded quotes/fees, dispatcher approval and clustered evaluation of margin and delivery.", 118)
    s.paragraph(650, 313, 268, "3 | Gradual rollout",
                "Partition inference, coordinate shared drivers, monitor drift and retain rollback.", 118)
    s.text(42, 454, 876, 52, "Success = higher settled contribution without degrading promised delivery, booking retention or exception handling.",
           21, True, TEAL)
    s.notes = ("The repository is a simulator prototype, not a proven production dispatcher. A production design should "
               "persist events and as-of features, keep action and model identities, coordinate shared-driver reservations "
               "and use one writer/idempotent action handling. Partitioning inference does not make driver capacity independent. "
               "Shadow evaluation precedes a limited pilot; consider region/time-clustered experiments because pricing changes "
               "affect other jobs and driver behaviour. Measure settled contribution per completed order, promise adherence, "
               "booking latency, drop rates and human interventions, including real operating costs. Require data access, "
               "retention rules and privacy/security review with Bahn. Monitoring should detect miscalibration and region/time "
               "shift, with bounded actions and rollback. No production ROI or top-10 guarantee is claimed. The actual "
               "final outcome and availability incident must remain distinct from rehearsal and practice evidence.")
    slides.append(s)
    return slides


def render_pdf(slides, path):
    pdf = canvas.Canvas(str(path), pagesize=(W, H))
    pdf.setTitle("The Delusionals - Spread: technical evidence and ML roadmap")
    pdf.setAuthor("The Delusionals")
    for slide in slides:
        for item in slide.items:
            x, y, w, h = (item[k] for k in ("x", "y", "w", "h"))
            pdf.setFillColor(HexColor(item["color"]))
            if item["kind"] == "rect":
                pdf.roundRect(x, H - y - h, w, h, item["radius"], stroke=0, fill=1)
            elif item["kind"] == "arrow":
                p = pdf.beginPath()
                for i, (px, py) in enumerate(((x, y+h*.3), (x+w*.6, y+h*.3), (x+w*.6, y),
                                               (x+w, y+h*.5), (x+w*.6, y+h), (x+w*.6, y+h*.7), (x, y+h*.7))):
                    p.moveTo(px, H-py) if i == 0 else p.lineTo(px, H-py)
                p.close()
                pdf.drawPath(p, fill=1, stroke=0)
            else:
                pdf.setFont(item["font"], item["size"])
                for i, line in enumerate(item["lines"]):
                    pdf.drawString(x, H - y - item["size"]*.86 - i*item["leading"], line)
        pdf.showPage()
    pdf.save()


def rgb(value):
    return RGBColor.from_string(value.lstrip("#"))


def render_pptx(slides, path):
    deck = Presentation()
    deck.slide_width, deck.slide_height = Pt(W), Pt(H)
    deck.core_properties.title = "The Delusionals - Spread"
    deck.core_properties.subject = "Measured dispatch ideas and a proposed ML production roadmap"
    deck.core_properties.author = "The Delusionals"
    for spec in slides:
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        for item in spec.items:
            x, y, w, h = (Pt(item[k]) for k in ("x", "y", "w", "h"))
            if item["kind"] in ("rect", "arrow"):
                shape = MSO_SHAPE.RIGHT_ARROW if item["kind"] == "arrow" else MSO_SHAPE.ROUNDED_RECTANGLE if item["radius"] else MSO_SHAPE.RECTANGLE
                box = slide.shapes.add_shape(shape, x, y, w, h)
                box.fill.solid()
                box.fill.fore_color.rgb = rgb(item["color"])
                box.line.fill.background()
            else:
                box = slide.shapes.add_textbox(x, y, w, h)
                tf = box.text_frame
                tf.clear()
                tf.word_wrap = False
                tf.vertical_anchor = MSO_ANCHOR.TOP
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                for i, line in enumerate(item["lines"]):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.text = line
                    p.space_before = p.space_after = Pt(0)
                    p.line_spacing = Pt(item["leading"])
                    p.font.name = "Courier New" if item["font"] == "Courier" else "Arial"
                    p.font.size = Pt(item["size"])
                    p.font.bold = item["bold"]
                    p.font.color.rgb = rgb(item["color"])
        slide.notes_slide.notes_text_frame.text = spec.notes + "\n\nSources: " + spec.sources + ". See submission/SOURCES.md and evidence.json."
    deck.save(str(path))


def render_html(slides, path):
    sections = []
    for slide in slides:
        shapes = []
        for item in slide.items:
            style = (f"left:{item['x']}px;top:{item['y']}px;width:{item['w']}px;height:{item['h']}px;")
            if item["kind"] == "rect":
                style += f"background:{item['color']};border-radius:{item['radius']}px;"
                shapes.append(f'<div class="shape" style="{style}"></div>')
            elif item["kind"] == "arrow":
                style += f"background:{item['color']};clip-path:polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%);"
                shapes.append(f'<div class="shape" style="{style}"></div>')
            else:
                family = "Courier New,monospace" if item["font"] == "Courier" else "Arial,sans-serif"
                style += (f"color:{item['color']};font-size:{item['size']}px;line-height:{item['leading']}px;"
                          f"font-family:{family};font-weight:{700 if item['bold'] else 400};")
                shapes.append(f'<div class="shape text" style="{style}">' + "<br>".join(html.escape(line) for line in item["lines"]) + "</div>")
        sections.append(f'<section class="slide" aria-label="Slide {slide.number}: {html.escape(slide.title)}">' + "".join(shapes) + "</section>")
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Delusionals - Spread</title><style>
body{margin:0;background:#dfe7ef;font-family:Arial,sans-serif}.toolbar{padding:18px;text-align:center;font-size:15px}
.slide{position:relative;width:960px;height:540px;margin:24px auto;overflow:hidden;box-shadow:0 8px 30px #132d4625}
.shape{position:absolute;box-sizing:border-box}.text{white-space:nowrap}
button,a{margin:0 8px}details{max-width:920px;margin:20px auto;padding:16px;background:white;line-height:1.5}
@page{size:10in 5.625in;margin:0}@media print{.toolbar,details{display:none}.slide{margin:0;box-shadow:none;break-after:page;print-color-adjust:exact}.slide:last-of-type{break-after:auto}}
</style></head><body><div class="toolbar"><button onclick="window.print()">Print</button>
<a href="Spread-The-Delusionals.pdf">PDF</a><a href="Spread-The-Delusionals.pptx">Editable PowerPoint</a>
<a href="SOURCES.md">Sources</a><a href="SPEAKER_NOTES.md">Speaker notes</a></div>"""
    page += "".join(sections)
    page += "<details><summary>Read before submitting</summary>Review every slide. The real final result must not be replaced with a rehearsal score. Company statements, simulator evidence and future proposals are explicitly separated. Detailed assumptions and sources are in the speaker notes.</details></body></html>"
    path.write_text(page + "\n")


def review_exports(slides, pdf_path, pptx_path):
    import pymupdf
    from PIL import Image, ImageDraw

    presentation = Presentation(str(pptx_path))
    preview = Image.new("RGB", (1000, 1510), "#e5ebf1")
    normalise = lambda value: " ".join(value.split())
    with pymupdf.open(pdf_path) as document:
        if len(document) != len(slides) or len(presentation.slides) != len(slides):
            raise ValueError("Exported slide counts differ")
        for i, (page, slide) in enumerate(zip(document, slides)):
            expected = "\n".join("\n".join(item["lines"]) for item in slide.items if item["kind"] == "text")
            pptx_text = "\n".join(shape.text for shape in presentation.slides[i].shapes if shape.has_text_frame)
            if normalise(page.get_text()) != normalise(expected) or normalise(pptx_text) != normalise(expected):
                raise ValueError(f"Slide {i + 1}: exported text differs from the authored layout")
            if not presentation.slides[i].notes_slide.notes_text_frame.text.strip():
                raise ValueError(f"Slide {i + 1}: speaker notes missing")
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        if not (0 <= x0 < x1 <= W + .5 and 0 <= y0 < y1 <= H + .5):
                            raise ValueError(f"Slide {i + 1}: text outside the PDF page")
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples).resize((480, 270))
            x, y = 10 + (i % 2) * 500, 10 + (i // 2) * 300
            preview.paste(image, (x, y))
            ImageDraw.Draw(preview).text((x + 4, y + 276), f"Slide {i + 1}", fill=NAVY)
    preview.save(HERE / "preview.png")


def main():
    evidence = json.loads((HERE / "evidence.json").read_text())
    slides = story(evidence)
    if len(slides) != 10:
        raise ValueError("The judging deck must have exactly 10 slides")
    pdf, pptx = HERE / "Spread-The-Delusionals.pdf", HERE / "Spread-The-Delusionals.pptx"
    render_pdf(slides, pdf)
    render_pptx(slides, pptx)
    render_html(slides, HERE / "slides.html")
    review_exports(slides, pdf, pptx)
    (HERE / "SPEAKER_NOTES.md").write_text(
        "# Speaker notes\n\nReview every claim before presenting. Source IDs resolve in [SOURCES.md](SOURCES.md).\n\n"
        + "\n\n".join(f"## {s.number}. {s.title}\n\n{s.notes}\n\nSources: {s.sources}." for s in slides) + "\n")
    (HERE / "deck-layout.json").write_text(json.dumps([{"number": s.number, "title": s.title, "items": s.items} for s in slides], indent=2) + "\n")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
              (Path(__file__), HERE/"build_evidence.py", HERE/"evidence.json", HERE/"SOURCES.md",
               HERE/"SPEAKER_NOTES.md", HERE/"requirements.txt", HERE/"deck-layout.json",
               pdf, pptx, HERE/"slides.html", HERE/"preview.png")}
    (HERE / "build-manifest.json").write_text(json.dumps({
        "slides": len(slides), "size_points": [W, H], "fit_window": None, "hashes": hashes,
        "packages": {name: importlib.metadata.version(name) for name in ("python-pptx", "reportlab", "PyMuPDF", "Pillow", "lxml", "XlsxWriter")},
        "real_final_result_available": evidence["final_result"] is not None,
    }, indent=2) + "\n")
    print(f"Exported {len(slides)} slides to PDF, editable PPTX and HTML; speaker notes and source evidence included.")


if __name__ == "__main__":
    main()
