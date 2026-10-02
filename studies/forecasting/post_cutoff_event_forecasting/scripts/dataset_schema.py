"""S013 dataset row schema, validation, JSONL io and freezing. Tested by test_dataset_schema.py."""
import hashlib
import json
from pathlib import Path

from leak_check import check_brief
from select_lib import CATEGORIES, FLOOR, parse_ts

REQUIRED = ["item_id", "event_id", "category", "source", "market_ticker", "statement", "negated_statement",
            "polarity_flipped", "asked_statement", "resolution_criteria", "t0", "resolved_at", "outcome",
            "asked_outcome", "market_price_t0", "brief", "brief_sources", "leak_check", "audited"]
LEAK_KEYS = ["mechanical_ok", "llm_flag", "llm_predicted_probability"]


def validate_item(it):
    """List of problems (empty = valid)."""
    errs = [f"missing field: {k}" for k in REQUIRED if k not in it]
    if errs:
        return errs
    if it["category"] not in CATEGORIES:
        errs.append(f"bad category: {it['category']}")
    if it["outcome"] not in (0, 1) or it["asked_outcome"] not in (0, 1):
        errs.append("outcome/asked_outcome must be 0 or 1")
    else:
        want = 1 - it["outcome"] if it["polarity_flipped"] else it["outcome"]
        if it["asked_outcome"] != want:
            errs.append("asked_outcome inconsistent with polarity_flipped")
    want_stmt = it["negated_statement"] if it["polarity_flipped"] else it["statement"]
    if it["asked_statement"] != want_stmt:
        errs.append("asked_statement inconsistent with polarity_flipped")
    p = it["market_price_t0"]
    if p is not None and not (0 < p < 1):
        errs.append("market_price_t0 must be in (0,1) or null")
    try:
        if parse_ts(it["resolved_at"]) < parse_ts(FLOOR):
            errs.append("resolved before the floor")
        if not parse_ts(it["t0"]) < parse_ts(it["resolved_at"]):
            errs.append("t0 must be before resolved_at")
    except (ValueError, TypeError):
        errs.append("t0/resolved_at not ISO timestamps")
        return errs
    lk = it["leak_check"]
    errs += [f"leak_check missing {k}" for k in LEAK_KEYS if not isinstance(lk, dict) or k not in lk]
    rep = check_brief(it["brief"], it["t0"], it["resolved_at"], it["brief_sources"])
    errs += rep["hard_fail"]
    return errs


def write_jsonl(path, items):
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, sort_keys=True, ensure_ascii=False) + "\n")


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def freeze(path):
    """Write <path>.sha256 and return the hex digest. Do this before any model sees the dataset."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def verify(path):
    path = Path(path)
    want = Path(str(path) + ".sha256").read_text(encoding="utf-8").split()[0]
    return hashlib.sha256(path.read_bytes()).hexdigest() == want
