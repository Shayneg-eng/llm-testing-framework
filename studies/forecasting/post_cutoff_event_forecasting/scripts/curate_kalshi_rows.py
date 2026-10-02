#!/usr/bin/env python3
"""S013: turn runs/kalshi_shortlist_rows.psv (316 shortlisted Kalshi rungs, collected via the browser)
into runs/shortlist.jsonl + runs/curation.jsonl for build_items.py finalize.

Row format (pipe separated, no header):
  ticker(no KX) | yes_subtitle | close_ts-1788000000 | hours_t0_before_close('' = 24) | t0_price | outcome(1=YES) | game_desc | game_date
Category comes from row position (sports 0-90, econ 91-181, politics 182-231, culture 232-315).
Statements/negations are templated per Kalshi series; anything unknown is reported so it can be patched.
"""
import json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
BASE = 1788000000
CATS = [("sports", 0, 91), ("economics_finance", 91, 182), ("politics_world", 182, 232), ("culture_science_tech", 232, 316)]
MON = {"AUG": 8, "SEP": 9, "OCT": 10}
MNAME = {8: "Aug", 9: "Sep", 10: "Oct"}

DROP = {  # ticker -> reason
    "CANCTRTARIFF-26": "title truncated/ambiguous", "GENERICBALLOTVOTEHUB-26SEP04-T5.9": "metric definition unclear",
    "AMSAVO-26SEP25-T1.10": "unit/spec unclear", "AMSAVO-26SEP04-T1.10": "unit/spec unclear",
    "POTUSTWEETS-26SEP01-0": "bucket unclear", "BILLBOARDRUNNERUPALBUM-26SEP19-YOU": "chart unclear",
    "YTVIEWSW-KEN26SEP06-7.0M": "window unclear", "YTVIEWSW-ARI26AUG30-20.0M": "window unclear",
    "PUREALBUMS-OW26SEP17-8K": "window unclear", "H200W-26SEP04-4.49": "spec unclear", "H100W-26SEP04-2.93": "spec unclear",
    "YTTOPVIDEOG2D-26AUG31-FAL": "chart unclear",
}


def dt(t, off=0):
    m = re.search(r"-26(AUG|SEP|OCT)(\d\d)", t)
    if not m:
        return ""
    d = datetime(2026, MON[m.group(1)], int(m.group(2))) + timedelta(days=off)
    return f"{MNAME[d.month]} {d.day}, 2026"


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def thr(y, pre="", pl=False):
    was = "were" if pl else "was"
    y = y.strip()

    def v(s):
        s = s.strip()
        return pre + s if pre and not s.startswith("$") else s
    m = re.match(r"^Above\s+(.+)$", y)
    if m: return f"{was} above {v(m.group(1))}", f"{was} at or below {v(m.group(1))}"
    m = re.match(r"^At least\s+(.+)$", y)
    if m: return f"{was} at least {v(m.group(1))}", f"{was} below {v(m.group(1))}"
    m = re.match(r"^(.+?) or [Aa]bove$", y)
    if m: return f"{was} {m.group(1)} or above", f"{was} below {m.group(1)}"
    m = re.match(r"^<\s*(.+)$", y)
    if m: return f"{was} below {m.group(1)}", f"{was} {m.group(1)} or above"
    m = re.match(r"^Exactly\s+(.+)$", y)
    if m: return f"{was} exactly {m.group(1)}", f"{was} not exactly {m.group(1)}"
    m = re.match(r"^([\d,.]+[°%]?)\s*(?:to|-)\s*([\d,.]+[°%]?)$", y)
    if m: return f"{was} between {m.group(1)} and {m.group(2)} (inclusive)", f"{was} not between {m.group(1)} and {m.group(2)} (inclusive)"
    m = re.match(r"^[\d.]+%$", y)
    if m: return f"{was} exactly {y}", f"{was} not exactly {y}"
    m = re.match(r"^\d+$", y)
    if m: return f"{was} exactly {y}", f"{was} not exactly {y}"
    return None


def S(subj, y, pre="", pl=False):
    r = thr(y, pre, pl)
    if r is None:
        raise KeyError(f"unparsed ys {y!r} for {subj!r}")
    return f"{subj} {r[0]}.", f"{subj} {r[1]}."


def P(a, b):
    return a + ".", b + "."


