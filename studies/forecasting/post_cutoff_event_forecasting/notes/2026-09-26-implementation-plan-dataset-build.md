# S013 Dataset Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and freeze a 250-item dataset of real-world binary forecasting questions (settled Kalshi markets that resolved on or after 2026-09-01), each with a leak-checked pre-event brief, ready for model runs.

**Architecture:** Small pure-Python modules (selection, leak checks, schema) tested offline, three thin pipeline scripts that pass JSONL files between stages in the study's `runs/`, and a set of agent-driven steps (Kalshi collection, question curation, brief writing, independent leak check) that the Claude session performs with the Kalshi and web-search tools and records as JSONL. A hand audit and a SHA-256 freeze end the plan. Model runs and scoring are a separate plan (Plan B), written after the freeze.

**Tech Stack:** Python 3.10 standard library only (no pytest: tests are plain scripts, S012 style), Kalshi MCP tools, WebSearch, `Agent` subagents.

**Spec:** `studies/forecasting/post_cutoff_event_forecasting/notes/2026-09-26-dataset-design.md` (also Project doc `claude/2026-09-26-post-cutoff-forecasting-design.md`). Floor probe evidence: `notes/2026-09-26-floor-probe-round1.md`.

## Global Constraints

- Floor: an item counts only if it resolved on or after **2026-09-01** (`select_lib.FLOOR`). Confirmed after floor probe round 1.
- Total **250** items; quotas: economics_finance **65**, sports **65**, politics_world **60**, culture_science_tech **60** (`select_lib.QUOTAS`). A shortfall is reported, never hidden.
- Unit of analysis is the real-world **event**: at most **2 rungs per Kalshi ladder** and at most **2 items per `event_id`** (a CPI print is one event across several Kalshi series).
- Keep only rungs whose Kalshi price at t0 is between **0.15 and 0.85**. The t0 price comes from candlestick history, never from a settled market's listed last price.
- t0 is at least **24 hours** before resolution (earlier of market close and game/event start).
- Exclude auto-generated parlays: series tickers starting `KXMVE`. Exclude Kalshi category "Mentions".
- Question polarity balanced: exactly half (rounded down) of each category asked negated.
- Brief: target at most **400 words** for the writer, hard cap **450** in code; every source published strictly before t0's calendar day; no prediction-market or betting terms; no dates after the resolution date. The Kalshi price never appears in a brief. (Extension of the spec, decided while planning: betting lines and sportsbook terms are also excluded from briefs.)
- The brief writer never sees the outcome or the market price.
- Every script locates its folders relative to `__file__`, never the working directory; no absolute paths; no API keys are needed in this plan (no Poe calls).
- Raw data in `runs/` is append-only; reruns write new files or clearly overwrite only files this plan regenerates (stated per task).
- Run scripts with `python3 -B` (a `__pycache__` folder cannot be deleted from the connected folder); `tools/check_structure.py` must report 0 problems at the end of every task.
- No git repository exists in `LLM Testing/`, so there are no commit steps; the checkpoint after each task is the passing test run plus `check_structure.py`.
- Every write-up states caveats: replicates per cell, number of models, single rater or judge setup, halted or missing trials.

## File Structure

All paths are under `studies/forecasting/post_cutoff_event_forecasting/`.

| File | Responsibility |
|---|---|
| `scripts/select_lib.py` | Pure selection logic: floor, category mapping, parlay filter, t0, ladder sampling and rung picking, per-event cap, quota fill, polarity |
| `scripts/leak_check.py` | Pure mechanical checks on briefs (length, banned terms, source dates, dates after resolution) |
| `scripts/dataset_schema.py` | Row schema, `validate_item`, JSONL io, freeze/verify |
| `scripts/build_items.py` | Stages `prices-needed`, `shortlist`, `finalize` (raw Kalshi markets to polarity-assigned items) |
| `scripts/assemble_dataset.py` | Joins items + briefs + LLM leak-check output into `dataset_candidate.jsonl` |
| `scripts/audit_sample.py` | Builds the hand-audit sheet, applies verdicts, writes and freezes `dataset_v1.jsonl` |
| `scripts/test_*.py` (4 files) | Offline tests, one per module plus an end-to-end smoke test |
| `design/brief_writer_prompt.md`, `design/brief_checker_prompt.md` | Prompt templates for the writer and independent checker agents |
| `runs/*.jsonl`, `runs/audit_sheet.csv`, `runs/report_*.json` | Stage data and reports (created during execution) |

Data flow: `kalshi_markets_raw.jsonl` (Task 5) -> `prices_needed.jsonl` -> `kalshi_t0_prices.jsonl` (Task 6) -> `shortlist.jsonl` -> `curation.jsonl` (Task 7) -> `items_pre_brief.jsonl` -> `briefs.jsonl` (Task 8) + `leak_llm.jsonl` (Task 9) -> `dataset_candidate.jsonl` -> `audit_sheet.csv` -> `dataset_v1.jsonl` + `.sha256` (Task 10).

Shell convention for every command below (run with `device_bash`):

```bash
S="$HOME/mnt/LLM Testing/studies/forecasting/post_cutoff_event_forecasting"
cd "$S/scripts"
```

---

### Task 1: Selection library

**Files:**
- Create: `scripts/select_lib.py`
- Create: `scripts/test_select_lib.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 3-4): constants `FLOOR`, `CATEGORIES`, `QUOTAS`, `P_LO`, `P_HI`, `KALSHI_CATEGORY_MAP`; functions `parse_ts(s) -> datetime`, `is_parlay(series_ticker) -> bool`, `category_for(kalshi_category) -> str | None`, `resolved_after_floor(close_ts, floor=FLOOR) -> bool`, `choose_t0(open_ts, close_ts, event_start_ts=None, min_hours=24) -> datetime | None`, `sample_ladder(markets, max_n=10) -> list`, `pick_rungs(markets, lo, hi, max_n=2, min_gap=0.2) -> list[dict]` (needs keys `market_ticker`, `t0_price`), `cap_per_event(items, cap=2) -> list[dict]` (needs `event_id`, `t0_price`, `market_ticker`), `fill_quota(items, quota, seed) -> (list, int shortfall)`, `assign_polarity(items, seed) -> {market_ticker: bool}`, `apply_polarity(item, flipped) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_select_lib.py`:

```python
"""Offline tests for select_lib. Run: python test_select_lib.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_lib as S


def mk(t, p, ev="e1", cat="sports"):
    return {"market_ticker": t, "t0_price": p, "event_id": ev, "category": cat,
            "statement": f"S {t}", "negated_statement": f"NOT {t}", "outcome": 1}


def test_parlay_and_category():
    assert S.is_parlay("KXMVECROSSCATEGORY") and S.is_parlay("kxmvesports")
    assert not S.is_parlay("KXCPI")
    assert S.category_for("Economics") == "economics_finance"
    assert S.category_for("Elections") == "politics_world"
    assert S.category_for("Mentions") is None


def test_resolved_after_floor():
    assert S.resolved_after_floor("2026-09-01T00:00:00Z")
    assert not S.resolved_after_floor("2026-08-31T23:59:59Z")


def test_choose_t0():
    t0 = S.choose_t0("2026-08-01T00:00:00Z", "2026-09-11T12:25:00Z")
    assert t0.isoformat() == "2026-09-10T12:25:00+00:00"
    # event start earlier than close wins
    t0 = S.choose_t0("2026-08-01T00:00:00Z", "2026-09-20T00:00:00Z", event_start_ts="2026-09-12T18:00:00Z")
    assert t0.isoformat() == "2026-09-11T18:00:00+00:00"
    # market opened after t0 -> unusable
    assert S.choose_t0("2026-09-10T20:00:00Z", "2026-09-11T12:25:00Z") is None


def test_sample_ladder():
    m = [{"market_ticker": str(i)} for i in range(26)]
    s = S.sample_ladder(m, 10)
    assert len(s) == 10 and s[0]["market_ticker"] == "0" and s[-1]["market_ticker"] == "25"
    assert S.sample_ladder(m[:5], 10) == m[:5]


def test_pick_rungs_band_gap_and_ties():
    ladder = [mk("A", 0.97), mk("B", 0.80), mk("C", 0.55), mk("D", 0.52), mk("E", 0.20), mk("F", 0.03)]
    got = [m["market_ticker"] for m in S.pick_rungs(ladder)]
    assert got == ["D", "B"], got          # D closest to .5; C too close to D; B is >=0.2 from D; A,F out of band
    assert S.pick_rungs([mk("A", 0.99), mk("B", 0.01)]) == []
    assert S.pick_rungs([{"market_ticker": "X", "t0_price": None}]) == []
    a = S.pick_rungs([mk("B", 0.5), mk("A", 0.5)], max_n=1)
    assert a[0]["market_ticker"] == "A"     # deterministic tie-break


def test_cap_per_event():
    items = [mk("a", 0.5, "cpi"), mk("b", 0.4, "cpi"), mk("c", 0.3, "cpi"), mk("d", 0.9, "fed")]
    kept = {i["market_ticker"] for i in S.cap_per_event(items, 2)}
    assert kept == {"a", "b", "d"}


def test_fill_quota_seeded_and_shortfall():
    items = [mk(f"t{i}", 0.5) for i in range(10)]
    a, sa = S.fill_quota(items, 4, seed=1)
    b, _ = S.fill_quota(items, 4, seed=1)
    c, _ = S.fill_quota(items, 4, seed=2)
    assert a == b and a != c and sa == 0 and len(a) == 4
    _, short = S.fill_quota(items[:3], 5, seed=1)
    assert short == 2


def test_polarity_balanced_and_consistent():
    items = [mk(f"t{i}", 0.5, cat="sports") for i in range(9)] + [mk(f"u{i}", 0.5, cat="politics_world") for i in range(4)]
    flips = S.assign_polarity(items, seed=7)
    assert sum(flips[i["market_ticker"]] for i in items if i["category"] == "sports") == 4
    assert sum(flips[i["market_ticker"]] for i in items if i["category"] == "politics_world") == 2
    assert flips == S.assign_polarity(items, seed=7)
    it = mk("x", 0.5)
    y = S.apply_polarity(it, False)
    n = S.apply_polarity(it, True)
    assert y["asked_statement"] == "S x" and y["asked_outcome"] == 1
    assert n["asked_statement"] == "NOT x" and n["asked_outcome"] == 0 and n["polarity_flipped"] is True


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -B test_select_lib.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'select_lib'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/select_lib.py`:

```python
"""S013 selection logic: pure functions, no network. Tested by test_select_lib.py."""
import random
from datetime import datetime, timedelta

FLOOR = "2026-09-01T00:00:00Z"
CATEGORIES = ("economics_finance", "sports", "politics_world", "culture_science_tech")
QUOTAS = {"economics_finance": 65, "sports": 65, "politics_world": 60, "culture_science_tech": 60}
P_LO, P_HI = 0.15, 0.85          # keep only rungs whose t0 market price is in this band

# Kalshi category label -> study category. Anything not listed (e.g. "Mentions") is excluded.
KALSHI_CATEGORY_MAP = {
    "Economics": "economics_finance", "Financials": "economics_finance", "Finance": "economics_finance",
    "Commodities": "economics_finance", "Crypto": "economics_finance", "Companies": "economics_finance",
    "Business": "economics_finance",
    "Sports": "sports",
    "Politics": "politics_world", "Elections": "politics_world",
    "Entertainment": "culture_science_tech", "Culture": "culture_science_tech",
    "Science and Technology": "culture_science_tech", "Tech & Science": "culture_science_tech",
    "Climate and Weather": "culture_science_tech", "Climate": "culture_science_tech",
    "AI": "culture_science_tech", "Social": "culture_science_tech", "Transportation": "culture_science_tech",
}


def parse_ts(s):
    """ISO-8601 with trailing Z -> aware datetime (works on Python 3.10)."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_parlay(series_ticker):
    """Auto-generated multi-leg markets (KXMVE...) are never used."""
    return str(series_ticker).upper().startswith("KXMVE")


