"""S013 mechanical leak checks for pre-event briefs. Pure functions. Tested by test_leak_check.py.

Hard failures (item must be rewritten): too long, mentions prediction markets / betting terms,
no sources, a source published on/after t0, a date after the resolution date.
Warnings (an LLM checker and the human audit look at these): dates between t0 and resolution,
outcome-revealing words.
"""
import re
from datetime import date

from select_lib import parse_ts

_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
         "October", "November", "December"]
MONTHS = {m: i for i, m in enumerate(_FULL, 1)}
MONTHS.update({"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9,
               "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12})
_MON = "|".join(sorted(MONTHS, key=len, reverse=True))
ISO = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")
LONG = re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b")
MARKET_WORDS = re.compile(r"kalshi|polymarket|prediction[- ]market|implied probabilit|betting odds|"
                          r"sportsbook|moneyline", re.I)
RESOLUTION_WORDS = re.compile(r"\b(resolved|resolves|final result|final score|ended up|went on to|"
                              r"turned out|was announced on)\b", re.I)


def word_count(text):
    return len(re.findall(r"\S+", text))


def find_dates(text, default_year):
    """All exact calendar dates in text (ISO or 'Month D[, YYYY]'); year defaults to default_year."""
    out = []
    for y, m, d in ISO.findall(text):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for mon, d, y in LONG.findall(text):
        try:
            out.append(date(int(y) if y else default_year, MONTHS[mon], int(d)))
        except ValueError:
            pass
    return sorted(set(out))


def source_published_ok(published, t0):
    """Source must be published strictly before t0. Date-only values must be before t0's calendar day."""
    if not published:
        return False
    t0dt = parse_ts(t0)
    try:
        if "T" in published:
            return parse_ts(published) < t0dt
        y, m, d = (int(x) for x in published.split("-"))
        return date(y, m, d) < t0dt.date()
    except (ValueError, TypeError):
        return False


def check_brief(brief, t0, resolved_at, sources, max_words=450):
    hard, warn = [], []
    n = word_count(brief)
    if n > max_words:
        hard.append(f"brief too long: {n} words (max {max_words})")
    if n == 0:
        hard.append("brief is empty")
    hits = sorted({m.group(0).lower() for m in MARKET_WORDS.finditer(brief)})
    if hits:
        hard.append(f"market/betting terms in brief: {hits}")
    if not sources:
        hard.append("no sources listed")
    for s in sources or []:
        if not source_published_ok(s.get("published"), t0):
            hard.append(f"source not published before t0: {s.get('url') or s.get('title')} ({s.get('published')})")
    t0d, resd = parse_ts(t0).date(), parse_ts(resolved_at).date()
    for d in find_dates(brief, default_year=t0d.year):
        if d > resd:
            hard.append(f"date after resolution date: {d.isoformat()}")
        elif d > t0d:
            warn.append(f"date between t0 and resolution: {d.isoformat()} (fine only if it is the scheduled event date)")
    rw = sorted({m.group(0).lower() for m in RESOLUTION_WORDS.finditer(brief)})
    if rw:
        warn.append(f"outcome-flavoured words: {rw}")
    return {"hard_fail": hard, "warnings": warn, "ok": not hard}
