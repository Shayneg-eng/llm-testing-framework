# Post cutoff event forecasting

| | |
|---|---|
| **ID** | S013 |
| **Study slug** | `post_cutoff_event_forecasting` |
| **Area** | forecasting |
| **Status** | running (238-question set built; briefs, leak check, audit and model runs pending) |
| **Started** | 2026-09-26 |
| **Models** | (tbd: chosen after the floor-verification probe; roster in Project doc "Poe model names") |
| **Question** | Which LLMs forecast real-world binary events best (per category: economics/finance, sports, politics/policy/world, culture/science/tech) when every outcome resolved after the models' knowledge cutoffs and each item is given a leak-checked pre-event brief? |

## Design

250 binary real-world forecasting items across 4 categories (economics/finance 65, sports 65,
politics/policy/world 60, culture/science/tech 60), sourced mainly from settled Kalshi markets.
Every outcome resolved on or after a global floor (2026-09-01, confirmed) so it cannot be in
any tested model's training data. Each item gives the model a question, resolution criteria and
a leak-checked pre-event brief (as-of t0, at least 24h before resolution); the model returns a
probability. Scoring: Brier, log loss, calibration, per category and overall, against baselines
(Kalshi price at t0, base rate, 50%). 1 replicate per (item, model), temperature 0. Full design:
`notes/2026-09-26-dataset-design.md`. Builds on no shared code yet.

## How to run

Step 1, floor-verification probe (the only runnable script so far). Asks every candidate model its
own cutoff plus two facts first published in September 2026 (US CPI and core CPI for August 2026:
3.4% and 2.4%, BLS release 2026-09-11) and classifies each model's reply:

```
python studies/forecasting/post_cutoff_event_forecasting/scripts/floor_probe.py            # all 32 models, 1 ask each
python studies/forecasting/post_cutoff_event_forecasting/scripts/floor_probe.py --reps 3   # guard against lucky guesses
python studies/forecasting/post_cutoff_event_forecasting/scripts/floor_probe.py --resume studies/forecasting/post_cutoff_event_forecasting/runs/floor_probe_<ts>.jsonl   # re-ask only failed pairs
python studies/forecasting/post_cutoff_event_forecasting/scripts/floor_probe.py --dry-run  # offline test, writes to scratch/
```

Needs `openai` installed. Output in `runs/`: `floor_probe_<ts>.jsonl` (raw replies + parsed fields),
`floor_probe_<ts>_summary.csv` (one row per model with a verdict), `audit_log_floor_probe_<ts>.json`.
Verdicts: `PAST_FLOOR` (both facts right: cutoff likely at or after 2026-09, flag or exclude),
`AMBIGUOUS` (one right: re-run with `--reps 3`), `STALE_OR_GUESS`, `BEFORE_FLOOR_LIKELY` (said "I
don't know": keep), `UNPARSED`, `NO_RESPONSE`. Read the raw replies before deciding; the parser is
regex-based. Run live once (2026-09-26, 1 ask per model): see `notes/2026-09-26-floor-probe-round1.md`. `--list-models` saves Poe's live model ids to `runs/`.

Later steps (Kalshi pull, briefs, leak check, model run, analysis) are not written yet; the
scaffolded `post_cutoff_event_forecasting_study.py` and `_analysis.py` are placeholders.

## Question set (2026-09-26)

`runs/items_pre_brief.jsonl`: 238 curated binary questions (econ/finance 65, sports 65, politics/world 48 of 60, culture/science/tech 60), no briefs yet.
Build details and caveats: `notes/2026-09-26-question-set-build.md`. Rebuild: `python scripts/curate_kalshi_rows.py` then `python scripts/build_items.py finalize`.

## Findings

No forecasting results yet. Floor probe round 1 (2026-09-26): 18 of 32 candidate models are queryable
through Poe and none knew the September 2026 CPI figures; 14 candidates (all Claude 5.x, GPT-5.5+, GPT-6-*,
Gemini-Omni-Flash) are not on the API. See `notes/2026-09-26-floor-probe-round1.md`.
Design: `notes/2026-09-26-dataset-design.md`.

## Caveats

Planned caveats to report with any result: 1 replicate per cell; no judge (mechanical scoring);
about 60 items per category gives roughly +/-10-12 point intervals; about 25-day window; cutoffs
of several models unpublished (floor probe required); single brief-writer and checker model.

## Related

`studies/forecasting/wisdom_of_crowd_btc` (S012): same area, different data type and design.

## Next steps

1. Write the implementation plan, then run the floor-verification probe.