def category_for(kalshi_category):
    return KALSHI_CATEGORY_MAP.get(kalshi_category)


def resolved_after_floor(close_ts, floor=FLOOR):
    return parse_ts(close_ts) >= parse_ts(floor)


def choose_t0(open_ts, close_ts, event_start_ts=None, min_hours=24):
    """t0 = (earlier of close and event start) - min_hours. None if the market was not open a full
    hour before t0 (then there is no usable pre-event price)."""
    end = parse_ts(close_ts)
    if event_start_ts:
        end = min(end, parse_ts(event_start_ts))
    t0 = end - timedelta(hours=min_hours)
    if parse_ts(open_ts) > t0 - timedelta(hours=1):
        return None
    return t0


def sample_ladder(markets, max_n=10):
    """Evenly spaced subset of a ladder (input order = threshold order) to limit price lookups."""
    n = len(markets)
    if n <= max_n:
        return list(markets)
    idx = sorted({round(i * (n - 1) / (max_n - 1)) for i in range(max_n)})
    return [markets[i] for i in idx]


def pick_rungs(markets, lo=P_LO, hi=P_HI, max_n=2, min_gap=0.2):
    """From one ladder pick up to max_n rungs with t0_price in [lo, hi], closest to 0.5 first, each at
    least min_gap apart in price from those already chosen. Deterministic (ties broken by ticker)."""
    live = [m for m in markets if m.get("t0_price") is not None and lo <= m["t0_price"] <= hi]
    live.sort(key=lambda m: (round(abs(m["t0_price"] - 0.5), 6), m["market_ticker"]))
    chosen = []
    for m in live:
        if all(abs(m["t0_price"] - c["t0_price"]) >= min_gap for c in chosen):
            chosen.append(m)
        if len(chosen) == max_n:
            break
    return chosen


def cap_per_event(items, cap=2):
    """At most `cap` items per real-world event_id (a CPI print is one event even across several
    Kalshi series). Keeps those closest to 0.5."""
    kept, seen = [], {}
    for it in sorted(items, key=lambda i: (round(abs(i["t0_price"] - 0.5), 6), i["market_ticker"])):
        if seen.get(it["event_id"], 0) < cap:
            kept.append(it)
            seen[it["event_id"]] = seen.get(it["event_id"], 0) + 1
    return kept


def fill_quota(items, quota, seed):
    """Seeded random subset of size <= quota. Returns (selected, shortfall)."""
    pool = sorted(items, key=lambda i: i["market_ticker"])
    random.Random(seed).shuffle(pool)
    sel = pool[:quota]
    return sel, max(0, quota - len(sel))