CITY = {"LOWTLV": "Las Vegas", "LOWTSEA": "Seattle", "LOWTBOS": "Boston", "LOWTATL": "Atlanta", "HIGHAUS": "Austin", "LOWTSFO": "San Francisco",
        "HIGHTOKC": "Oklahoma City", "LOWTCHI": "Chicago", "LOWTPHIL": "Philadelphia", "HIGHTDC": "Washington, D.C.", "HIGHCHI": "Chicago",
        "HIGHNY": "New York City", "LOWTPHX": "Phoenix", "HIGHTNOLA": "New Orleans", "HIGHTLV": "Las Vegas", "LOWTSATX": "San Antonio",
        "HIGHPHIL": "Philadelphia"}
EMMY = {"EMMYDSACTR": "Outstanding Supporting Actress in a Drama Series", "EMMYDSACTO": "Outstanding Supporting Actor in a Drama Series",
        "EMMYCSACTR": "Outstanding Supporting Actress in a Comedy Series", "EMMYCSACTO": "Outstanding Supporting Actor in a Comedy Series",
        "EMMYDACTR": "Outstanding Lead Actress in a Drama Series", "EMMYCSERIES": "Outstanding Comedy Series",
        "EMMYLIMITEDACTO": "Outstanding Lead Actor in a Limited or Anthology Series or Movie",
        "EMMYLIMITEDACTR": "Outstanding Lead Actress in a Limited or Anthology Series or Movie"}
SOFR = {"26SEP21": "Sep 18, 2026", "26SEP08": "Sep 4, 2026", "26SEP14": "Sep 11, 2026"}
COMM = {"COPPERD": "copper close price (USD per pound; 1-minute candlestick at 5:00 PM EDT)", "COPPERW": "copper close price (USD per pound; 1-minute candlestick at 5:00 PM EDT)",
        "GOLDD": "gold close price (USD per troy ounce; 1-minute candlestick at 5:00 PM EDT)", "GOLDW": "gold close price (USD per troy ounce; 1-minute candlestick at 5:00 PM EDT)",
        "BRENTD": "Brent crude oil close price (USD per barrel; 1-minute candlestick at 5:00 PM EDT)", "BRENTW": "Brent crude oil close price (USD per barrel; 1-minute candlestick at 5:00 PM EDT)",
        "NATGASW": "natural gas close price (USD per MMBtu; 1-minute candlestick at 5:00 PM EDT)", "WTI": "WTI crude oil daily settlement price (USD per barrel)"}
TW = {"IMFTWEETS": "@IMFNews", "WEFTWEETS": "@wef", "FEDTWEETS": "@federalreserve"}
PW = {"BABELMANDEBWEEKLY": "the Bab el-Mandeb Strait", "SUEZWEEKLY": "the Suez Canal", "PANAMAWEEKLY": "the Panama Canal", "HORMUZWEEKLY": "the Strait of Hormuz"}
SHARE = {"BABASHARE": "Qwen", "OPENSHARE": "OpenAI", "GOOGSHARE": "Google", "ANTHSHARE": "Anthropic", "DEEPSHARE": "DeepSeek"}
RAMP = {"AIADOPTION": "The Ramp AI Index overall AI adoption rate for August 2026", "AIFOOD": "The Ramp AI Index adoption rate for the Accommodation and food services sector for August 2026",
        "AITECH": "The Ramp AI Index adoption rate for the Technology and media sector for August 2026", "OPENADOPT": "The Ramp AI Index OpenAI model adoption rate for August 2026",
        "AISPEND10": "The Ramp AI Index spend per employee (top 10%) for August 2026"}
CB = {"CBDSA": "The South African Reserve Bank at its September 2026 Monetary Policy Committee meeting", "CBDNORWAY": "Norges Bank at its September 2026 monetary policy meeting",
      "CBDINDONESIA": "Bank Indonesia at its September 2026 Board of Governors meeting"}
GAME_SUBJ = None


