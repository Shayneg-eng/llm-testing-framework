#!/usr/bin/env python3
import os
"""S013 post_cutoff_event_forecasting: floor-verification probe.

Asks every candidate model (a) its own training-data cutoff and (b) two facts that were first
published in September 2026 (US CPI for August 2026, released 2026-09-11). A model that answers
(b) correctly has a cutoff at or past the provisional floor (2026-09-01). See
notes/2026-09-26-dataset-design.md, section 1.

    python floor_probe.py                       # query all models once
    python floor_probe.py --reps 3              # 3 independent asks per model (guards against lucky guesses)
    python floor_probe.py --only Kimi-K3,Muse-Spark-1.1
    python floor_probe.py --resume ../runs/floor_probe_<ts>.jsonl    # re-ask only missing/failed pairs
    python floor_probe.py --list-models         # save Poe's live model ids + closest match for each name below
    python floor_probe.py --dry-run             # offline, fake models, writes to ROOT/scratch/

Outputs (runs/, append-only): floor_probe_<ts>.jsonl (raw + parsed per ask),
floor_probe_<ts>_summary.csv (one row per model), audit_log_floor_probe_<ts>.json.
Every model is called WITHOUT tools or web search; the prompt also tells it not to use any.
"""
import argparse
import csv
import json
import re
import sys
import threading
import time
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[4]          # .../LLM Testing
_sys.path.insert(0, str(ROOT / "shared"))

STUDY_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = STUDY_DIR / "runs"
DRYRUN_DIR = ROOT / "scratch" / "floor_probe_dryrun"

POE_API_KEY = os.getenv("POE_API_KEY", "")   # testing only (project policy); never copy into results/
POE_BASE_URL = "https://api.poe.com/v1"
MAX_TOKENS = 4000
MAX_ATTEMPTS = 3

# The 18 candidate models that Poe's API actually serves (round 1, 2026-09-26). The other 14 names in the
# Project doc "Poe Model Names" are NOT on the API and 404: GPT-6-Astra, GPT-6-Sol, GPT-6-Luna, GPT-5.6-Sol,
# GPT-5.6-Terra, GPT-5.6-Luna, GPT-5.5, GPT-5.5-Pro, Claude-Fable-5.1, Claude-Fable-5, Claude-Opus-5,
# Claude-Opus-5.5, Claude-Sonnet-5, Gemini-Omni-Flash. See notes/2026-09-26-floor-probe-round1.md.
MODELS = [
    "Gemini-3.8-Flash", "Gemini-3.7-Flash", "Gemini-3.6-Flash", "Gemini-3.5-Flash", "Gemini-3.5-Flash-Lite",
    "Gemini-Omni-1.1-Flash", "Grok-4.7", "Grok-4.6", "Grok-4.5", "Grok-4.3", "Kimi-K3", "Inkling",
    "Muse-Spark-1.1", "Claude-Opus-4.8", "GPT-5.4", "GPT-5.4-Mini", "GPT-5.4-Nano", "GPT-OSS-120B-CS",
]

PROMPT = """Answer these three questions. Do not use web search or any tools. If you don't know, say "I don't know" rather than guessing.

1. What is the most recent month and year your training data covers? Give your best estimate.
2. What was the US CPI inflation rate, year over year, for August 2026 (the headline figure released in September 2026)?
3. What was the US core CPI inflation rate, year over year, for August 2026?

For each answer, say how confident you are (low / medium / high).

Reply in exactly this format, one line per question:
Q1: <month and year> | confidence: <low/medium/high>
Q2: <number>% or I don't know | confidence: <low/medium/high>
Q3: <number>% or I don't know | confidence: <low/medium/high>"""

