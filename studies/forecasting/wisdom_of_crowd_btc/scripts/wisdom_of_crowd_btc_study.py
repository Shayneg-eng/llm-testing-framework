#!/usr/bin/env python3
import os
"""S012 wisdom_of_crowd_btc: run script.

    python wisdom_of_crowd_btc_study.py check                  # diagnose: price feed + 1 call per model
    python wisdom_of_crowd_btc_study.py fetch [--days 60]      # download 1-min candles (needs internet)
    python wisdom_of_crowd_btc_study.py run   [--n 100]        # sample windows + query 10 models
    python wisdom_of_crowd_btc_study.py run --dry-run          # offline: synthetic candles, fake models

Live outputs go to ../runs/. Dry-run outputs go to ROOT/scratch/btc_dryrun/ (never into runs/).
`run` is resumable: rerun it and only missing/failed (window, model) pairs are queried.
"""
import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[4]          # .../LLM Testing
_sys.path.insert(0, str(ROOT / "shared"))
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import btc_lib as B  # noqa: E402

STUDY_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = STUDY_DIR / "runs"
DRYRUN_DIR = ROOT / "scratch" / "btc_dryrun"

POE_API_KEY = os.getenv("POE_API_KEY", "")   # testing only (project policy)
POE_BASE_URL = "https://api.poe.com/v1"
# Muse-Spark-1.1 (empty replies, finish=stop) and Kimi-K3 (slow, needed retries) were dropped after
# the 2026-09-26 `check`; the study runs on these 8. See README caveats.
MODELS = ["GPT-5.4-Nano", "GPT-5.4-Mini", "Gemini-3.5-Flash-Lite", "Gemini-3.5-Flash",
          "Gemini-3.7-Flash", "GPT-OSS-120B-CS", "Grok-4.3", "Inkling"]
SEED = 20260926
MAX_TOKENS = 4000
MAX_ATTEMPTS = 3