def sports(r, y, desc, date):
    soccer = "soccer" in (desc or "")
    reg = ", counting only 90 minutes plus stoppage time (extra time excluded)" if soccer else ""
    pre = f"In the {desc} on {date}, "
    m = re.match(r"^(?:Reg Time: )?Over ([\d.]+) (goals|points|runs)", y)
    if m: return P(pre + f"more than {m.group(1)} total {m.group(2)} were scored{reg}", pre + f"at most {m.group(1)} total {m.group(2)} were scored{reg}")
    if y == "Tie": return P(f"The {desc} on {date} ended in a tie{reg}", f"The {desc} on {date} did not end in a tie{reg}")
    m = re.match(r"^(.+) wins by (?:more than|over) ([\d.]+) (goals|points)$", y)
    if m: return P(pre + f"{m.group(1)} won by more than {m.group(2)} {m.group(3)}{reg}", pre + f"{m.group(1)} did not win by more than {m.group(2)} {m.group(3)}{reg}")
    if y == "Neither team reaches 7 points": return P(pre + "neither team scored 7 or more points", pre + "at least one team scored 7 or more points")
    if y == "New England reaches 7 points first": return P(pre + "New England was the first team to score 7 points", pre + "New England was not the first team to score 7 points")
    t = y.replace("Reg Time: ", "")
    lost = "it drew or lost" if soccer else "it lost"
    return P(pre + f"{t} won{reg}", pre + f"{t} did not win ({lost}){reg}")