# Answer key. Confirmed 2026-09-26 against the BLS CPI news release for August 2026
# (https://www.bls.gov/news.release/cpi.nr0.htm, released 2026-09-11): all items CPI-U
# +3.4% over 12 months, all items less food and energy +2.4%. Also matches the settled
# Kalshi markets KXECONSTATCPIYOY-26AUG and KXECONSTATCORECPIYOY-26AUG.
KEY_CPI_YOY = 3.4
KEY_CORE_YOY = 2.4
TOLERANCE = 0.05          # answers must match to one decimal
FLOOR_YM = "2026-09"


# ---------- parsing ----------
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], 1)}
ABBR = {k[:3]: v for k, v in MONTHS.items()}
LABEL = re.compile(r"^\W*(?:Q\s*)?([123])\s*[:.)\-]\s*(.*)$", re.I)
DK = re.compile(r"don'?t know|do not know|unknown|not sure|cannot|can'?t|unable|no information", re.I)


def parse_answers(text):
    ans = {}
    for line in (text or "").splitlines():
        clean = line.replace("*", "").replace("`", "").strip()
        m = LABEL.match(clean)
        if not m:
            continue
        num, rest = m.group(1), m.group(2).strip()
        if not rest or rest.endswith("?") or num in ans:
            continue
        ans[num] = rest
    return ans


def parse_confidence(s):
    m = re.search(r"confidence\W*(low|medium|high)", s, re.I) or re.search(r"\b(low|medium|high)\b", s, re.I)
    return m.group(1).lower() if m else None


def parse_pct(s):
    """-> (value or None, said_dont_know)."""
    if not s:
        return None, False
    head = re.split(r"confidence", s, flags=re.I)[0]
    dk = bool(DK.search(head))
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:%|percent)", head)
    if m:
        return float(m.group(1)), dk
    if not dk:
        m = re.search(r"(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d])", head)
        if m and 0 <= float(m.group(1)) <= 25:
            return float(m.group(1)), False
    return None, dk


def parse_year_month(s):
    if not s:
        return None
    low = s.lower()
    m = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december"
                  r"|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\b\.?,?\s+(20\d\d)", low)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)] if m.group(1) in MONTHS else ABBR[m.group(1)[:3]]:02d}"
    m = re.search(r"(20\d\d)[-/](\d{1,2})", low)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"(20\d\d)", low)
    return m.group(1) if m else None


def parse_record(text):
    a = parse_answers(text)
    cpi, cpi_dk = parse_pct(a.get("2"))
    core, core_dk = parse_pct(a.get("3"))
    ym = parse_year_month(a.get("1"))
    return {
        "parsed_ok": all(k in a for k in ("1", "2", "3")),
        "cutoff_claim": (a.get("1") or "")[:120] or None,
        "claimed_ym": ym,
        "claims_cutoff_at_or_past_floor": bool(ym and len(ym) == 7 and ym >= FLOOR_YM),
        "cpi_yoy_answer": cpi, "cpi_dont_know": cpi_dk, "cpi_conf": parse_confidence(a.get("2", "")),
        "core_yoy_answer": core, "core_dont_know": core_dk, "core_conf": parse_confidence(a.get("3", "")),
        "cpi_correct": cpi is not None and abs(cpi - KEY_CPI_YOY) < TOLERANCE,
        "core_correct": core is not None and abs(core - KEY_CORE_YOY) < TOLERANCE,
    }


SEVERITY = ["PAST_FLOOR", "AMBIGUOUS", "STALE_OR_GUESS", "BEFORE_FLOOR_LIKELY", "UNPARSED", "NO_RESPONSE"]


def verdict_for(rec):
    if rec.get("error") or not rec.get("raw"):
        return "NO_RESPONSE"
    n = int(bool(rec.get("cpi_correct"))) + int(bool(rec.get("core_correct")))
    if n == 2:
        return "PAST_FLOOR"
    if n == 1:
        return "AMBIGUOUS"
    if rec.get("cpi_yoy_answer") is None and rec.get("core_yoy_answer") is None:
        return "BEFORE_FLOOR_LIKELY" if rec.get("parsed_ok") else "UNPARSED"
    return "STALE_OR_GUESS"


