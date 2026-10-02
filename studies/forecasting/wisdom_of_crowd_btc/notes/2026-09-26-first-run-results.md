# S012 wisdom_of_crowd_btc: first run results (2026-09-26)

**Bottom line:** no evidence that the crowd, or any single model, predicts 15-minute BTC direction
better than a coin flip. The crowd mean got 48/100 (95% CI 38.5% to 57.7%, p = 0.76 vs 50%).
Averaging did not help because the models share no directional signal.

## Setup and caveats (read first)

- 100 random 15-minute windows (seed 20260926, disjoint outcome intervals) from 86,399 one-minute
  BTC-USD candles, 2026-07-28 to 2026-09-26 (`studies/forecasting/wisdom_of_crowd_btc/runs/candles_btcusd_1m_2026-09-26.csv`).
- **8 models**, 1 replicate per (window, model), temperature 0: GPT-5.4-Nano, GPT-5.4-Mini,
  Gemini-3.5-Flash-Lite, Gemini-3.5-Flash, Gemini-3.7-Flash, GPT-OSS-120B-CS, Grok-4.3, Inkling.
  The planned 10 became 8: Muse-Spark-1.1 (empty replies) and Kimi-K3 (slow/flaky) were dropped
  before any data was collected.
- 800 of 800 calls returned a valid prediction (0 missing, 0 halted). No rater or judge; scoring is
  mechanical against the realized close.
- Base rate: 49 of 100 windows went up; no ties.
- With n = 100, any accuracy has roughly +/-10 points of margin. This run can only detect a large
  edge; a real edge of a few points would be invisible.
- Anonymized prompts (no dates, prices rescaled) reduce but do not eliminate memorization risk.
  One 60-day market regime.
- **Scoring convention:** a prediction of exactly 100 (or a tied vote) is a no-call and counts as
  wrong. This was fixed before the run, but it materially affects one model (see below). Both
  versions are now reported.

## Results

| Forecaster | Accuracy | 95% CI | p vs 50% |
|---|---|---|---|
| Crowd: mean (primary) | 48% | 38.5-57.7% | 0.76 |
| Crowd: median | 46% | 36.6-55.7% | 0.48 |
| Crowd: trimmed mean | 49% | 39.4-58.7% | 0.92 |
| Crowd: majority vote | 44% | 34.7-53.8% | 0.27 |
| Baseline: momentum | 49% | | |
| Baseline: always up / always down | 49% / 51% | | |

| Model | Accuracy (no-call = wrong) | No-calls | Accuracy on calls made | p (on calls) |
|---|---|---|---|---|
| GPT-5.4-Mini | 54% | 0 | 54.0% | 0.48 |
| GPT-5.4-Nano | 50% | 0 | 50.0% | 1.00 |
| Inkling | 50% | 4 | 52.1% | 0.76 |
| Gemini-3.5-Flash | 46% | 0 | 46.0% | 0.48 |
| GPT-OSS-120B-CS | 45% | 4 | 46.9% | 0.61 |
| Gemini-3.7-Flash | 45% | 0 | 45.0% | 0.37 |
| Grok-4.3 | 44% | 8 | 47.8% | 0.76 |
| Gemini-3.5-Flash-Lite | 30% | 32 | 44.1% | 0.40 |

Charts: `studies/forecasting/wisdom_of_crowd_btc/charts/accuracy_by_forecaster.png`,
`error_correlation.png`, `crowd_size_curve.png`. Data: `runs/aggregate_results.json`,
`aggregate_by_model.csv`, `aggregate_per_window.csv`.

## Findings

1. **Flash-Lite's 30% is a scoring artifact, not an anti-signal.** It predicted exactly 100.0 in
   32 of 100 windows, which the convention scores as wrong. On the 68 calls it made it was right
   30 times (44%, p = 0.40). It also does not drag the crowd down: the crowd mean is 48/100 both
   with and without it (post-hoc check). Flipping its calls (also post-hoc, exploratory) gives 50/100.
2. **The models share no directional signal.** Two models agree on direction 49.5% of the time,
   about what independent coin flips with these up-rates would give (roughly 50-52%). A crowd can
   only beat its members when members have partially independent *and* better-than-chance views;
   here there is nothing to aggregate. Accuracy versus crowd size is flat (45.5% at 1 model to
   about 48-49% at 5-8).
3. **No model beat "predict no change" on price.** The flat forecast (index 100) has a mean absolute
   error of 0.1257 index points; every model (0.1345 to 0.1791) and the crowd mean (0.1348) is worse.
4. **Strong directional habits unrelated to outcomes.** Up-prediction rates range from 21% (Inkling)
   to 77% (Gemini-3.5-Flash) against a 49% base rate. These are model biases, not signal.
5. **The market itself showed no simple pattern.** Momentum (repeat the last 15 minutes) scored 49%,
   and the outcome reversed the prior 15-minute direction in 51 of 100 windows.
6. Error correlation between models is high (mean 0.78), but this mostly reflects the shared
   realized price move in the error term, not shared model views; finding 2 is the better diversity measure.
7. Crowd versus average model: +2.5 points (95% bootstrap CI -4.5 to +9.5); versus momentum -1.0
   (-11 to +9). Neither is distinguishable from zero. The best single model (GPT-5.4-Mini, 54%) is
   picked after seeing the data, so its edge should not be trusted; it is within noise of 50%.

## Not concluded

This does not show LLMs cannot forecast Bitcoin, only that these 8 cheap models, given 2 hours of
anonymized 1-minute candles, showed no detectable edge at n = 100. Useful follow-ups (same study,
new runs): more windows (300+) to tighten intervals, a second seed as out-of-sample replication
before any post-hoc idea (such as fixing Flash-Lite's no-calls) is trusted, a raw-price arm to test
memorization, and longer horizons.