def assign_polarity(items, seed):
    """Flip exactly half (rounded down) of the items in each category. Returns {market_ticker: bool}."""
    flips = {}
    for cat in {i["category"] for i in items}:
        grp = sorted((i for i in items if i["category"] == cat), key=lambda i: i["market_ticker"])
        idx = list(range(len(grp)))
        random.Random(f"{seed}|{cat}").shuffle(idx)
        flipped = set(idx[: len(grp) // 2])
        for k, it in enumerate(grp):
            flips[it["market_ticker"]] = k in flipped
    return flips


def apply_polarity(item, flipped):
    """asked_statement/asked_outcome for the model. Outcome 1 = the market's YES statement was true."""
    item = dict(item)
    item["polarity_flipped"] = bool(flipped)
    item["asked_statement"] = item["negated_statement"] if flipped else item["statement"]
    item["asked_outcome"] = (1 - item["outcome"]) if flipped else item["outcome"]
    return item
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B test_select_lib.py`
Expected: 8 lines, all `PASS` (test_cap_per_event, test_choose_t0, test_fill_quota_seeded_and_shortfall, test_parlay_and_category, test_pick_rungs_band_gap_and_ties, test_polarity_balanced_and_consistent, test_resolved_after_floor, test_sample_ladder), exit code 0.

- [ ] **Step 5: Structure check**

Run: `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py`
Expected: `0 problems, 0 warnings`.

---

### Task 2: Mechanical leak checks

**Files:**
- Create: `scripts/leak_check.py`
- Create: `scripts/test_leak_check.py`

**Interfaces:**
- Consumes: `select_lib.parse_ts`.
- Produces: `word_count(text) -> int`, `find_dates(text, default_year) -> list[date]`, `source_published_ok(published, t0) -> bool`, `check_brief(brief, t0, resolved_at, sources, max_words=450) -> {"hard_fail": list[str], "warnings": list[str], "ok": bool}`; constants `MARKET_WORDS`, `RESOLUTION_WORDS` (compiled regexes).

- [ ] **Step 1: Write the failing test**

Create `scripts/test_leak_check.py`:

```python
"""Offline tests for leak_check. Run: python test_leak_check.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leak_check as L

T0, RES = "2026-09-10T12:25:00Z", "2026-09-11T12:25:00Z"
GOOD_SRC = [{"url": "https://x.example/a", "title": "a", "published": "2026-09-08"}]


def test_find_dates():
    txt = "On 2026-09-05 and September 7, 2026 and Sept. 9 the report; September 2026 alone is ignored; Feb 30 invalid."
    assert L.find_dates(txt, 2026) == [date(2026, 9, 5), date(2026, 9, 7), date(2026, 9, 9)]


def test_source_published_rules():
    assert L.source_published_ok("2026-09-09", T0)
    assert not L.source_published_ok("2026-09-10", T0)             # date-only on t0's day: too risky
    assert L.source_published_ok("2026-09-10T08:00:00Z", T0)
    assert not L.source_published_ok("2026-09-10T13:00:00Z", T0)
    assert not L.source_published_ok(None, T0) and not L.source_published_ok("soon", T0)


def test_clean_brief_passes():
    r = L.check_brief("Consensus expects +0.3% month over month; July was +0.1%.", T0, RES, GOOD_SRC)
    assert r["ok"] and r["hard_fail"] == [] and r["warnings"] == []


def test_hard_failures():
    r = L.check_brief("Kalshi traders price this at 40% and the sportsbook agrees. " + "word " * 460, T0, RES, GOOD_SRC)
    joined = " ".join(r["hard_fail"])
    assert not r["ok"] and "too long" in joined and "market/betting" in joined
    r = L.check_brief("Fine text.", T0, RES, [])
    assert "no sources listed" in r["hard_fail"]
    r = L.check_brief("Fine text.", T0, RES, [{"url": "u", "published": "2026-09-12"}])
    assert any("not published before t0" in h for h in r["hard_fail"])
    r = L.check_brief("The figure published on September 20, 2026 showed 3.4%.", T0, RES, GOOD_SRC)
    assert any("after resolution date" in h for h in r["hard_fail"])
    assert not L.check_brief("", T0, RES, GOOD_SRC)["ok"]


def test_warnings_not_failures():
    r = L.check_brief("The release is scheduled for September 11, 2026; it turned out later to matter.", T0, RES, GOOD_SRC)
    assert r["ok"] and len(r["warnings"]) == 2


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -B test_leak_check.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'leak_check'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/leak_check.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B test_leak_check.py`
Expected: 5 lines, all `PASS`, exit code 0.

- [ ] **Step 5: Structure check**

Run: `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py`
Expected: `0 problems, 0 warnings`.

---

### Task 3: Dataset schema and freezing

**Files:**
- Create: `scripts/dataset_schema.py`
- Create: `scripts/test_dataset_schema.py`

**Interfaces:**
- Consumes: `select_lib.CATEGORIES`, `select_lib.FLOOR`, `select_lib.parse_ts`, `leak_check.check_brief`.
- Produces: `REQUIRED` (list of field names), `LEAK_KEYS`, `validate_item(item) -> list[str]` (empty = valid), `write_jsonl(path, items)`, `read_jsonl(path) -> list[dict]`, `freeze(path) -> str` (writes `<path>.sha256`, returns hex digest), `verify(path) -> bool`.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_dataset_schema.py`:

```python
"""Offline tests for dataset_schema. Run: python test_dataset_schema.py"""
import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dataset_schema as D

GOOD = {
    "item_id": "S013-0001", "event_id": "cpi-2026-08", "category": "economics_finance", "source": "kalshi",
    "market_ticker": "KXCPI-26AUG-T0.3", "statement": "US CPI rose more than 0.3% in August 2026.",
    "negated_statement": "US CPI rose 0.3% or less in August 2026.", "polarity_flipped": False,
    "asked_statement": "US CPI rose more than 0.3% in August 2026.",
    "resolution_criteria": "BLS all-items CPI-U, seasonally adjusted, one-month change, first release.",
    "t0": "2026-09-10T12:25:00Z", "resolved_at": "2026-09-11T12:25:00Z", "outcome": 1, "asked_outcome": 1,
    "market_price_t0": 0.45, "brief": "Consensus expects +0.3%; July was +0.1%.",
    "brief_sources": [{"url": "https://x.example/a", "title": "a", "published": "2026-09-08"}],
    "leak_check": {"mechanical_ok": True, "llm_flag": False, "llm_predicted_probability": 0.5}, "audited": False,
}


def bad(**kw):
    it = copy.deepcopy(GOOD)
    it.update(kw)
    return D.validate_item(it)


def test_good_item_is_valid():
    assert D.validate_item(GOOD) == []


def test_catches_problems():
    assert any("missing field" in e for e in D.validate_item({"item_id": "x"}))
    assert any("bad category" in e for e in bad(category="weather"))
    assert any("inconsistent" in e for e in bad(polarity_flipped=True))
    assert bad(polarity_flipped=True, asked_outcome=0, asked_statement=GOOD["negated_statement"]) == []
    assert any("market_price_t0" in e for e in bad(market_price_t0=1.0))
    assert any("before the floor" in e for e in bad(resolved_at="2026-08-30T00:00:00Z"))
    assert any("t0 must be before" in e for e in bad(t0="2026-09-12T00:00:00Z"))
    assert any("Kalshi".lower() in e.lower() for e in bad(brief="Kalshi says 45%."))
    assert any("leak_check missing" in e for e in bad(leak_check={"mechanical_ok": True}))


def test_jsonl_roundtrip_and_freeze():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ds.jsonl"
        D.write_jsonl(p, [GOOD, GOOD])
        assert D.read_jsonl(p) == [GOOD, GOOD]
        h = D.freeze(p)
        assert len(h) == 64 and D.verify(p)
        p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        assert not D.verify(p)


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -B test_dataset_schema.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'dataset_schema'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dataset_schema.py`:

```python
"""S013 dataset row schema, validation, JSONL io and freezing. Tested by test_dataset_schema.py."""
import hashlib
import json
from pathlib import Path

from leak_check import check_brief
from select_lib import CATEGORIES, FLOOR, parse_ts

REQUIRED = ["item_id", "event_id", "category", "source", "market_ticker", "statement", "negated_statement",
            "polarity_flipped", "asked_statement", "resolution_criteria", "t0", "resolved_at", "outcome",
            "asked_outcome", "market_price_t0", "brief", "brief_sources", "leak_check", "audited"]
LEAK_KEYS = ["mechanical_ok", "llm_flag", "llm_predicted_probability"]


def validate_item(it):
    """List of problems (empty = valid)."""
    errs = [f"missing field: {k}" for k in REQUIRED if k not in it]
    if errs:
        return errs
    if it["category"] not in CATEGORIES:
        errs.append(f"bad category: {it['category']}")
    if it["outcome"] not in (0, 1) or it["asked_outcome"] not in (0, 1):
        errs.append("outcome/asked_outcome must be 0 or 1")
    else:
        want = 1 - it["outcome"] if it["polarity_flipped"] else it["outcome"]
        if it["asked_outcome"] != want:
            errs.append("asked_outcome inconsistent with polarity_flipped")
    want_stmt = it["negated_statement"] if it["polarity_flipped"] else it["statement"]
    if it["asked_statement"] != want_stmt:
        errs.append("asked_statement inconsistent with polarity_flipped")
    p = it["market_price_t0"]
    if p is not None and not (0 < p < 1):
        errs.append("market_price_t0 must be in (0,1) or null")
    try:
        if parse_ts(it["resolved_at"]) < parse_ts(FLOOR):
            errs.append("resolved before the floor")
        if not parse_ts(it["t0"]) < parse_ts(it["resolved_at"]):
            errs.append("t0 must be before resolved_at")
    except (ValueError, TypeError):
        errs.append("t0/resolved_at not ISO timestamps")
        return errs
    lk = it["leak_check"]
    errs += [f"leak_check missing {k}" for k in LEAK_KEYS if not isinstance(lk, dict) or k not in lk]
    rep = check_brief(it["brief"], it["t0"], it["resolved_at"], it["brief_sources"])
    errs += rep["hard_fail"]
    return errs


def write_jsonl(path, items):
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, sort_keys=True, ensure_ascii=False) + "\n")


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def freeze(path):
    """Write <path>.sha256 and return the hex digest. Do this before any model sees the dataset."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def verify(path):
    path = Path(path)
    want = Path(str(path) + ".sha256").read_text(encoding="utf-8").split()[0]
    return hashlib.sha256(path.read_bytes()).hexdigest() == want
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B test_dataset_schema.py && python3 -B test_select_lib.py && python3 -B test_leak_check.py`
Expected: every line `PASS`, exit code 0.

- [ ] **Step 5: Structure check**

Run: `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py`
Expected: `0 problems, 0 warnings`.

---

### Task 4: Pipeline scripts and end-to-end smoke test

**Files:**
- Create: `scripts/build_items.py`
- Create: `scripts/assemble_dataset.py`
- Create: `scripts/audit_sample.py`
- Create: `scripts/test_pipeline_smoke.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces (file formats the agent steps in Tasks 5-9 must write exactly):
  - `runs/kalshi_markets_raw.jsonl`, one market per line: `event_ticker`, `series_ticker`, `market_ticker`, `yes_subtitle`, `event_title`, `kalshi_category` (Kalshi's label, e.g. "Economics"), `open_ts`, `close_ts` (ISO-8601 UTC with `Z`), `event_start_ts` (ISO or `null`), `result` (`"yes"` or `"no"`), `ladder_order` (int, threshold order within the event), `rules_primary` (string).
  - `runs/kalshi_t0_prices.jsonl`: `market_ticker`, `t0_price` (float in dollars 0-1, or `null`).
  - `runs/curation.jsonl`: `market_ticker`, `event_id` (string slug), `statement`, `negated_statement`, `resolution_criteria`, `drop` (bool).
  - `runs/briefs.jsonl`: `item_id`, `brief`, `brief_sources` (list of `{url, title, published: "YYYY-MM-DD"}`).
  - `runs/leak_llm.jsonl`: `item_id`, `predicted_probability` (float, probability the ASKED statement is true given only the brief), `flag` (bool), `reason`.
  - CLIs: `build_items.py {prices-needed|shortlist|finalize} [--runs-dir DIR]`, `assemble_dataset.py [--runs-dir DIR]`, `audit_sample.py {make|apply} [--runs-dir DIR]`; each prints a JSON report.
  - Functions used by tests: `build_items.stage_prices_needed(runs)`, `stage_shortlist(runs)`, `stage_finalize(runs)`, `assemble_dataset.assemble(runs)`, `audit_sample.make(runs)`, `audit_sample.apply(runs)`, `audit_sample.FIELDS`.

- [ ] **Step 1: Write the failing smoke test**

Create `scripts/test_pipeline_smoke.py`:

```python
"""End-to-end smoke test of build_items -> assemble_dataset -> audit_sample on synthetic data.
Run: python test_pipeline_smoke.py"""
import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble_dataset as A
import audit_sample as AU
import build_items as B
import dataset_schema as D
import select_lib as S

KCAT = {"economics_finance": "Economics", "sports": "Sports", "politics_world": "Politics",
        "culture_science_tech": "Entertainment"}
PRICES = [0.95, 0.80, 0.55, 0.40, 0.20, 0.05]


def raw_markets():
    rows = []
    for cat, kc in KCAT.items():
        for e in range(4):
            ev = f"{cat[:3].upper()}EV{e}"
            for k, _p in enumerate(PRICES):
                rows.append({"event_ticker": ev, "series_ticker": "KXSER", "market_ticker": f"{ev}-T{k}",
                             "yes_subtitle": f"Above {k}", "event_title": ev, "kalshi_category": kc,
                             "open_ts": "2026-08-01T00:00:00Z", "close_ts": f"2026-09-{10 + e:02d}T12:00:00Z",
                             "event_start_ts": None, "result": "yes" if k < 3 else "no", "ladder_order": k,
                             "rules_primary": "rules"})
    base = dict(event_ticker="X", yes_subtitle="", event_title="X", open_ts="2026-08-01T00:00:00Z",
                close_ts="2026-09-12T12:00:00Z", event_start_ts=None, result="yes", ladder_order=0, rules_primary="")
    rows += [{**base, "series_ticker": "KXMVECROSSCATEGORY", "market_ticker": "PARLAY", "kalshi_category": "Sports"},
             {**base, "series_ticker": "KXM", "market_ticker": "MENTION", "kalshi_category": "Mentions"},
             {**base, "series_ticker": "KXM", "market_ticker": "OLD", "kalshi_category": "Sports", "close_ts": "2026-08-20T00:00:00Z"},
             {**base, "series_ticker": "KXM", "market_ticker": "LATEOPEN", "kalshi_category": "Sports", "open_ts": "2026-09-11T20:00:00Z"}]
    return rows


def test_pipeline():
    S.QUOTAS = {c: 3 for c in S.CATEGORIES}          # small quotas for the smoke test
    with tempfile.TemporaryDirectory() as d:
        runs = Path(d)
        D.write_jsonl(runs / "kalshi_markets_raw.jsonl", raw_markets())

        r = B.stage_prices_needed(runs)
        assert r["dropped"] == {"parlay": 1, "category_excluded": 1, "before_floor": 1, "no_pre_event_window": 1}, r
        need = D.read_jsonl(runs / "prices_needed.jsonl")
        assert len(need) == 16 * 6 and all("t0" in n for n in need)

        prices = [{"market_ticker": n["market_ticker"], "t0_price": PRICES[int(n["market_ticker"][-1])]} for n in need]
        D.write_jsonl(runs / "kalshi_t0_prices.jsonl", prices)
        r = B.stage_shortlist(runs)
        short = D.read_jsonl(runs / "shortlist.jsonl")
        assert all(0.15 <= s["t0_price"] <= 0.85 for s in short) and len(short) <= 4 * 5   # ceil(3*1.6)=5 per category
        assert {s["category"] for s in short} == set(S.CATEGORIES)

        cur, seen = [], {}
        for i, s in enumerate(short):
            ev = "shared-event" if s["event_ticker"] in ("ECOEV0", "ECOEV1") else s["event_ticker"]
            cur.append({"market_ticker": s["market_ticker"], "event_id": ev, "drop": i == 0,
                        "statement": f"Statement {s['market_ticker']}", "negated_statement": f"Not {s['market_ticker']}",
                        "resolution_criteria": "criteria"})
        D.write_jsonl(runs / "curation.jsonl", cur)
        r = B.stage_finalize(runs)
        items = D.read_jsonl(runs / "items_pre_brief.jsonl")
        assert r["final"] == len(items) and all(v >= 0 for v in r["shortfall_vs_quota"].values())
        assert len({i["item_id"] for i in items}) == len(items)
        for c in S.CATEGORIES:
            assert sum(1 for i in items if i["category"] == c) <= 3
        assert sum(1 for i in items if i["event_id"] == "shared-event") <= 2

        briefs = [{"item_id": i["item_id"], "brief": "Prior print +0.1%; consensus +0.3%.",
                   "brief_sources": [{"url": f"https://x.example/{i['item_id']}", "title": "t", "published": "2026-08-25"}]}
                  for i in items]
        briefs[0]["brief_sources"][0]["published"] = "2026-09-30"          # leaks -> must be rejected
        missing = briefs.pop()                                              # no brief -> rejected
        llm = [{"item_id": b["item_id"], "predicted_probability": 0.5, "flag": False, "reason": "ok"} for b in briefs]
        llm[1]["flag"] = True
        it2 = next(i for i in items if i["item_id"] == briefs[2]["item_id"])
        llm[2]["predicted_probability"] = 0.97 if it2["asked_outcome"] == 1 else 0.03    # suspicious
        llm.append({"item_id": missing["item_id"], "predicted_probability": 0.5, "flag": False, "reason": ""})
        D.write_jsonl(runs / "briefs.jsonl", briefs)
        D.write_jsonl(runs / "leak_llm.jsonl", llm)
        r = A.assemble(runs)
        rej = D.read_jsonl(runs / "dataset_rejects.jsonl")
        assert r["rejected"] == 2 and r["valid"] == len(items) - 2, r
        assert any("not published before t0" in " ".join(x["errors"]) for x in rej)
        assert any("missing brief" in " ".join(x["errors"]) for x in rej)
        assert r["flagged_for_audit"] == 2

        m = AU.make(runs)
        assert m["flagged"] == 2 and m["sheet_rows"] >= 2
        try:
            AU.apply(runs)
            raise AssertionError("apply must refuse blank verdicts")
        except SystemExit as e:
            assert "cannot freeze" in str(e)
        rows = list(csv.DictReader((runs / "audit_sheet.csv").open(encoding="utf-8")))
        for row in rows:
            row["human_verdict"] = "ok"
        rows[0]["human_verdict"] = "drop"
        with (runs / "audit_sheet.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=AU.FIELDS); w.writeheader(); w.writerows(rows)
        res = AU.apply(runs)
        final = D.read_jsonl(runs / "dataset_v1.jsonl")
        assert res["items"] == len(final) == r["valid"] - 1 and D.verify(runs / "dataset_v1.jsonl")
        assert sum(1 for x in final if x["audited"]) == len(rows) - 1
        assert all(D.validate_item(x) == [] for x in final)


if __name__ == "__main__":
    test_pipeline()
    print("PASS test_pipeline")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -B test_pipeline_smoke.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'assemble_dataset'`.

- [ ] **Step 3: Write `build_items.py`**

Create `scripts/build_items.py`:

```python
#!/usr/bin/env python3
"""S013 item builder: raw Kalshi markets -> selected, polarity-assigned items (no briefs yet).

    python build_items.py prices-needed   # which markets need a t0 price lookup   -> runs/prices_needed.jsonl
    python build_items.py shortlist       # rungs in the 15-85% band, 1.6x quota    -> runs/shortlist.jsonl
    python build_items.py finalize        # apply curation, cap, quota, polarity    -> runs/items_pre_brief.jsonl

Inputs (written by the Claude session through the Kalshi tools, see the plan): runs/kalshi_markets_raw.jsonl,
runs/kalshi_t0_prices.jsonl, runs/curation.jsonl. Add --runs-dir to point elsewhere (tests).
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import dataset_schema as D  # noqa: E402
import select_lib as S  # noqa: E402

DEFAULT_RUNS = _HERE.parent / "runs"
SEED = 20260926
OVERFLOW = 1.6           # shortlist this multiple of each quota so curation can drop some
LADDER_MAX = 10          # price lookups per ladder


def eligible(rows):
    """Hard filters. Returns (rows with 'category' and 't0' added, {reason: count})."""
    drops, kept = defaultdict(int), []
    for r in rows:
        if S.is_parlay(r["series_ticker"]):
            drops["parlay"] += 1; continue
        cat = S.category_for(r["kalshi_category"])
        if cat is None:
            drops["category_excluded"] += 1; continue
        if r.get("result") not in ("yes", "no"):
            drops["not_settled_yes_no"] += 1; continue
        if not S.resolved_after_floor(r["close_ts"]):
            drops["before_floor"] += 1; continue
        t0 = S.choose_t0(r["open_ts"], r["close_ts"], r.get("event_start_ts"))
        if t0 is None:
            drops["no_pre_event_window"] += 1; continue
        kept.append({**r, "category": cat, "t0": t0.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return kept, dict(drops)


def _by_event(rows):
    d = defaultdict(list)
    for r in rows:
        d[r["event_ticker"]].append(r)
    for ms in d.values():
        ms.sort(key=lambda m: m.get("ladder_order", 0))
    return d


def stage_prices_needed(runs):
    kept, drops = eligible(D.read_jsonl(runs / "kalshi_markets_raw.jsonl"))
    by_ev = _by_event(kept)
    need = []
    for _ev, ms in sorted(by_ev.items()):
        need += [{"market_ticker": m["market_ticker"], "t0": m["t0"]} for m in S.sample_ladder(ms, LADDER_MAX)]
    D.write_jsonl(runs / "prices_needed.jsonl", need)
    return {"eligible_markets": len(kept), "events": len(by_ev), "prices_needed": len(need), "dropped": drops}


def stage_shortlist(runs):
    kept, drops = eligible(D.read_jsonl(runs / "kalshi_markets_raw.jsonl"))
    prices = {p["market_ticker"]: p["t0_price"] for p in D.read_jsonl(runs / "kalshi_t0_prices.jsonl")}
    priced = [{**r, "t0_price": prices[r["market_ticker"]]} for r in kept if prices.get(r["market_ticker"]) is not None]
    picked = []
    for _ev, ms in sorted(_by_event(priced).items()):
        picked += S.pick_rungs(ms)
    out, per_cat = [], {}
    for cat in S.CATEGORIES:
        pool = [m for m in picked if m["category"] == cat]
        sel, _ = S.fill_quota(pool, math.ceil(S.QUOTAS[cat] * OVERFLOW), SEED)
        per_cat[cat] = {"in_band_rungs": len(pool), "shortlisted": len(sel)}
        out += sel
    rows = [{"market_ticker": m["market_ticker"], "event_ticker": m["event_ticker"], "series_ticker": m["series_ticker"],
             "category": m["category"], "t0": m["t0"], "resolved_at": m["close_ts"], "t0_price": m["t0_price"],
             "outcome": 1 if m["result"] == "yes" else 0, "yes_subtitle": m.get("yes_subtitle", ""),
             "event_title": m.get("event_title", ""), "rules_primary": m.get("rules_primary", "")} for m in out]
    D.write_jsonl(runs / "shortlist.jsonl", rows)
    return {"unpriced_dropped": len(kept) - len(priced), "per_category": per_cat, "dropped": drops}


def stage_finalize(runs):
    short = {r["market_ticker"]: r for r in D.read_jsonl(runs / "shortlist.jsonl")}
    cur = {c["market_ticker"]: c for c in D.read_jsonl(runs / "curation.jsonl")}
    items, dropped = [], defaultdict(int)
    for t, r in sorted(short.items()):
        c = cur.get(t)
        if c is None:
            dropped["not_curated"] += 1; continue
        if c.get("drop"):
            dropped["curator_dropped"] += 1; continue
        items.append({**r, "event_id": c["event_id"], "statement": c["statement"],
                      "negated_statement": c["negated_statement"], "resolution_criteria": c["resolution_criteria"]})
    n_before_cap = len(items)
    items = S.cap_per_event(items, 2)
    final, shortfall = [], {}
    for cat in S.CATEGORIES:
        sel, short_n = S.fill_quota([i for i in items if i["category"] == cat], S.QUOTAS[cat], SEED)
        final += sel
        shortfall[cat] = short_n
    flips = S.assign_polarity(final, SEED)
    final.sort(key=lambda i: (S.CATEGORIES.index(i["category"]), i["market_ticker"]))
    out = []
    for n, it in enumerate(final, 1):
        row = {"item_id": f"S013-{n:04d}", "event_id": it["event_id"], "category": it["category"], "source": "kalshi",
               "market_ticker": it["market_ticker"], "statement": it["statement"],
               "negated_statement": it["negated_statement"], "resolution_criteria": it["resolution_criteria"],
               "t0": it["t0"], "resolved_at": it["resolved_at"], "outcome": it["outcome"],
               "market_price_t0": it["t0_price"]}
        out.append(S.apply_polarity(row, flips[it["market_ticker"]]))
    D.write_jsonl(runs / "items_pre_brief.jsonl", out)
    return {"curated": n_before_cap, "after_event_cap": len(items), "final": len(out),
            "shortfall_vs_quota": shortfall, "dropped": dict(dropped),
            "yes_rate_asked": round(sum(o["asked_outcome"] for o in out) / max(1, len(out)), 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["prices-needed", "shortlist", "finalize"])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    a = ap.parse_args(argv)
    runs = Path(a.runs_dir)
    fn = {"prices-needed": stage_prices_needed, "shortlist": stage_shortlist, "finalize": stage_finalize}[a.stage]
    report = fn(runs)
    (runs / f"report_{a.stage.replace('-', '_')}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `assemble_dataset.py`**

Create `scripts/assemble_dataset.py`:

```python
#!/usr/bin/env python3
"""S013: join items + briefs + LLM leak-checker output, run mechanical checks, validate.

    python assemble_dataset.py           # -> runs/dataset_candidate.jsonl, runs/dataset_rejects.jsonl

Inputs: runs/items_pre_brief.jsonl, runs/briefs.jsonl ({item_id, brief, brief_sources}),
runs/leak_llm.jsonl ({item_id, predicted_probability, flag, reason}; the probability is that the
ASKED statement is true, given only the brief). An item whose checker was confidently right
(p >= 0.95 with asked_outcome 1, or p <= 0.05 with asked_outcome 0) is flagged as suspicious.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import dataset_schema as D  # noqa: E402
import select_lib as S  # noqa: E402
from leak_check import check_brief  # noqa: E402

DEFAULT_RUNS = _HERE.parent / "runs"


def assemble(runs):
    items = D.read_jsonl(runs / "items_pre_brief.jsonl")
    briefs = {b["item_id"]: b for b in D.read_jsonl(runs / "briefs.jsonl")}
    llm = {l["item_id"]: l for l in D.read_jsonl(runs / "leak_llm.jsonl")}
    good, rejects = [], []
    for it in items:
        b, l = briefs.get(it["item_id"]), llm.get(it["item_id"])
        if b is None or l is None:
            rejects.append({"item_id": it["item_id"], "errors": ["missing brief" if b is None else "missing llm leak check"]})
            continue
        mech = check_brief(b["brief"], it["t0"], it["resolved_at"], b["brief_sources"])
        p = l["predicted_probability"]
        suspicious = (p >= 0.95 and it["asked_outcome"] == 1) or (p <= 0.05 and it["asked_outcome"] == 0)
        row = {**it, "brief": b["brief"], "brief_sources": b["brief_sources"],
               "leak_check": {"mechanical_ok": mech["ok"], "mechanical_warnings": mech["warnings"],
                              "llm_flag": bool(l["flag"]) or suspicious, "llm_reason": l.get("reason", ""),
                              "llm_predicted_probability": p, "llm_suspicious_confident_correct": suspicious},
               "audited": False}
        errs = D.validate_item(row)
        if errs:
            rejects.append({"item_id": it["item_id"], "errors": errs})
        else:
            good.append(row)
    D.write_jsonl(runs / "dataset_candidate.jsonl", good)
    D.write_jsonl(runs / "dataset_rejects.jsonl", rejects)
    counts = Counter(g["category"] for g in good)
    return {"valid": len(good), "rejected": len(rejects),
            "per_category": {c: {"have": counts.get(c, 0), "quota": S.QUOTAS[c]} for c in S.CATEGORIES},
            "flagged_for_audit": sum(1 for g in good if g["leak_check"]["llm_flag"] or g["leak_check"]["mechanical_warnings"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    rep = assemble(Path(ap.parse_args().runs_dir))
    print(json.dumps(rep, indent=2))
```

- [ ] **Step 5: Write `audit_sample.py`**

Create `scripts/audit_sample.py`:

```python
#!/usr/bin/env python3
"""S013 hand audit: `make` writes the sheet, you fill human_verdict, `apply` writes the frozen dataset.

    python audit_sample.py make     # runs/audit_sheet.csv: every flagged item + a random 10% of the rest
    python audit_sample.py apply    # reads the sheet -> runs/dataset_v1.jsonl (+ .sha256)

human_verdict values: ok | drop | rewrite. `apply` refuses to freeze while any sheet row is blank or
'rewrite' (fix the brief in runs/briefs.jsonl, re-run assemble_dataset.py and `make`).
"""
import argparse
import csv
import math
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import dataset_schema as D  # noqa: E402
import select_lib as S  # noqa: E402

DEFAULT_RUNS = _HERE.parent / "runs"
SEED = 20260926
FIELDS = ["item_id", "category", "why", "asked_statement", "resolution_criteria", "t0", "brief", "sources",
          "llm_reason", "human_verdict", "human_note"]


def make(runs, frac=0.10):
    ds = D.read_jsonl(runs / "dataset_candidate.jsonl")
    flagged = [i for i in ds if i["leak_check"]["llm_flag"] or i["leak_check"]["mechanical_warnings"]]
    fids = {i["item_id"] for i in flagged}
    rest = sorted((i for i in ds if i["item_id"] not in fids), key=lambda i: i["item_id"])
    sample = random.Random(SEED).sample(rest, min(len(rest), math.ceil(frac * len(rest))))
    rows = []
    for i in sorted(flagged + sample, key=lambda i: i["item_id"]):
        lk = i["leak_check"]
        why = "flagged" if i["item_id"] in fids else "random_sample"
        rows.append({"item_id": i["item_id"], "category": i["category"], "why": why,
                     "asked_statement": i["asked_statement"], "resolution_criteria": i["resolution_criteria"],
                     "t0": i["t0"], "brief": i["brief"], "sources": " ; ".join(s["url"] for s in i["brief_sources"]),
                     "llm_reason": lk["llm_reason"] + " | " + " | ".join(lk["mechanical_warnings"]),
                     "human_verdict": "", "human_note": ""})
    with (runs / "audit_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return {"sheet_rows": len(rows), "flagged": len(flagged), "random_sample": len(sample)}


def apply(runs):
    ds = D.read_jsonl(runs / "dataset_candidate.jsonl")
    with (runs / "audit_sheet.csv").open(newline="", encoding="utf-8") as f:
        sheet = {r["item_id"]: r["human_verdict"].strip().lower() for r in csv.DictReader(f)}
    bad = {k: v for k, v in sheet.items() if v not in ("ok", "drop")}
    if bad:
        raise SystemExit(f"cannot freeze: {len(bad)} sheet rows blank or 'rewrite': {sorted(bad)[:10]}")
    out = []
    for i in ds:
        if sheet.get(i["item_id"]) == "drop":
            continue
        if sheet.get(i["item_id"]) == "ok":
            i = {**i, "audited": True}
        out.append(i)
    path = runs / "dataset_v1.jsonl"
    D.write_jsonl(path, out)
    digest = D.freeze(path)
    from collections import Counter
    c = Counter(i["category"] for i in out)
    return {"items": len(out), "dropped_in_audit": sum(v == "drop" for v in sheet.values()), "sha256": digest,
            "per_category": {k: {"have": c.get(k, 0), "quota": S.QUOTAS[k]} for k in S.CATEGORIES}}


if __name__ == "__main__":
    import json
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["make", "apply"])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    a = ap.parse_args()
    fn = make if a.action == "make" else apply
    print(json.dumps(fn(Path(a.runs_dir)), indent=2))
```

- [ ] **Step 6: Run the whole suite**

Run: `for f in test_select_lib test_leak_check test_dataset_schema test_pipeline_smoke; do python3 -B $f.py || echo "FAILED $f"; done`
Expected: every line `PASS` (the smoke test prints `PASS test_pipeline`), no `FAILED`.

- [ ] **Step 7: Structure check**

Run: `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py`
Expected: `0 problems, 0 warnings`. (If the checker objects to the extra scripts, fix the cause rather than moving files: everything lives flat in `scripts/`.)

---

### Task 5: Collect raw Kalshi markets (agent-driven)

Done by the Claude session with the Kalshi MCP tools; a script cannot call them. Load the tools first with ToolSearch (`select:mcp__kalshi_mcp__search_past_events,mcp__kalshi_mcp__get_series_list,mcp__kalshi_mcp__search_events,mcp__kalshi_mcp__get_market,mcp__kalshi_mcp__get_event_markets`).

**Files:**
- Create: `runs/kalshi_markets_raw.jsonl` (appended in batches by `device_bash`)
- Create: `runs/kalshi_collection_log.md` (what was pulled, dates, counts, anything skipped and why)

**Interfaces:**
- Consumes: the `kalshi_markets_raw.jsonl` format defined in Task 4.
- Produces: the raw file that `build_items.py prices-needed` reads.

- [ ] **Step 1: Preflight**

Run `mcp__remote-devices__device_bash` with `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py` (expect 0 problems) and confirm the four test files still pass. Confirm the Kalshi tools respond by calling `mcp__kalshi_mcp__get_exchange_status`.

- [ ] **Step 2: List series per category**

For each of Economics, Financials, Politics, Elections, Sports, Entertainment, Science and Technology, Climate and Weather, Commodities, Crypto, Companies call `mcp__kalshi_mcp__get_series_list` with `category` and `limit=100`. Skip series whose ticker starts `KXMVE`. Note that a category may exceed one page; page by narrowing with `search_past_events(series_ticker=...)`.

- [ ] **Step 3: Pull settled events since the floor, per series**

Call `mcp__kalshi_mcp__search_past_events` with `status="settled"`, `from_date="2026-09-01"`, `to_date="2026-09-26"` (use the current date as `to_date` when executing), `series_ticker=<ticker>`, `limit=100`. Never call it with only `category` (the date-range plus category search returns almost nothing but `KXMVECROSSCATEGORY` parlays). Prefer series with clear numeric or binary resolution: CPI, jobs, GDP, Fed and central-bank decisions, weather, game winners, spreads and totals, awards, chart positions, court rulings, elections. Skip series that are subjective or multi-leg.

- [ ] **Step 4: Convert each market to one raw row and append**

For every market in every event returned, build one JSON object with exactly the fields in the Task 4 raw-file format. `ladder_order` is the market's position in the event's threshold ordering (0-based, ascending threshold). `event_start_ts` is the game or event start time when identifiable from the market rules (`mcp__kalshi_mcp__get_market` returns them), otherwise `null`. Keep `rules_primary` to the first 600 characters. Append with:

```bash
cat >> "$S/runs/kalshi_markets_raw.jsonl" <<'JSONL'
{"event_ticker": "...", ...}
JSONL
```

Work per series (roughly 20-60 markets per batch) so no single command is huge.

- [ ] **Step 5: Validate the file**

Run:

```bash
python3 -B - <<'PY'
import sys, collections
sys.path.insert(0, ".")
import dataset_schema as D
rows = D.read_jsonl("../runs/kalshi_markets_raw.jsonl")
need = ["event_ticker","series_ticker","market_ticker","yes_subtitle","event_title","kalshi_category","open_ts","close_ts","event_start_ts","result","ladder_order","rules_primary"]
bad = [r["market_ticker"] for r in rows if any(k not in r for k in need)]
dups = [t for t, c in collections.Counter(r["market_ticker"] for r in rows).items() if c > 1]
print(len(rows), "rows;", len(bad), "missing fields;", len(dups), "duplicate tickers")
print(collections.Counter(r["kalshi_category"] for r in rows))
PY
```

Expected: 0 missing fields, 0 duplicates. Fix and re-run until true. Then run `python3 -B build_items.py prices-needed` and read `dropped` and the counts.

- [ ] **Step 6: Check supply against quotas and log it**

From the `prices-needed` report, `events` per category should be at least about 2x the quota (65/65/60/60), because rung banding, curation and the event cap each remove some. If a category is short, go back to Step 2-4 for more series in that category (economics: add international CPI, central banks, earnings, commodities; sports: more leagues; politics: courts and international; culture: charts, awards, launches). Write what was pulled and counts to `runs/kalshi_collection_log.md`. Run `check_structure.py`.

---

### Task 6: Pre-event price lookups (agent-driven)

**Files:**
- Modify (regenerate): `runs/prices_needed.jsonl` (created by the script)
- Create: `runs/kalshi_t0_prices.jsonl`

**Interfaces:**
- Consumes: `runs/prices_needed.jsonl` rows `{market_ticker, t0}`.
- Produces: `runs/kalshi_t0_prices.jsonl` rows `{market_ticker, t0_price}` for `build_items.py shortlist`.

- [ ] **Step 1: Generate the list**

Run: `python3 -B build_items.py prices-needed`
Expected: JSON report; `prices_needed` is at most 10 per ladder.

- [ ] **Step 2: Fetch each price**

For every row call `mcp__kalshi_mcp__get_market_history` with `ticker=<market_ticker>`, `end_ts=<t0 as Unix seconds>`, `hours_back=48`, `period_interval="60"`, `include_latest_before_start=false`. Take the closing price, in dollars, of the last candle that ends at or before t0. If there is no candle, `t0_price` is `null`. Never use a settled market's `last_price_dollars`. Run calls in parallel batches.

- [ ] **Step 3: Write and validate the file**

Append rows with `cat >> "$S/runs/kalshi_t0_prices.jsonl" <<'JSONL'` in batches, then check every ticker in `prices_needed.jsonl` has exactly one row and every non-null price is in (0, 1):

```bash
python3 -B - <<'PY'
import sys; sys.path.insert(0, ".")
import dataset_schema as D
need = {r["market_ticker"] for r in D.read_jsonl("../runs/prices_needed.jsonl")}
got = D.read_jsonl("../runs/kalshi_t0_prices.jsonl")
ids = [g["market_ticker"] for g in got]
print("needed", len(need), "got", len(ids), "missing", len(need - set(ids)), "dups", len(ids) - len(set(ids)))
print("out of range:", [g for g in got if g["t0_price"] is not None and not 0 < g["t0_price"] < 1][:5])
PY
```

Expected: 0 missing, 0 dups, empty out-of-range list.

- [ ] **Step 4: Shortlist**

Run: `python3 -B build_items.py shortlist`
Expected: report with `per_category` counts; `shortlisted` should be close to 1.6x each quota (104 / 104 / 96 / 96). If a category is far below, return to Task 5 Step 6 for more supply, then redo Steps 1-4 (delete nothing: append the new prices and re-run the scripts, which regenerate `prices_needed.jsonl` and `shortlist.jsonl`).

---

### Task 7: Curation and finalization (agent-driven)

For each shortlisted market, write the question in clear language and assign the real-world event.

**Files:**
- Create: `runs/curation.jsonl`
- Modify (regenerate): `runs/items_pre_brief.jsonl`, `runs/report_finalize.json`

**Interfaces:**
- Consumes: `runs/shortlist.jsonl` (fields include `market_ticker`, `yes_subtitle`, `event_title`, `rules_primary`, `t0`, `resolved_at`, `category`).
- Produces: `curation.jsonl` rows `{market_ticker, event_id, statement, negated_statement, resolution_criteria, drop}` and then `items_pre_brief.jsonl`.

- [ ] **Step 1: Read the shortlist**

Read `runs/shortlist.jsonl`. For any row whose rules are unclear, call `mcp__kalshi_mcp__get_market` for the full rules text.

- [ ] **Step 2: Write one curation row per shortlisted market**

Rules, all mandatory:

1. `statement` is a self-contained sentence, true if and only if the Kalshi market resolved YES, written as of the event ("US CPI-U rose more than 0.3% in August 2026."). No reference to Kalshi, prices, or "the market".
2. `negated_statement` is the exact logical negation, also self-contained, not a "not" bolted onto the front for awkward phrasing ("US CPI-U rose 0.3% or less in August 2026." for a threshold market). For "exactly X" ladders, use "did not equal X".
3. `resolution_criteria` states the data source, the exact quantity, adjustment (seasonal or not), which release counts (first release), and the time window.
4. `event_id` is a lowercase slug naming the real-world event, shared by every market about the same event across Kalshi series (`cpi-2026-08`, `fed-decision-2026-09`, `nfl-2026-w3-dal-phi`). At most 2 items per `event_id` survive later.
5. `drop: true` for anything ambiguous, subjective, dependent on a rule change, or about an event whose scheduled date is not a fixed known date before t0. For sports, drop if the game had already started at t0 (t0 is in the shortlist) or if the result depends on an unclear tie or forfeit rule.
6. Balance yes/no: do not systematically curate in favor of the more newsworthy outcome.

Append rows with `cat >> "$S/runs/curation.jsonl" <<'JSONL'` in batches of about 30.

- [ ] **Step 3: Validate coverage**

Run:

```bash
python3 -B - <<'PY'
import sys; sys.path.insert(0, ".")
import dataset_schema as D
sh = {r["market_ticker"] for r in D.read_jsonl("../runs/shortlist.jsonl")}
cu = D.read_jsonl("../runs/curation.jsonl")
ids = [c["market_ticker"] for c in cu]
print("shortlist", len(sh), "curated", len(set(ids)), "uncurated", len(sh - set(ids)), "unknown", len(set(ids) - sh), "dups", len(ids) - len(set(ids)))
print("dropped", sum(1 for c in cu if c.get("drop")))
PY
```

Expected: 0 uncurated, 0 unknown, 0 dups.

- [ ] **Step 4: Finalize**

Run: `python3 -B build_items.py finalize`
Expected: report with `final`, `after_event_cap`, `shortfall_vs_quota` per category (0 is the goal), `yes_rate_asked` near 0.5. If a category has a shortfall, return to Task 5 Step 6 (more supply) and re-run Tasks 6-7 for the added markets only, then finalize again. Any residual shortfall is reported in the write-up, not filled with weaker items.

- [ ] **Step 5: Structure check**

Run: `cd "$HOME/mnt/LLM Testing" && python3 -B tools/check_structure.py`
Expected: `0 problems, 0 warnings`.

---

### Task 8: Write the briefs (agent-driven, blind to outcome)

**Files:**
- Create: `design/brief_writer_prompt.md`
- Create: `runs/briefs.jsonl`

**Interfaces:**
- Consumes: `runs/items_pre_brief.jsonl`, but only these fields are ever shown to a writer: `item_id`, `category`, `asked_statement`, `resolution_criteria`, `t0`, `resolved_at`. Never `outcome`, `asked_outcome`, `market_price_t0`, `market_ticker`.
- Produces: `runs/briefs.jsonl` rows `{item_id, brief, brief_sources}`.

- [ ] **Step 1: Create the writer prompt template**

Create `design/brief_writer_prompt.md`:

```markdown
# Brief writer prompt (S013)

You are writing a pre-event briefing for a forecasting benchmark. For each item below you get the
question statement, the precise resolution criteria, the as-of time T0, and the category. You are
NOT given the outcome or any market price, and you must not look for either.

For each item, write a factual briefing of at most 400 words that a forecaster would want to have
read at T0. Rules:

1. Use only information published strictly BEFORE T0's calendar date. Use web search. Discard any page
   dated on or after T0's date, and never use a page that reports how the question resolved.
2. State facts, not predictions of the outcome: recent data prints, scheduled dates, recent form,
   injuries, base rates, consensus forecasts (economics), official statements, upcoming schedule. Do
   not say or hint which outcome is more likely.
3. Never mention prediction markets, Kalshi, Polymarket, betting odds, sportsbooks, moneylines or
   implied probabilities, and do not quote betting lines or point spreads as evidence.
4. Do not mention any date after the scheduled resolution date. The scheduled event date itself may be
   mentioned as upcoming.
5. Write as of T0: "is scheduled", "will be released", never "was released" for the event itself.
6. List every source you used: URL, title, and publication date (YYYY-MM-DD). Every source must be
   dated before T0's date. If you cannot find at least 2 qualifying sources, set status to
   "insufficient_sources" and leave brief empty.

Output exactly one JSON object per item, one per line, no other text:

{"item_id": "S013-0001", "brief": "...", "brief_sources": [{"url": "...", "title": "...", "published": "YYYY-MM-DD"}], "status": "ok"}

Items:
{ITEMS_JSON}
```

- [ ] **Step 2: Build blinded batches**

Write a temporary script under `scratch/` (not the study) that reads `items_pre_brief.jsonl` and emits batches of 5 items containing only the six allowed fields, as JSON arrays. Verify with a grep that no batch file contains the strings `outcome` or `market_price`.

- [ ] **Step 3: Dispatch writers**

For each batch, spawn one `Agent` (`subagent_type: general-purpose`, fresh context) with the template's text and `{ITEMS_JSON}` replaced by the batch. Run in waves of 8 parallel agents. Each returns one JSON line per item.

- [ ] **Step 4: Collect and validate**

Append returned lines with `cat >> "$S/runs/briefs.jsonl" <<'JSONL'`, drop any `"status": "insufficient_sources"` rows (record those `item_id`s), strip the `status` field, then run every brief through `check_brief`:

```bash
python3 -B - <<'PY'
import sys; sys.path.insert(0, ".")
import dataset_schema as D
from leak_check import check_brief
items = {i["item_id"]: i for i in D.read_jsonl("../runs/items_pre_brief.jsonl")}
briefs = D.read_jsonl("../runs/briefs.jsonl")
bad = 0
for b in briefs:
    it = items[b["item_id"]]
    r = check_brief(b["brief"], it["t0"], it["resolved_at"], b["brief_sources"])
    if not r["ok"]:
        bad += 1; print(b["item_id"], r["hard_fail"])
print(len(briefs), "briefs;", bad, "hard failures;", len(items) - len({b['item_id'] for b in briefs}), "items without a brief")
PY
```

Expected at the end: 0 hard failures and 0 items without a brief. For failures, re-dispatch those items to a fresh writer with the failure reason appended to the prompt, and replace their lines (rewrite `briefs.jsonl` keeping the newest line per `item_id`).

---

### Task 9: Independent leak check (agent-driven)

**Files:**
- Create: `design/brief_checker_prompt.md`
- Create: `runs/leak_llm.jsonl`

**Interfaces:**
- Consumes: `items_pre_brief.jsonl` and `briefs.jsonl`. A checker sees only: `item_id`, `asked_statement`, `resolution_criteria`, `t0`, `brief`, `brief_sources`. Never the outcome or price.
- Produces: `runs/leak_llm.jsonl` rows `{item_id, predicted_probability, flag, reason}`.

- [ ] **Step 1: Create the checker prompt template**

Create `design/brief_checker_prompt.md`:

```markdown
# Independent leak-checker prompt (S013)

You are auditing forecasting-benchmark briefings for leakage. For each item you see ONLY: the ASKED
statement, the resolution criteria, the as-of time T0, the briefing, and its sources. You do not know
the outcome and must not try to look it up.

For each item:

1. Read the briefing for any information dated after T0, or any wording that reveals or strongly
   implies how the ASKED statement resolved (past-tense reports of the event itself, results,
   figures released after T0, "eventually", "went on to"). Quote each suspect phrase.
2. Using ONLY the briefing (not your own memory of real events), give the probability, from 0 to 1,
   that the ASKED statement is true.
3. Set flag to true if you quoted anything in step 1 that is post-T0 or outcome-revealing, or if the
   briefing appears to name the answer. Otherwise false.

Output exactly one JSON object per item, one per line, no other text:

{"item_id": "S013-0001", "predicted_probability": 0.42, "flag": false, "reason": "one sentence; quote phrases if flagged"}

Items:
{ITEMS_JSON}
```

- [ ] **Step 2: Dispatch checkers**

Use fresh `Agent` subagents that did not write the briefs, batches of 5, waves of 8. Give each the template with `{ITEMS_JSON}` replaced. Append each returned JSON line to `runs/leak_llm.jsonl`.

- [ ] **Step 3: Validate**

Every `item_id` in `briefs.jsonl` has exactly one row in `leak_llm.jsonl`, `predicted_probability` is in [0, 1], `flag` is boolean. Fix and re-dispatch any missing rows.

- [ ] **Step 4: Note the caveat**

Record in the eventual write-up that the checker is a Claude model whose own knowledge might include real events; the instruction is to use only the brief, but a confidently correct prediction is itself treated as suspicious in `assemble_dataset.py` (any checker probability of at least 0.95 or at most 0.05 that matches the asked outcome flags the item for the hand audit).

---

### Task 10: Assemble, audit, freeze

**Files:**
- Create (generated): `runs/dataset_candidate.jsonl`, `runs/dataset_rejects.jsonl`, `runs/audit_sheet.csv`, `runs/dataset_v1.jsonl`, `runs/dataset_v1.jsonl.sha256`

**Interfaces:**
- Consumes: `items_pre_brief.jsonl`, `briefs.jsonl`, `leak_llm.jsonl`.
- Produces: the frozen `dataset_v1.jsonl` that Plan B reads.

- [ ] **Step 1: Assemble**

Run: `python3 -B assemble_dataset.py`
Expected: report with `rejected` 0 (otherwise inspect `runs/dataset_rejects.jsonl`, fix the cause in briefs or curation, and re-run), `per_category` `have` equal to quota, and `flagged_for_audit` (the count the hand audit must cover).

- [ ] **Step 2: Make the audit sheet**

Run: `python3 -B audit_sample.py make`
Expected: `runs/audit_sheet.csv` with every flagged item plus a random 10% of the rest.

- [ ] **Step 3: Hand audit (user)**

Ask the user to open `runs/audit_sheet.csv`, and for each row read the brief against `asked_statement` and `t0`, then set `human_verdict` to `ok`, `drop`, or `rewrite`. Offer to do a first pass and mark obvious `ok` rows, but the user confirms.

- [ ] **Step 4: Apply and freeze**

Run: `python3 -B audit_sample.py apply`
Expected: refuses with `cannot freeze` while any row is blank or `rewrite`; once all rows are `ok` or `drop`, writes `runs/dataset_v1.jsonl` and `runs/dataset_v1.jsonl.sha256` and prints `items`, `dropped_in_audit`, `sha256`, `per_category`. If drops leave a category below quota, either accept and report it or return to Task 7.

- [ ] **Step 5: Verify the freeze**

Run: `python3 -B -c "import dataset_schema as D; print(D.verify('../runs/dataset_v1.jsonl'))"`
Expected: `True`. From now on `dataset_v1.jsonl` is never edited; changes create `dataset_v2.jsonl`.

---

### Task 11: Close-out and hand-off

**Files:**
- Modify: `README.md` (this study), `notes/2026-09-26-dataset-design.md` (link to the result), root `INDEX.md`
- Create: `notes/YYYY-MM-DD-dataset-v1-build.md` (use the execution date)

- [ ] **Step 1: Write the build note**

`notes/YYYY-MM-DD-dataset-v1-build.md`: counts per category (have vs quota), drop and reject counts with reasons, how many items were flagged and audited and how many dropped, yes-rate of asked outcomes overall and per category, the price-band distribution of `market_price_t0`, the dataset SHA-256, and the caveats: single writer model and single checker model, 25-day window, no sportsbook lines allowed in briefs but "favored by" style wording may still carry implied information, a single-rater hand audit covering every flagged item plus about 10% of the rest, t0 prices from hourly candles, floor evidence from `notes/2026-09-26-floor-probe-round1.md`.

- [ ] **Step 2: Update README, INDEX, Project**

Keep the study README status `planned` (model runs have not started) and state "dataset v1 frozen, sha256 <digest>" in Findings; update the INDEX row's Headline, run `check_structure.py`, then sync `INDEX.md` and the build note to the Project docs (`project_write` after staging).

- [ ] **Step 3: Hand off to Plan B**

Write Plan B (`notes/YYYY-MM-DD-implementation-plan-model-run.md`) for: `run_models.py` (18 Poe models, temperature 0, 1 replicate, probability output parsing, resumable, `runs/` output), `scoring_lib.py` (Brier, log loss, calibration bins, cluster bootstrap by `event_id`, per-category and overall, baselines Kalshi t0 price / base rate / 0.5), analysis script and charts, results note with all caveats. Scope Plan B only after the dataset is frozen so it can use real item counts.

---

## Self-review (done while writing)

- **Spec coverage:** floor (Global Constraints, `select_lib`), unit of analysis / ladder rules / band / cap / parlays (Tasks 1, 4, 5-7), categories and quotas (Tasks 1, 4, 7, 10), t0 and brief content (Tasks 1, 2, 8), leak control writer + checker + hand audit (Tasks 2, 8, 9, 10), schema and freeze (Tasks 3, 10), pipeline stages 1-6 of the design (floor probe already done; 2-6 = Tasks 5-10), stage 7 (model run, scoring) is explicitly deferred to Plan B (Task 11). Dropped from the spec: nothing else.
- **Placeholders:** none; every code step has full file content, every procedural step has exact tool parameters or commands.
- **Type consistency:** function and field names are the ones in the embedded files (checked by the passing smoke test): `market_ticker`, `t0_price`, `event_id`, `asked_statement`, `asked_outcome`, `polarity_flipped`, `leak_check{mechanical_ok, mechanical_warnings, llm_flag, llm_reason, llm_predicted_probability, llm_suspicious_confident_correct}`.
- **Known limits carried into execution:** collection speed is bounded by MCP call volume; the shortlist-to-quota margin (1.6x) may need supply top-ups; the writer can still encounter post-t0 pages through web search, which is why sources are checked by date and the checker plus hand audit exist.
