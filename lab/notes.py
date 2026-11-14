"""Note reader v3: earliest pickup time ("not before") from dealer notes in Finnish, Swedish, English.

RULES "Notes": days count from the arrival day; today/tomorrow/day-after words; a weekday name is 2..6 days after
arrival; digits are a 24 h clock unless am/pm; an hour in WORDS is the working hour 9..17 ("two" = 14:00,
"half three" = 14:30); a correction counts; a denied time ("not 3pm") does not.
Returns the earliest pickup world-minute implied by the note, or None. Evaluated against reveal truth (see EXPERIMENTS).
"""
from __future__ import annotations

import re
from typing import Optional

DAY = 1440
REL = [(re.compile(r"ylihuomenna|i övermorgon|övermorgon|dayaftertomorrow"), 2),
       (re.compile(r"huomenna|huomisaamuna|huomen|i morr?gon|imorr?gon|tomm?orr?o?w|tomorow|tomororw|tmrw|\btmr\b"), 1),
       (re.compile(r"tänään|tänne|idag|i dag|today"), 0)]
WEEKDAYS = {0: r"maanantai\w*|\bma\b|måndag\w*|\bmån\b|monday|\bmon\b",
            1: r"tiistai\w*|\bti\b|tisdag\w*|\btis\b|tuesday|\btues?\b",
            2: r"keskiviikko\w*|\bke\b|onsdag\w*|\bons\b|wednesday|\bwed\b",
            3: r"torstai\w*|\bto\b|torsdag\w*|\btors?\b|thursday|\bthu(rs)?\b",
            4: r"perjantai\w*|\bpe\b|fredag\w*|\bfre\b|friday|\bfri\b"}
WD = {d: re.compile(p) for d, p in WEEKDAYS.items()}
READY = re.compile(r"readyfrom|valmi|vlami|vasta|maksu|maksettu|maksaa|aikaisintaan|alkaen|jälkeen|ei ennen|noudettavissa|haettavissa|saa hakea|auton saa|luovut|"
                   r"klar|tidigast|efter|inte före|förrän|hämtas|framåt|"
                   r"ready|not before|not beofre|earliest|after|available|from\b|onwards|collect|payment|paid|clears|released|until")
STOP = re.compile(r"ennen|viim|mennessä|asti|sulke|kiinni|auki|aukiolo|"
                  r"före|senast|till\b|stänger|öppet|öppettid|"
                  r"before|no later|latest|until|closes?|open\b|opening")
DELIV = re.compile(r"toimit|perillä|perille|vastaanot|deliver|arrive|destination|leverera|leverans|framme|mottag")
NUM_FI = {"yhdestätoista": 11, "kahdestatoista": 12, "yhde": 1, "kahde": 2, "kolme": 3, "nelj": 4, "viide": 5, "yhdeks": 9, "kymmene": 10, "yhdentoista": 11, "kahdentoista": 12}
NUM_SV = {"ett": 1, "två": 2, "tre": 3, "fyra": 4, "fem": 5, "nio": 9, "tio": 10, "elva": 11, "tolv": 12}
NUM_EN = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
WORD_FI = re.compile(r"(puoli\s+)?(yhdestätoista|kahdestatoista|yhdeltätoista|kahdeltatoista|yhdeltä|yhdelta|kahdelta|kolmelta|neljältä|viideltä|yhdeksältä|kymmeneltä|yhdestä|kahdesta|kolmesta|neljästä|viidestä)")
WORD_SV = re.compile(r"(halv\s+)?\b(ett|två|tre|fyra|fem|nio|tio|elva|tolv)\b")
WORD_EN = re.compile(r"(half\s+)?\b(one|two|three|four|five|nine|ten|eleven|twelve)\b(?!\s*(cars?|keys?|days?|hours?))")
CLOCK = re.compile(r"\b(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)?\b")


def _work_hour(n: int) -> int:
    return n + 12 if 1 <= n <= 5 else n          # working hour 9..17


def _fi_num(w: str) -> int:
    if w.startswith("yhdestätoista"):
        return 11
    if w.startswith("kahdestatoista"):
        return 12
    w = w.replace("ltätoista", "ntoista").replace("ltä", "").replace("lta", "")
    if w.startswith("yhdentoista") or w.startswith("yhdeltätoista"):
        return 11
    if w.startswith("kahdentoista") or w.startswith("kahdeltatoista"):
        return 12
    for k, v in NUM_FI.items():
        if w.startswith(k):
            return v
    return 0