def econ_pol_cult(t, y):
    s = t.split("-")[0]
    d = dt(t)
    if s == "AAAGASWNJ": return S(f"The AAA average price of regular gas in New Jersey on {d}", y, "$")
    if s == "AAAGASW": return S(f"The AAA national average price of regular gas on {d}", y, "$")
    if s == "AAAGASMAXM": return P("The AAA national average price of regular gas rose above $4.20 at some point on or before Sep 30, 2026", "The AAA national average price of regular gas did not rise above $4.20 at any point on or before Sep 30, 2026")
    if s in COMM: return S(f"The {COMM[s]} on {d}", y, "$")
    if re.match(r"^(USD[A-Z]{3}|NZDUSD|EURUSD)", s):
        pair = re.sub(r"AW$", "", s)
        return S(f"The {pair} exchange rate (opening candlestick value at 5pm ET) on {d}", y)
    if s in ("B200WS", "H100WS", "H200WS"): return S(f"The NVIDIA {s[:4]} compute price per hour (USD; reference index) at 4 PM ET on {d}", y, "$")
    if s == "NASDAQDUD": return S(f"The NASDAQ-100 end-of-day price on {d}", y)
    if s == "INXDUD": return S(f"The S&P 500 end-of-day price on {d}", y)
    if s == "INX": return S(f"The S&P 500 end-of-day value on {d}", y)
    if s == "SP500ADDQ": return P("Pure Storage was added to the S&P 500 between July 1 and September 30, 2026", "Pure Storage was not added to the S&P 500 between July 1 and September 30, 2026")
    if s == "30YMORTW": return S(f"The average U.S. 30-year fixed-rate mortgage rate for {d}", y)
    if s == "TSAW": return S(f"The average number of people screened per day by the TSA over the week ending {d}", y)
    if s == "JOBLESSCLAIMS": return S(f"Initial U.S. jobless claims for the week ending {dt(t, -5)}", y, "", True)
    if s == "CONTCLAIMS": return S(f"U.S. seasonally adjusted continuing unemployment insurance claims for the week ending {dt(t, -12)}", y, "", True)
    if s == "SOFRD":
        k = re.search(r"-(26SEP\d\d)-", t).group(1)
        return S(f"The Secured Overnight Financing Rate (SOFR) for {SOFR[k]}", y)
    if s in TW: return S(f"The number of posts, quote posts and reposts (excluding replies) by {TW[s]} on X in the weekly window ending {d} at 12:00 PM ET", y)
    if t.startswith("UE-"):
        c, mo = ("Russia", "July 2026") if "RUS" in t else ("Australia", "August 2026")
        return S(f"{c}'s unemployment rate for {mo}", y)
    if s in CB:
        return P(CB[s] + " hiked its policy rate by 1-25bps", CB[s] + " did not hike its policy rate by 1-25bps")
    if s == "CBDHUNGARY": return P("The Magyar Nemzeti Bank at its September 2026 Monetary Council meeting cut its base rate by more than 50bps", "The Magyar Nemzeti Bank at its September 2026 Monetary Council meeting did not cut its base rate by more than 50bps")
    if s == "CFNAI": return S("The Chicago Fed National Activity Index for August 2026", y)
    if s == "BUILDPERMS": return S("US building permits (total units, SAAR) for August 2026", y, "", True)
    if s == "HOUSINGSTART": return S("US housing starts (SAAR) for August 2026", y, "", True)
    if s == "NHSALES": return S("US new home sales (SAAR) for August 2026", y, "", True)
    if s == "USHOME": return S("The median sales price of new houses sold in the United States (MSPNHSUS) for August 2026", y)
    if s == "SARETAIL": return S("South Africa's retail sales (month-over-month change) for July 2026", y)
    if s == "UKRETAIL": return S("United Kingdom retail sales (month-over-month change) for August 2026", y)
    if s == "SAMOMINF": return S("South Africa's month-over-month inflation rate for August 2026", y)
    if s == "PAYROLLS": return S("The change in total non-farm payroll employment (BLS) for August 2026", y)
    if s == "U3": return S("The U.S. unemployment rate (U-3) for August 2026", y)
    if s == "USLEI": return S("The month-over-month change in The Conference Board U.S. Leading Economic Index for August 2026", y)
    if s == "AAPLPRICEFOLD": return S("The price of Apple's foldable iPhone", y)
    # politics / world
    if s == "TRUMPVH": return S(f"Donald Trump's approval rating in the VoteHub polling average on {d}", y)
    if s == "APRPOTUS": return S(f"President Trump's approval rating (per the designated polling-average source) on {d}", y)
    if s == "TRUMPAPPROVE": return S(f"Donald Trump's RealClearPolitics approval average on {d}", y)
    if s == "HORMUZMAX": return P(f"{y} was the single day with the most transit calls through the Strait of Hormuz (IMF PortWatch) in the week ending {d}", f"{y} was not the single day with the most transit calls through the Strait of Hormuz (IMF PortWatch) in the week ending {d}")
    if s == "HORMUZPEAK": return S(f"The highest single-day number of transit calls through the Strait of Hormuz (IMF PortWatch) in the week ending {d}", y)
    if s in PW: return S(f"The number of transit calls through {PW[s]} (IMF PortWatch) in the week ending {d}", y)
    if s == "TRUMPENDORSEMENTS":
        n = re.search(r"(\d+)", y).group(1)
        return P(f"Donald Trump endorsed at least {n} people on Truth Social in the week ending {d}", f"Donald Trump endorsed fewer than {n} people on Truth Social in the week ending {d}")
    if s == "TRUTHSOCIAL": return S(f"The number of Truth Social posts made by Donald Trump in the week ending {d}", y)
    if s == "TRUMPPHOTO": return S(f"The number of distinct days on which Donald Trump appeared in a tagged editorial Getty Images photo in the week ending {d}", y)
    if s == "VOTESWEDEN":
        party = "Green Party" if "GREEN" in t else "Swedish Social Democratic Party"
        n = re.search(r"(\d+)", y).group(1)
        return P(f"The {party} received at least {n}% of the popular vote in the Swedish general election of Sep 13, 2026", f"The {party} received less than {n}% of the popular vote in the Swedish general election of Sep 13, 2026")
    if s == "SWEDEN4TH": return P("The Centre Party finished 4th in the Swedish general election of Sep 13, 2026", "The Centre Party did not finish 4th in the Swedish general election of Sep 13, 2026")
    if s == "BERLINSTATE": return P(f"{y} won (finished first in) the Berlin state election of Sep 20, 2026", f"{y} did not win (finish first in) the Berlin state election of Sep 20, 2026")
    if s == "MECKLENBURGVORPOMMERN": return P(f"{y} won (finished first in) the Mecklenburg-Vorpommern state election of Sep 20, 2026", f"{y} did not win (finish first in) the Mecklenburg-Vorpommern state election of Sep 20, 2026")
    if s == "OKINAWAGOV": return P(f"{y} won the Okinawa gubernatorial election of Sep 13, 2026", f"{y} did not win the Okinawa gubernatorial election of Sep 13, 2026")
    if s == "AGNOMRID": return P(f"{y} won the 2026 Democratic nomination for Attorney General of Rhode Island", f"{y} did not win the 2026 Democratic nomination for Attorney General of Rhode Island")
    if s == "DEALR": return P(f"{y} won the 2026 Republican nomination for Delaware's at-large congressional district", f"{y} did not win the 2026 Republican nomination for Delaware's at-large congressional district")
    if s == "MTGSWITCH": return P("Marjorie Taylor Greene left the Republican Party during the market's window (through January 2027)", "Marjorie Taylor Greene did not leave the Republican Party during the market's window (through January 2027)")
    if s == "SNAPELECTIONRS": return P("Serbia announced a snap election before Sep 1, 2026", "Serbia did not announce a snap election before Sep 1, 2026")
    # culture / science / tech
    if s in CITY:
        kind = "minimum" if s.startswith("LOWT") else "maximum"
        return S(f"The {kind} temperature (°F) in {CITY[s]} on {d}", y)
    if s in RAMP: return S(RAMP[s], y, "$" if s == "AISPEND10" else "")
    if s in SHARE: return S(f"{SHARE[s]}'s market share in the weekly AI market-share ranking for the week of {d}", y)
    if s == "TOPUSAGEAI": return P(f"{y} was the most popular AI (by usage) for the week of {d}", f"{y} was not the most popular AI (by usage) for the week of {d}")
    if s == "VIDEOAI": return P(f"{y} was the top text-to-video AI for the week ending {d}", f"{y} was not the top text-to-video AI for the week ending {d}")
    if s == "CHINAAI": return P(f"{y} was the top Chinese AI company for the week of September 14, 2026", f"{y} was not the top Chinese AI company for the week of September 14, 2026")
    if s == "TOKENUSE":
        return S(f"Total OpenRouter token usage for {dt(t, -7)[:-6]}-{dt(t, -1)}", y)
    if s == "OPENSOURCESHARE": return S(f"The open-weights share in the 'Open vs. Closed Token Volume' metric for {dt(t, -1)}", y)
    if s == "NETFLIXTOPVIEWSMOVIE": return S(f"The number of views of the #1 movie in Netflix's weekly Top 10 (market date {d})", y)
    if s == "NETFLIXTOPVIEWSTV": return S(f"The number of views of the #1 show in Netflix's weekly Top 10 (market date {d})", y)
    if s == "NETFLIXRANKMOVIE": return P(f"{y} was the #1 movie on Netflix in the US on {d}", f"{y} was not the #1 movie on Netflix in the US on {d}")
    if s == "NETFLIXRANKSHOWGLOBAL2": return P(f"{y} was the #2 show on Netflix globally on {d}", f"{y} was not the #2 show on Netflix globally on {d}")
    if s in EMMY: return P(f"{y} won the 78th Primetime Emmy Award for {EMMY[s]}", f"{y} did not win the 78th Primetime Emmy Award for {EMMY[s]}")
    if s == "EMMYCOUNT":
        show = {"HAC": "Hacks", "PIT": "The Pitt"}[t.split("-")[1][2:]]
        n = re.search(r"(\d+)", y).group(1)
        return P(f"{show} won exactly {n} award(s) at the 78th Emmy Awards", f"{show} did not win exactly {n} award(s) at the 78th Emmy Awards")
    if s in ("BIGBROTHERELIMINATION", "AGTELIMINATION"):
        show = "Big Brother Season 28" if s.startswith("BIG") else "America's Got Talent Season 21"
        return P(f"{y} was eliminated from {show} on or before {d}", f"{y} was not eliminated from {show} on or before {d}")
    if s == "DWTSELIMINATION": return P(f"{y} and their partner were eliminated from Dancing with the Stars on or before {dt(t)}", f"{y} and their partner were not eliminated from Dancing with the Stars on or before {dt(t)}")
    if s == "GROK": return P("SpaceXAI released Grok 4.7 before Sep 25, 2026", "SpaceXAI did not release Grok 4.7 before Sep 25, 2026")
    if s == "ALBUMRELEASE": return P("Beyoncé released a new album in 2026", "Beyoncé did not release a new album in 2026")
    if s == "ALBUMRELEASEDATEBEY": return P(f"Beyoncé released a new album {y[0].lower()+y[1:]}", f"Beyoncé did not release a new album {y[0].lower()+y[1:]}")
    if s == "TIFF": return P(f"{y} won the People's Choice Award at the 2026 Toronto International Film Festival", f"{y} did not win the People's Choice Award at the 2026 Toronto International Film Festival")
    if s == "FRAGRANCE": return S("The price of Creed Aventus in August 2026 (per the market's price source)", y, "$")
    if s == "NEWDRUGAPPNTLA":
        w = "before January 1, 2027" if "27JAN01" in t else "before November 1, 2026"
        return P(f"Intellia Therapeutics submitted a BLA for lonvoguran ziclumeran {w}", f"Intellia Therapeutics did not submit a BLA for lonvoguran ziclumeran {w}")
    if s == "COLLEGEDROP": return P(f"{y} dropped in the national university rankings (2027 edition)", f"{y} did not drop in the national university rankings (2027 edition)")
    raise KeyError(f"no template for series {s} ({t})")


