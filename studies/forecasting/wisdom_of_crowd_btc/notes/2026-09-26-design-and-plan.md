# S012 wisdom_of_crowd_btc: design and implementation plan

Approved 2026-09-26. Question: can the aggregate of 10 cheap LLMs, each independently
predicting BTC price 15 minutes ahead, call the direction (up/down) better than chance and
better than its members?

> **Amendment 2026-09-26 (before any data):** the lineup is 8 models, not 10. Muse-Spark-1.1 returned
> empty replies (finish=stop, 3/3 attempts) and Kimi-K3 was slow and needed retries in `check`; both
> were dropped at the user's request. Everything below that says 10 models / 1,000 calls / 5-5 votes
> now means 8 models / 800 calls / 4-4 votes.

## Design (approved)

- **Data:** ~60 days of 1-minute BTC-USD candles from Coinbase Exchange public API
  (`/products/BTC-USD/candles`, granularity 60, 300 candles per request), cached in `runs/`.
- **Windows:** 100 random decision minutes T, seed 20260926, outcome windows [T, T+15] pairwise
  disjoint, each with a complete 120-minute lookback and no missing minutes. Start price =
  close of candle T; end price = close of candle T+15. Ties (end == start) are excluded and logged.
- **Prompt (identical for all models):** the 120 lookback candles as an index table
  (last close = 100, no dates, volume relative to window mean). Model returns JSON
  `{"predicted_close_index": <number>}`. Direction = up if > 100, down if < 100 (== 100 is "no call").
- **Models (10, Poe names):** GPT-5.4-Nano, GPT-5.4-Mini, Gemini-3.5-Flash-Lite,
  Gemini-3.5-Flash, Gemini-3.7-Flash, GPT-OSS-120B-CS, Kimi-K3, Grok-4.3, Muse-Spark-1.1, Inkling.
  Stateless, temperature 0, one replicate per (window, model). 1,000 calls.
- **Aggregation (primary fixed before running):** mean of the 10 predicted index values.
  Secondary: median, trimmed mean (drop min and max), majority vote of directions (5-5 = no call).
- **Scoring:** direction accuracy with Wilson 95% CI and exact binomial p vs 50%; baselines
  always-up and momentum (sign of last-15-minute return); paired bootstrap of crowd minus median
  model and crowd minus momentum; price error (MAE of index points vs actual end index, versus a
  predict-flat baseline); pairwise error correlation; crowd accuracy as a function of crowd size k.
- **Leakage guard:** windows drawn from the most recent ~60 days, dates stripped, prices rescaled.

## Environment note

On 2026-09-26 neither the cloud workspace nor the local Cowork shell could reach
`api.poe.com` or any BTC price API (org egress policy). The scripts are therefore tested
offline (`--dry-run`: synthetic candles, fake models) and the live run is executed on the
user's own machine.

## Files

| File | Responsibility |
|---|---|
| `scripts/btc_lib.py` | Pure logic: candle cache/IO, window sampling, prompt building, response parsing, aggregation |
| `scripts/test_btc_lib.py` | Offline unit tests for btc_lib (plain asserts; `python test_btc_lib.py`) |
| `scripts/wisdom_of_crowd_btc_study.py` | Run script: `fetch`, then `run` (parallel, resumable); `--dry-run` for offline |
| `scripts/wisdom_of_crowd_btc_analysis.py` | Reads `runs/`, writes aggregate files to `runs/` and figures to `charts/` |

## Plan

1. btc_lib + tests (TDD): sampling determinism and disjointness, gap rejection, anonymization
   arithmetic, parser edge cases, aggregation and vote ties.
2. Study script: fetch with cache; run with resume, retries, parse-failure logging, audit log.
3. Analysis script: metrics above, dry-run end to end on synthetic data.
4. User runs `fetch` then `run` then analysis on their machine; results written up in `notes/`.