def _times(clause: str):
    """(minute, position) candidates: digits, then hours in words."""
    out = []
    for m in CLOCK.finditer(clause):
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "")
        pre, post = clause[max(0, m.start() - 3):m.start()], clause[m.end():m.end() + 3]
        if re.search(r"[-–]\s*$", pre) or re.match(r"\s*[-–]", post):
            continue                                   # a range: opening hours
        if not m.group(2) and not ap and not re.search(r"(klo|kl\.?|at|@|kello)\s*$", clause[max(0, m.start() - 7):m.start()]):
            continue                                   # bare number without a clock marker
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        if h <= 23 and mi <= 59:
            out.append((h * 60 + mi, m.start()))
    for m in WORD_FI.finditer(clause):
        n = _fi_num(m.group(2))
        if n:
            out.append((_work_hour(n) * 60 - (30 if m.group(1) else 0), m.start()))
    for rx, table in ((WORD_SV, NUM_SV), (WORD_EN, NUM_EN)):
        for m in rx.finditer(clause):
            n = table[m.group(2)]
            if re.search(r"(klockan|kl|at|by|from|efter|after|halv|half)\s*$", clause[max(0, m.start() - 9):m.start()]) or m.group(1):
                out.append((_work_hour(n) * 60 - (30 if m.group(1) else 0), m.start()))
    return out


ABBR = re.compile(r"\b(viim|klo|kl|esim|n|ca|noin|ma|ti|ke|to|pe|la|su|mon|tue|wed|thu|fri)\.")
WDRANGE = re.compile(r"\b(ma|ti|ke|to|pe|la|su|mon|tue|wed|thu|fri|mån|tis|ons|tors|fre)\w*\s*[-–]\s*(ma|ti|ke|to|pe|la|su|mon|tue|wed|thu|fri|sat|sun|mån|tis|ons|tors|fre|lör|sön)\w*")


def ready_time(text: str, arrived_at: int) -> Optional[int]:
    """Earliest pickup minute implied by the note, or None."""
    if not text:
        return None
    t = text.lower()
    t = re.sub(r"\b(not|no|isn't|won't be)\s+(ready|available|pickup|collection|released?)?\s*(before|until|till)\b", " readyfrom ", t)
    t = re.sub(r"\b(ei|eikä)\s+(valmis|valmiina|noudettavissa)?\s*ennen\b|\binte\s+(klar\s+)?(före|förrän)\b", " readyfrom ", t)
    t = t.replace("day after tomorrow", "dayaftertomorrow").replace("noon", "klo 12").replace("puolilta päivin", "klo 12")
    t = ABBR.sub(lambda m: m.group(1) + " ", t)     # abbreviation dots don't end a clause
    t = WDRANGE.sub(" ", t)                           # weekday ranges are opening hours
    t = re.sub(r"(\d{1,2})\s*:?\s*(sta|stä|ista|istä)\b", r"klo \1", t)   # "12:sta alkaen" = from 12
    t = re.sub(r"(huomenna|tänään|tomorrow|tmrw|i morgon|idag|today)\s+(\d{1,2})\b(?![.:]\d)", r"\1 klo \2", t)
    if not READY.search(t):
        return None
    day0 = arrived_at // DAY
    best, off_carry = None, None
    clauses = re.split(r"(?<!\d)[.;!?](?!\d)|\n|\bkorjaus\b|\bcorrection\b|\brättelse\b|\bkorrigering\b", t)
    for clause in clauses:
        if not clause.strip():
            continue
        if DELIV.search(clause) and not READY.search(clause):
            continue
        off = None
        for rx, k in REL:
            if rx.search(clause):
                off = k
                break
        if off is None:
            for d, rx in WD.items():
                if rx.search(clause):
                    off = (d - day0 % 7) % 7
                    if off < 2:
                        off += 7
                    break
        cands = []
        for minute, pos in _times(clause):
            win = clause[max(0, pos - 28):pos + 12]
            neg = re.search(r"\b(not|ei|inte)\s+(\w+\s+)?$", clause[max(0, pos - 12):pos])
            pre = clause[max(0, pos - 28):pos]
            s_pos = [m.end() for m in STOP.finditer(pre)]
            r_pos = [m.end() for m in READY.finditer(pre)]
            post = clause[pos:pos + 14]
            if neg or (s_pos and (not r_pos or max(s_pos) > max(r_pos))) or (not r_pos and not s_pos and STOP.search(post) and not READY.search(post)):
                continue
            cands.append(minute)
        has_ready = bool(READY.search(clause))
        if off is None and not cands:
            continue
        if not has_ready and not cands and off is not None and best is None:
            continue
        if off is None:
            off = off_carry if off_carry is not None else 0
        off_carry = off
        minute = cands[-1] if cands else (8 * 60 if off else None)
        if minute is None:
            continue
        best = (day0 + off) * DAY + minute
    return best
