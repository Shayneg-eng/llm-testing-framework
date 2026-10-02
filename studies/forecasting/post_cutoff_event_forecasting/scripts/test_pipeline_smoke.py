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
