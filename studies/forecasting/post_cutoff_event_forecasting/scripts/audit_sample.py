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
