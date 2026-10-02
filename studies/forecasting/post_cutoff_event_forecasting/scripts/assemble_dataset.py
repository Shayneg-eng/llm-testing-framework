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
