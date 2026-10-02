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
