# Wisdom of crowd btc

| | |
|---|---|
| **ID** | S012 |
| **Study slug** | `wisdom_of_crowd_btc` |
| **Area** | forecasting |
| **Status** | complete (first run, seed 20260926) |
| **Started** | 2026-09-26 |
| **Models** | GPT-5.4-Nano, GPT-5.4-Mini, Gemini-3.5-Flash-Lite, Gemini-3.5-Flash, Gemini-3.7-Flash, GPT-OSS-120B-CS, Grok-4.3, Inkling |
| **Question** | Can an aggregate of 8 cheap LLMs, each independently predicting BTC price 15 minutes ahead from anonymized recent candles, call the direction (up/down) better than chance and better than its members? |

## Design

Backtest on real history, no live waiting. 100 random 15-minute windows are drawn (seed 20260926,
outcome intervals disjoint) from about 60 days of 1-minute BTC-USD candles (Coinbase Exchange public
API). Each of 8 cheap models, queried independently and statelessly (temperature 0, one replicate),
sees the previous 120 candles as an anonymized index (last close = 100, no dates, volume relative to
window mean) and returns `{"predicted_close_index": x}` for 15 minutes later. 800 calls.

- **Correct** = predicted direction (x > 100 up, x < 100 down) matches realized direction of
  close(T+15) vs close(T). A prediction of exactly 100 or a 5-5 vote is a no-call and counts as wrong.
- **Primary crowd forecast (fixed before running):** mean of the 8 predicted index values.
  Secondary: median, trimmed mean (drop min and max), majority vote.
- **Baselines:** always-up, always-down, momentum (repeat the last 15-minute direction), and a
  predict-flat forecast for price error.
- **Analysis:** accuracy with Wilson 95% CI and exact binomial test vs 50%; paired bootstrap of crowd
  minus average model / momentum / always-up (and best model, flagged post-hoc); price MAE in index
  points; pairwise error correlation; accuracy vs crowd size.
- Full design and plan: `notes/2026-09-26-design-and-plan.md`. Shared code: none (logic is in
  `scripts/btc_lib.py`, tests in `scripts/test_btc_lib.py`).

## How to run

From `scripts/` (needs internet, `pip install -r requirements.txt`):

```
python test_btc_lib.py                          # offline unit tests
python wisdom_of_crowd_btc_study.py fetch       # ~290 requests, writes runs/candles_btcusd_1m_<date>.csv
python wisdom_of_crowd_btc_study.py run         # samples windows, queries 10 models; safe to re-run (resumes)
python wisdom_of_crowd_btc_analysis.py          # aggregates into runs/, figures into charts/
```

Offline smoke test: add `--dry-run` to `run` and to the analysis (synthetic candles, fake models;
writes to `scratch/btc_dryrun/`, never to `runs/`).

Output: `runs/` (`candles_*.csv`, `windows.json`, `trials.jsonl`, audit log, `aggregate_*`),
`charts/` (`accuracy_by_forecaster.png`, `error_correlation.png`, `crowd_size_curve.png`).
`trials.jsonl` is append-only; on re-runs the latest row per (window, model) wins.

## Findings

No detectable edge. The crowd mean called direction correctly in 48/100 windows (95% CI 38.5-57.7%,
p = 0.76); no single model was significantly above 50% (best: GPT-5.4-Mini 54%, p = 0.48). The models'
directions agree with each other only 49.5% of the time, so there is no shared signal to aggregate,
and no model or the crowd beat a predict-no-change forecast on price error. Gemini-3.5-Flash-Lite's
30% is a scoring artifact (32 no-calls scored as wrong; 44% on the calls it made). Details:
`notes/2026-09-26-first-run-results.md`; figures in `charts/`.

## Caveats

- 100 windows and 1 replicate per (window, model): about +/-10 points of margin on any accuracy.
- 8 models (planned 10; Muse-Spark-1.1 returned empty replies and Kimi-K3 was slow/flaky in the 2026-09-26 `check`, so both were dropped before any data was collected), one prompt format, one 60-day market regime; windows overlap in lookback context.
- Anonymization reduces but does not remove the chance a model recognizes a price pattern.
- Exact-100 predictions and tied votes are scored as wrong (Flash-Lite: 32 no-calls); accuracy on calls made is reported alongside. 0 missing or failed calls in the first run.
- Comparing the crowd to the best single model is post-hoc (selection bias).

## Related

Studies this builds on or should be compared with (link their folders), and any
`results/` package made from this study.

## Next steps

1. Follow-ups (same study, new runs): 300+ windows and a second seed as out-of-sample replication, a raw-price arm to measure memorization, other horizons.
2. Decide whether no-calls should be scored as wrong or excluded before any re-run (currently both are reported).
