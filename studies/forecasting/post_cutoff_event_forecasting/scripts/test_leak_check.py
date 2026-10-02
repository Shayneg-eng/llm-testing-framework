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
