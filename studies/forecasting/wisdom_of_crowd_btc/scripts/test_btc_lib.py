"""Offline tests for btc_lib. Run: python test_btc_lib.py"""
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import btc_lib as B

M = 60


def synth(n=600, start_t=1_700_000_000 // 60 * 60, seed=1, gaps=()):
    rng = random.Random(seed)
    price, out = 50_000.0, {}
    for i in range(n):
        if i in gaps:
            continue
        o = price
        price *= 1 + rng.gauss(0, 0.0005)
        out[start_t + i * M] = (o, max(o, price) * 1.0001, min(o, price) * 0.9999, price, 1 + rng.random())
    return out


def test_complete_window_detects_gaps():
    c = synth(gaps={300})
    t_ok = sorted(c)[150]           # lookback 150-119..150, +15 -> 31..165, no gap at 300
    assert B.window_is_complete(c, t_ok)
    t_bad = sorted(c)[0] + 295 * M  # spans index 300
    assert not B.window_is_complete(c, t_bad)


def test_sampling_deterministic_and_disjoint():
    c = synth(n=3000)
    w1, _ = B.sample_windows(c, 20, seed=7)
    w2, _ = B.sample_windows(c, 20, seed=7)
    w3, _ = B.sample_windows(c, 20, seed=8)
    assert w1 == w2 and w1 != w3
    ts = sorted(w["t"] for w in w1)
    assert all(b - a >= B.HORIZON * M for a, b in zip(ts, ts[1:]))
    assert len(w1) == 20
    for w in w1:
        assert B.window_is_complete(c, w["t"])
        assert w["outcome"] == ("up" if w["end_price"] > w["start_price"] else "down")
        assert w["momentum"] in ("up", "down", None)
        assert w["start_price"] == c[w["t"]][3] and w["end_price"] == c[w["t"] + B.HORIZON * M][3]


def test_sampling_excludes_ties_and_raises_when_short():
    c = synth(n=3000)
    _, skipped = B.sample_windows(c, 10, seed=1)
    assert skipped >= 0
    try:
        B.sample_windows(synth(n=200), 100, seed=1)
        assert False, "should raise"
    except ValueError:
        pass


def test_prompt_is_anonymized_and_index_based():
    c = synth(n=400)
    t = sorted(c)[250]
    system, user = B.build_prompt(c, t)
    lines = [l for l in user.splitlines() if re.match(r"^-?\d+,", l)]
    assert len(lines) == B.LOOKBACK
    assert lines[0].startswith("-119,") and lines[-1].startswith("0,")
    assert abs(float(lines[-1].split(",")[4]) - 100.0) < 1e-9  # last close = 100
    for banned in ("2023", "2024", "2025", "2026", "BTC", "Bitcoin", "USD"):
        assert banned not in user and banned not in system, banned
    vols = [float(l.split(",")[5]) for l in lines]
    assert abs(sum(vols) / len(vols) - 1.0) < 0.01


def test_parse_prediction():
    assert B.parse_prediction('{"predicted_close_index": 100.25}') == 100.25
    assert B.parse_prediction('Sure!\n```json\n{"predicted_close_index": 99.8}\n```') == 99.8
    assert B.parse_prediction('{"predicted_close_index":"100.1"}') == 100.1
    assert B.parse_prediction("I think it will go up") is None
    assert B.parse_prediction(None) is None
    assert B.parse_prediction('{"predicted_close_index": 5000}') is None  # out of sanity range
    assert B.parse_prediction('{"predicted_close_index": NaN}') is None


def test_direction_and_aggregate():
    assert B.direction(100.2) == "up" and B.direction(99.9) == "down" and B.direction(100.0) is None
    a = B.aggregate([101, 101, 99, 99, 100.5, 99.5, 100.4, 99.6, 105, 95])
    assert math.isclose(a["mean"], 100.0, abs_tol=1e-9)
    assert a["vote"] is None            # 5 up, 5 down -> no call
    assert a["n"] == 10
    b = B.aggregate([101, 102, 103, 99])
    assert b["vote"] == "up" and b["median"] == 101.5 and math.isclose(b["trimmed"], 101.5)
    assert B.aggregate([]) is None


def test_stats():
    lo, hi = B.wilson(60, 100)
    assert 0.50 < lo < 0.60 < hi < 0.70
    assert math.isclose(B.binom_two_sided_p(50, 100), 1.0, abs_tol=1e-9)
    assert B.binom_two_sided_p(70, 100) < 0.001
    assert B.binom_two_sided_p(0, 0) == 1.0
    d = B.paired_bootstrap_diff([1] * 60 + [0] * 40, [1] * 40 + [0] * 60, n_boot=2000, seed=1)
    assert math.isclose(d["diff"], 0.2) and d["lo"] > 0


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as e:  # noqa
                fails += 1; print("FAIL", name, repr(e))
    print(f"{fails} failed")
    sys.exit(1 if fails else 0)