# ---------- model calls ----------
_client = None
_client_lock = threading.Lock()


def get_client():
    global _client
    with _client_lock:
        if _client is None:
            import openai
            _client = openai.OpenAI(api_key=POE_API_KEY, base_url=POE_BASE_URL, timeout=180)
    return _client


def live_call(model):
    client = get_client()
    kwargs = dict(model=model, max_tokens=MAX_TOKENS, temperature=0,
                  messages=[{"role": "user", "content": PROMPT}])
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        if "temperature" in str(e).lower():      # some reasoning models reject temperature
            kwargs.pop("temperature")
            resp = client.chat.completions.create(**kwargs)
        else:
            raise
    ch = resp.choices[0]
    return ch.message.content, ch.finish_reason


def fake_call(model):
    """Offline stand-in: deterministic per model; covers each verdict and some junk."""
    rng = random.Random(model)
    r = rng.random()
    if r < 0.15:
        return "", "stop"
    if r < 0.30:
        return "Sorry, I can't help with that.", "stop"
    if r < 0.50:
        return ("Q1: August 2026 | confidence: medium\nQ2: 3.4% | confidence: high\n"
                "Q3: 2.4% | confidence: medium"), "stop"
    if r < 0.60:
        return ("**Q1:** March 2026 | confidence: low\n**Q2:** 3.4% | confidence: low\n"
                "**Q3:** I don't know | confidence: high"), "stop"
    if r < 0.80:
        return ("1. What is the most recent month and year your training data covers?\n"
                "Q1: I don't know exactly, around mid-2025 | confidence: low\n"
                "Q2: I don't know | confidence: high\nQ3: I don't know | confidence: high"), "stop"
    return ("1: June 2025 (confidence: medium)\n2: 2.9% (confidence: low)\n"
            "3: 3.1 percent (confidence: low)"), "stop"


