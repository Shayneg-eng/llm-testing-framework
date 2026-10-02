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
