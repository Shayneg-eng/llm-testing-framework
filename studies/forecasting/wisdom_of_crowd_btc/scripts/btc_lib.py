"""Pure logic for S012 wisdom_of_crowd_btc: no network, no fixed paths.

Candles are dicts {open_time_unix_seconds: (open, high, low, close, volume)}.
Decision candle T: its close is the START price; the close of candle T+15min is the END price.
"""
import csv
import json
import math
import random
import re
import statistics
from pathlib import Path

LOOKBACK = 120          # candles shown to the models (T-119 .. T)
HORIZON = 15            # minutes ahead
STEP = 60
PRICE_SANITY = (80.0, 120.0)   # accepted range for predicted index (last close = 100)

SYSTEM_PROMPT = (
    "You are a quantitative forecaster. You are given a recent history of 1-minute candles for a "
    "liquid market, rescaled so the most recent close equals 100. Predict the close price index "
    "exactly 15 minutes after the last candle. Answer with a single JSON object and nothing else: "
    '{"predicted_close_index": <number>}'
)


# ---------- candle IO ----------
def save_candles(path, candles):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for t in sorted(candles):
            w.writerow([t, *candles[t]])


def load_candles(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[int(r["time"])] = (float(r["open"]), float(r["high"]), float(r["low"]),
                                   float(r["close"]), float(r["volume"]))
    return out


def coinbase_rows_to_candles(rows):
    """Coinbase row = [time, low, high, open, close, volume]."""
    return {int(t): (float(o), float(h), float(l), float(c), float(v)) for t, l, h, o, c, v in rows}


# ---------- windows ----------
def window_is_complete(candles, t):
    return all((t + k * STEP) in candles for k in range(-(LOOKBACK - 1), HORIZON + 1))


def sample_windows(candles, n, seed):
    """n windows with pairwise-disjoint outcome intervals. Returns (windows, skipped_ties)."""
    cands = [t for t in sorted(candles) if window_is_complete(candles, t)]
    rng = random.Random(seed)
    rng.shuffle(cands)
    chosen, skipped_ties = [], 0
    for t in cands:
        if len(chosen) == n:
            break
        if any(abs(t - u) < HORIZON * STEP for u in chosen):
            continue
        if candles[t + HORIZON * STEP][3] == candles[t][3]:
            skipped_ties += 1
            continue
        chosen.append(t)
    if len(chosen) < n:
        raise ValueError(f"only {len(chosen)} valid disjoint windows available, need {n}")
    windows = []
    for i, t in enumerate(sorted(chosen)):
        s, e = candles[t][3], candles[t + HORIZON * STEP][3]
        windows.append({"window_id": f"w{i:03d}", "t": t, "start_price": s, "end_price": e,
                        "outcome": "up" if e > s else "down",
                        "momentum": momentum_direction(candles, t)})
    return windows, skipped_ties


def momentum_direction(candles, t):
    """Baseline: repeat the direction of the previous HORIZON minutes (None if flat)."""
    a, b = candles[t - HORIZON * STEP][3], candles[t][3]
    return "up" if b > a else "down" if b < a else None


# ---------- prompt ----------
def build_prompt(candles, t):
    base = candles[t][3]
    ts = [t + k * STEP for k in range(-(LOOKBACK - 1), 1)]
    vmean = statistics.fmean(candles[x][4] for x in ts) or 1.0
    lines = ["offset_min,open,high,low,close,volume_rel"]
    for k, x in zip(range(-(LOOKBACK - 1), 1), ts):
        o, h, l, c, v = candles[x]
        lines.append(f"{k},{o / base * 100:.3f},{h / base * 100:.3f},{l / base * 100:.3f},"
                     f"{c / base * 100:.3f},{v / vmean:.2f}")
    user = ("1-minute candles, oldest first. offset_min 0 is the most recent candle; its close is "
            "100. volume_rel is volume divided by the mean volume of this window.\n\n"
            + "\n".join(lines)
            + "\n\nPredict the close price index 15 minutes after offset 0. "
              'Reply only with JSON: {"predicted_close_index": <number>}')
    return SYSTEM_PROMPT, user


# ---------- parsing / aggregation ----------
_NUM = r'(-?\d+(?:\.\d+)?)'
_KEY = re.compile(r'"predicted_close_index"\s*:\s*"?' + _NUM)


def parse_prediction(text):
    if not text:
        return None
    m = _KEY.search(text)
    if not m:
        return None
    v = float(m.group(1))
    lo, hi = PRICE_SANITY
    return v if math.isfinite(v) and lo <= v <= hi else None


def direction(pred):
    return "up" if pred > 100 else "down" if pred < 100 else None


def aggregate(preds):
    if not preds:
        return None
    s = sorted(preds)
    trimmed = statistics.fmean(s[1:-1]) if len(s) >= 3 else statistics.fmean(s)
    ups = sum(p > 100 for p in preds)
    downs = sum(p < 100 for p in preds)
    vote = "up" if ups > downs else "down" if downs > ups else None
    return {"mean": statistics.fmean(preds), "median": statistics.median(preds),
            "trimmed": trimmed, "vote": vote, "n": len(preds), "ups": ups, "downs": downs}


# ---------- stats ----------
def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def binom_two_sided_p(k, n, p=0.5):
    if n == 0:
        return 1.0
    pmf = [math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in pmf if x <= pmf[k] * (1 + 1e-9)))


def paired_bootstrap_diff(a, b, n_boot=10000, seed=0):
    """a, b: paired 0/1 correctness lists. Returns mean(a)-mean(b) with 95% bootstrap CI."""
    rng = random.Random(seed)
    n = len(a)
    diffs = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    return {"diff": sum(a) / n - sum(b) / n,
            "lo": diffs[int(0.025 * n_boot)], "hi": diffs[int(0.975 * n_boot) - 1]}
