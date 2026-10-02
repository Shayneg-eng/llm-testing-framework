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
