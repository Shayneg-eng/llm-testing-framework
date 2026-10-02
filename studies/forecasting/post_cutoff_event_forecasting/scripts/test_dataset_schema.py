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