def probe_one(model, rep, dry_run):
    rec = {"model": model, "rep": rep, "raw": None, "finish_reason": None, "attempts": 0,
           "error": None, "latency_s": None, "ts": None}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        rec["attempts"] = attempt
        t0 = time.time()
        try:
            text, fr = fake_call(model) if dry_run else live_call(model)
            rec.update(raw=(text or "")[:4000], finish_reason=fr, error=None,
                       latency_s=round(time.time() - t0, 2),
                       ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            if text and text.strip():
                break
            rec["error"] = "empty_response"
        except Exception as e:
            code = getattr(e, "status_code", None)
            rec.update(error=f"{type(e).__name__}: {str(e)[:300]}", latency_s=round(time.time() - t0, 2),
                       ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            if code in (400, 401, 402, 403, 404, 413):    # not retryable
                break
        if attempt < MAX_ATTEMPTS:
            time.sleep(min(30, 0.5 * 2 ** attempt) + random.random())
    rec.update(parse_record(rec["raw"]) if rec.get("raw") else {})
    rec["verdict"] = verdict_for(rec)
    return rec


def check_names(models):
    try:
        ids = {m.id.lower() for m in get_client().models.list()}
    except Exception as e:
        print(f"  (could not list Poe models: {type(e).__name__}: {str(e)[:120]}; skipping name check)")
        return None
    missing = [m for m in models if m.lower() not in ids]
    print(f"  Poe lists {len(ids)} models; {len(models) - len(missing)}/{len(models)} requested names found."
          + (f" NOT FOUND: {', '.join(missing)}" if missing else ""))
    return missing


def list_models(dry_run):
    """Fetch Poe's live /v1/models ids, save them, and suggest the closest id for every name in MODELS
    that Poe does not list. Use this when a run reports 404 'model not found'."""
    import difflib
    out_dir = DRYRUN_DIR if dry_run else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        data = [{"id": i, "owned_by": "fake", "description": ""} for i in
                ["gpt-5.4", "gpt-5.4-mini", "gemini-3.7-flash", "grok-4.3", "claude-opus-4.8",
                 "claude-sonnet-4.6", "claude-opus-4.7", "gpt-5.3-codex", "kimi-k3"]]
    else:
        raw = get_client().models.list()
        data = [{"id": m.id, "owned_by": getattr(m, "owned_by", None),
                 "description": (getattr(m, "description", "") or "")[:120],
                 "created": getattr(m, "created", None)} for m in raw]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"poe_models_{ts}.json"
    path.write_text(json.dumps(sorted(data, key=lambda d: d["id"].lower()), indent=2), encoding="utf-8")
    ids = {d["id"].lower(): d["id"] for d in data}
    print(f"Poe lists {len(ids)} models -> {path.relative_to(ROOT)}")
    found = [m for m in MODELS if m.lower() in ids]
    missing = [m for m in MODELS if m.lower() not in ids]
    print(f"\n{len(found)}/{len(MODELS)} requested names are valid API ids.")
    if missing:
        print(f"\n{len(missing)} names are NOT listed. Closest listed ids (edit MODELS in this script, or use --only):")
        for m in missing:
            close = difflib.get_close_matches(m.lower(), list(ids), n=3, cutoff=0.5)
            print(f"  {m:<24} -> " + (", ".join(ids[c] for c in close) if close else "(no close match; probably not on the API)"))


# ---------- io ----------
def load_records(path):
    recs = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return recs


def latest_by_pair(records):
    """Latest record per (model, rep), preferring a successful one over a failed one."""
    best = {}
    for r in records:
        k = (r["model"], r["rep"])
        ok = not r.get("error") and bool(r.get("raw"))
        if k not in best or ok or not (not best[k].get("error") and best[k].get("raw")):
            best[k] = r
    return best


def ans_str(r, which):
    v = r.get(f"{which}_yoy_answer")
    if v is not None:
        return str(v)
    return "DK" if r.get(f"{which}_dont_know") else "-"


def summarize(records, models, reps, csv_path):
    best = latest_by_pair(records)
    by_model = defaultdict(list)
    for (m, _rep), r in best.items():
        by_model[m].append(r)
    rows = []
    for m in models:
        rs = sorted(by_model.get(m, []), key=lambda r: r["rep"])
        vs = [r["verdict"] for r in rs] or ["NO_RESPONSE"]
        overall = min(vs, key=SEVERITY.index)
        rows.append({
            "model": m, "verdict": overall,
            "reps_ok": sum(1 for r in rs if not r.get("error") and r.get("raw")), "reps_target": reps,
            "cutoff_claims": " || ".join(str(r.get("cutoff_claim") or "-") for r in rs),
            "claimed_ym": " | ".join(str(r.get("claimed_ym") or "-") for r in rs),
            "claims_past_floor": any(r.get("claims_cutoff_at_or_past_floor") for r in rs),
            "cpi_answers": " | ".join(ans_str(r, "cpi") for r in rs),
            "core_answers": " | ".join(ans_str(r, "core") for r in rs),
            "cpi_correct": sum(bool(r.get("cpi_correct")) for r in rs),
            "core_correct": sum(bool(r.get("core_correct")) for r in rs),
            "confidences": " | ".join(f"{r.get('cpi_conf')}/{r.get('core_conf')}" for r in rs),
            "finish_reasons": ",".join(str(r.get("finish_reason")) for r in rs),
            "errors": "; ".join(str(r.get("error")) for r in rs if r.get("error")),
        })
    rows.sort(key=lambda x: (SEVERITY.index(x["verdict"]), x["model"]))
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def print_table(rows):
    print(f"\n{'model':<24}{'verdict':<22}{'CPI':<10}{'core':<10}{'says cutoff (parsed)':<22}")
    print("-" * 88)
    for r in rows:
        print(f"{r['model']:<24}{r['verdict']:<22}{r['cpi_answers'][:9]:<10}{r['core_answers'][:9]:<10}{r['claimed_ym'][:20]:<22}")
    counts = defaultdict(int)
    for r in rows:
        counts[r["verdict"]] += 1
    print("\n" + ", ".join(f"{v}: {counts[v]}" for v in SEVERITY if counts[v]))
    print(f"Answer key (BLS, released 2026-09-11): CPI YoY Aug 2026 = {KEY_CPI_YOY}%, core = {KEY_CORE_YOY}%.")
    print("PAST_FLOOR = both correct (cutoff likely at/after 2026-09: flag or exclude). "
          "AMBIGUOUS = one correct (re-run with --reps 3). "
          "BEFORE_FLOOR_LIKELY = said don't know (fine to keep). Read the raw replies in the .jsonl before deciding.")


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=1, help="independent asks per model (default 1)")
    ap.add_argument("--only", default="", help="comma-separated model names to query")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", default="", help="existing floor_probe_<ts>.jsonl to continue")
    ap.add_argument("--dry-run", action="store_true", help="offline fake models; writes to ROOT/scratch/")
    ap.add_argument("--list-models", action="store_true", help="save Poe's live model ids and suggest fixes for bad names")
    args = ap.parse_args()
    if args.list_models:
        list_models(args.dry_run)
        return

    only = [m.strip() for m in args.only.split(",") if m.strip()]
    models = only or MODELS
    out_dir = DRYRUN_DIR if args.dry_run else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.resume:
        jsonl = Path(args.resume).resolve()
        ts = jsonl.stem.replace("floor_probe_", "")
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        jsonl = out_dir / f"floor_probe_{ts}.jsonl"
    existing = load_records(jsonl)
    best_existing = latest_by_pair(existing)
    done = {k for k, r in best_existing.items() if not r.get("error") and r.get("raw")}
    todo = [(m, rep) for m in models for rep in range(1, args.reps + 1) if (m, rep) not in done]

    print(f"floor probe: {len(models)} models x {args.reps} rep(s); {len(todo)} asks to run "
          f"({len(done)} already done); {'DRY RUN' if args.dry_run else 'LIVE'}")
    missing = None
    if not args.dry_run and todo:
        missing = check_names(models)

    t_start, failures = time.time(), []
    with jsonl.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe_one, m, rep, args.dry_run): (m, rep) for m, rep in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if rec.get("error") and not rec.get("raw"):
                failures.append({"model": rec["model"], "rep": rec["rep"], "error": rec["error"]})
            print(f"  [{i}/{len(todo)}] {rec['model']:<22} rep{rec['rep']} {rec['verdict']:<20} "
                  f"finish={rec['finish_reason']} {rec['latency_s']}s"
                  + (f"  ERROR {rec['error'][:80]}" if rec.get("error") else ""), flush=True)

    all_recs = load_records(jsonl)
    rows = summarize(all_recs, models, args.reps, out_dir / f"floor_probe_{ts}_summary.csv")
    audit = {"ts": ts, "dry_run": args.dry_run, "reps": args.reps, "models_requested": models,
             "models_not_in_poe_list": missing, "asks_run": len(todo), "asks_already_done": len(done),
             "failed_asks": failures, "wall_seconds": round(time.time() - t_start, 1),
             "answer_key": {"cpi_yoy_aug_2026": KEY_CPI_YOY, "core_cpi_yoy_aug_2026": KEY_CORE_YOY},
             "floor": FLOOR_YM, "prompt": PROMPT}
    (out_dir / f"audit_log_floor_probe_{ts}.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print_table(rows)
    print(f"\nwrote {jsonl.relative_to(ROOT)}\n      {(out_dir / f'floor_probe_{ts}_summary.csv').relative_to(ROOT)}")
    if failures:
        print(f"\n{len(failures)} ask(s) failed. Re-run only those with:  --resume {jsonl.name}")


if __name__ == "__main__":
    main()