def event_id(t, cat):
    if cat == "sports":
        m = re.search(r"-(26[A-Z]{3}\d{2}(?:\d{4})?[A-Z0-9]+?)(?:-[A-Z0-9.]+)?$", t)
        if m and not t.startswith(("SAILGPRACE", "F1RACE", "ATPNATWINNER")):
            return m.group(1).lower()
    if t.startswith(("ALBUMRELEASE-26-BEY", "ALBUMRELEASEDATEBEY")): return "beyonce-new-album-2026"
    p = t.split("-")
    return "-".join(p[:-1] if len(p) >= 3 else p).lower()


def main():
    rows = [ln.rstrip("\n").split("|") for ln in (RUNS / "kalshi_shortlist_rows.psv").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 316, len(rows)
    short, cur, errors, seen_team = [], [], [], {}
    for i, r in enumerate(rows):
        r += [""] * (8 - len(r))
        t, y, ct, dh, price, out, desc, date = r[:8]
        cat = next(c for c, a, b in CATS if a <= i < b)
        ct = BASE + int(ct); dh = int(dh) if dh else 24
        ev = event_id(t, cat)
        short.append({"market_ticker": "KX" + t, "event_ticker": "KX" + ev.upper(), "series_ticker": "KX" + t.split("-")[0], "category": cat,
                      "t0": iso(ct - dh * 3600), "resolved_at": iso(ct), "t0_price": float(price), "outcome": int(out), "yes_subtitle": y,
                      "event_title": "", "rules_primary": ""})
        rec = {"market_ticker": "KX" + t, "event_id": ev, "resolution_criteria": ""}
        try:
            if t in DROP:
                st = ("(dropped)", "(dropped)")
            elif cat == "sports":
                if t.startswith("ATPMATCH"): st = P("Martin Damm Jr won his 2026 US Open men's singles round-of-128 match against Tiafoe (scheduled Aug 30, 2026)", "Martin Damm Jr did not win his 2026 US Open men's singles round-of-128 match against Tiafoe (scheduled Aug 30, 2026)")
                elif t.startswith("ATPNATWINNER"): st = P("An American man or woman won a 2026 US Open singles title (men's or women's)", "No American man or woman won a 2026 US Open singles title (men's or women's)")
                elif t.startswith("SAILGPRACE"): st = P("Red Bull Italy won the 2026 Spain Sail Grand Prix", "Red Bull Italy did not win the 2026 Spain Sail Grand Prix")
                elif t.startswith("F1RACE"): st = P("Charles Leclerc won the main race at the 2026 Italian Grand Prix (Sep 6, 2026)", "Charles Leclerc did not win the main race at the 2026 Italian Grand Prix (Sep 6, 2026)")
                else: st = sports(r, y, desc, date)
                rec["resolution_criteria"] = "Resolved by the official final result of the event (for soccer, regulation time: 90 minutes plus stoppage time, extra time excluded)."
                is_team = not (y == "Tie" or y.startswith(("Over", "Reg Time: Over")) or " wins by " in y or "reaches 7" in y or t.startswith(("ATPNAT", "SAIL", "F1", "ATPM")))
                if is_team:
                    if ev in seen_team: rec["drop"] = True; rec["drop_reason"] = "second team-win rung of the same game"
                    seen_team.setdefault(ev, t)
            else:
                st = econ_pol_cult(t, y)
                rec["resolution_criteria"] = "Resolves YES if the statement is true according to the official or primary published source for the stated date/period (as defined in the market rules)."
        except KeyError as e:
            errors.append(f"{i} {t}: {e}"); continue
        rec["statement"], rec["negated_statement"] = st
        if t in DROP: rec["drop"] = True; rec["drop_reason"] = DROP[t]
        cur.append(rec)
    for name, data in (("shortlist.jsonl", short), ("curation.jsonl", cur)):
        (RUNS / name).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in data), encoding="utf-8")
    print(f"shortlist {len(short)}, curated {len(cur)}, dropped {sum(1 for c in cur if c.get('drop'))}, errors {len(errors)}")
    for e in errors: print("ERR", e)


if __name__ == "__main__":
    main()