# ---------- fetch ----------
def fetch(days):
    import requests
    end = int(time.time()) // 60 * 60
    start = end - days * 86400
    candles, cur = {}, end
    s = requests.Session()
    total = -(-(end - start) // (300 * 60))
    print(f"fetching ~{days} days of 1-min candles in {total} requests (about 1-3 minutes)...", flush=True)
    chunk = 0
    while cur > start:
        lo = max(start, cur - 300 * 60)
        iso = lambda x: datetime.fromtimestamp(x, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for attempt in range(5):
            r = s.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                      params={"granularity": 60, "start": iso(lo), "end": iso(cur)}, timeout=30)
            if r.status_code == 200:
                break
            time.sleep(1.5 * (attempt + 1))
        else:
            sys.exit(f"fetch failed: HTTP {r.status_code} {r.text[:200]}")
        candles.update(B.coinbase_rows_to_candles(r.json()))
        cur = lo
        chunk += 1
        if chunk % 10 == 0 or chunk == total:
            print(f"  request {chunk}/{total}, {len(candles)} candles so far", flush=True)
        time.sleep(0.15)
    RUNS_DIR.mkdir(exist_ok=True)
    out = RUNS_DIR / f"candles_btcusd_1m_{datetime.now(timezone.utc):%Y-%m-%d}.csv"
    B.save_candles(out, candles)
    print(f"saved {len(candles)} candles ({days} days requested) -> {out.relative_to(ROOT)}")


# ---------- dry-run stand-ins ----------
def synthetic_candles(days=20, seed=42):
    rng = random.Random(seed)
    t0, price, out = 1_790_000_000 // 60 * 60, 60_000.0, {}
    for i in range(days * 1440):
        o = price
        price *= 1 + rng.gauss(0, 0.0004)
        out[t0 + i * 60] = (o, max(o, price) * 1.0001, min(o, price) * 0.9999, price, 1 + rng.random())
    return out


def fake_model_call(model, window_id, user_prompt):
    """Deterministic fake: weak momentum signal + model-specific noise. Occasionally junk."""
    rng = random.Random(f"{model}|{window_id}")
    rows = [l.split(",") for l in user_prompt.splitlines() if l[:1] in "-0123456789" and l.count(",") == 5]
    closes = [float(r[4]) for r in rows]
    mom = closes[-1] - closes[-16]
    if rng.random() < 0.03:
        return "I cannot predict markets.", "stop"
    return json.dumps({"predicted_close_index": round(100 + 0.2 * mom + rng.gauss(0, 0.05), 3)}), "stop"


# ---------- live model call ----------
_client = None


def live_model_call(model, system, user):
    global _client
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=POE_API_KEY, base_url=POE_BASE_URL, timeout=120)
    kwargs = dict(model=model, max_tokens=MAX_TOKENS, temperature=0,
                  messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    try:
        resp = _client.chat.completions.create(**kwargs)
    except Exception as e:
        if "temperature" in str(e).lower():          # some reasoning models reject temperature
            kwargs.pop("temperature")
            resp = _client.chat.completions.create(**kwargs)
        else:
            raise
    ch = resp.choices[0]
    return ch.message.content, ch.finish_reason


def query(model, window, candles, dry_run):
    system, user = B.build_prompt(candles, window["t"])
    rec = {"window_id": window["window_id"], "model": model, "pred": None, "raw": None,
           "finish_reason": None, "attempts": 0, "error": None, "latency_s": None}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        rec["attempts"] = attempt
        t0 = time.time()
        try:
            if dry_run:
                text, fr = fake_model_call(model, window["window_id"] + str(attempt), user)
            else:
                text, fr = live_model_call(model, system, user)
            rec.update(raw=(text or "")[:2000], finish_reason=fr, error=None)
            rec["latency_s"] = round(time.time() - t0, 2)
            pred = B.parse_prediction(text)
            if pred is not None:
                rec["pred"] = pred
                return rec
            rec["error"] = "parse_failure"
        except Exception as e:  # noqa
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        time.sleep(0 if dry_run else 2 * attempt)
    return rec


# ---------- run ----------
def run(args):
    out_dir = DRYRUN_DIR if args.dry_run else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        candles = synthetic_candles()
    else:
        path = Path(args.candles) if args.candles else max(RUNS_DIR.glob("candles_btcusd_1m_*.csv"), default=None)
        if not path:
            sys.exit("no candle file in runs/. Run `fetch` first.")
        candles = B.load_candles(path)
        print(f"candles: {len(candles)} from {path.name}")

    wpath = out_dir / "windows.json"
    if wpath.exists():
        wdata = json.loads(wpath.read_text())
        if wdata["seed"] != args.seed or wdata["n"] != args.n:
            sys.exit(f"{wpath.name} exists with different seed/n; move it aside to start a new sample")
        windows, skipped = wdata["windows"], wdata["skipped_ties"]
    else:
        windows, skipped = B.sample_windows(candles, args.n, args.seed)
        wpath.write_text(json.dumps({"seed": args.seed, "n": args.n, "skipped_ties": skipped,
                                     "lookback": B.LOOKBACK, "horizon_min": B.HORIZON,
                                     "windows": windows}, indent=1))
    wins = {w["window_id"]: w for w in windows}

    tpath = out_dir / "trials.jsonl"
    done = set()
    if tpath.exists():
        for line in tpath.read_text().splitlines():
            r = json.loads(line)
            if r["pred"] is not None:
                done.add((r["window_id"], r["model"]))
    models = args.models or MODELS
    todo = [(m, w) for w in windows for m in models if (w["window_id"], m) not in done]
    print(f"{len(windows)} windows x {len(models)} models; {len(done)} done, {len(todo)} to query", flush=True)
    if not todo:
        print("nothing to do: every (window, model) pair already has a valid prediction in trials.jsonl")

    lock, ok, fail, errs = threading.Lock(), 0, 0, {}
    started = time.time()
    with open(tpath, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(query, m, w, candles, args.dry_run) for m, w in todo]
        for i, fu in enumerate(as_completed(futs), 1):
            rec = fu.result()
            with lock:
                f.write(json.dumps(rec) + "\n"); f.flush()
            ok += rec["pred"] is not None
            fail += rec["pred"] is None
            if rec["pred"] is None:
                errs.setdefault(rec["model"], []).append(rec["error"] or "?")
            if i % 50 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} ok={ok} failed={fail}")

    if errs:
        print("\nFAILURES by model (count, first error):")
        for m, e in sorted(errs.items()):
            print(f"  {m}: {len(e)} failed - {e[0][:200]}")
        if len(todo) >= 10 and fail == len(todo):
            print("ALL calls failed. Run `check` to diagnose the API key / model names / network.")
    audit = {"finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "dry_run": args.dry_run, "seed": args.seed, "n_windows": len(windows),
             "skipped_ties": skipped, "models": models, "queried_this_invocation": len(todo),
             "ok": ok, "failed_after_retries": fail, "max_attempts": MAX_ATTEMPTS,
             "temperature": 0, "max_tokens": MAX_TOKENS, "seconds": round(time.time() - started, 1)}
    with open(out_dir / "audit_log_wisdom_of_crowd_btc.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(audit) + "\n")
    print("audit:", audit)
    print(f"next: python wisdom_of_crowd_btc_analysis.py{' --dry-run' if args.dry_run else ''}")


def check(args):
    """Diagnose setup: price feed + one call per model. Writes nothing."""
    print("1) price feed (Coinbase)...", flush=True)
    if args.dry_run:
        candles = synthetic_candles(days=1)
        print("   dry-run: synthetic candles")
    else:
        import requests
        try:
            r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                             params={"granularity": 60}, timeout=20)
            print(f"   HTTP {r.status_code}, {len(r.json()) if r.ok else r.text[:150]} candles")
        except Exception as e:  # noqa
            print(f"   FAILED: {type(e).__name__}: {str(e)[:200]}")
        cf = max(RUNS_DIR.glob("candles_btcusd_1m_*.csv"), default=None)
        if not cf:
            print("   no candle file in runs/ yet (run `fetch`); using synthetic candles for the model test")
            candles = synthetic_candles(days=1)
        else:
            candles = B.load_candles(cf)
            print(f"   candle file: {cf.name}, {len(candles)} candles")
    ts = [t for t in sorted(candles) if B.window_is_complete(candles, t)]
    if not ts:
        print("   no complete window available"); return
    w = {"window_id": "check", "t": ts[len(ts) // 2]}
    print(f"2) one call per model ({len(args.models or MODELS)} models)...", flush=True)
    for m in args.models or MODELS:
        rec = query(m, w, candles, args.dry_run)
        status = f"OK pred={rec['pred']}" if rec["pred"] is not None else f"FAIL {rec['error']} finish={rec['finish_reason']} raw={str(rec['raw'])[:80]!r}"
        print(f"   {m:24s} {status} ({rec['latency_s']}s, {rec['attempts']} attempt(s))", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--days", type=int, default=60)
    c = sub.add_parser("check"); c.add_argument("--models", nargs="+"); c.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--n", type=int, default=100)
    r.add_argument("--seed", type=int, default=SEED)
    r.add_argument("--workers", type=int, default=10)
    r.add_argument("--candles")
    r.add_argument("--models", nargs="+")
    r.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    {"fetch": lambda: fetch(a.days), "run": lambda: run(a), "check": lambda: check(a)}[a.cmd]()


if __name__ == "__main__":
    main()
