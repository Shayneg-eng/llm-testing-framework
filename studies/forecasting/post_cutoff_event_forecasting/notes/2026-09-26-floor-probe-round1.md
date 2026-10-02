# S013 floor probe, round 1 (2026-09-26)

**Bottom line:** 18 of the 32 candidate models were actually queried. None knew the September 2026
CPI figures, so nothing so far suggests any queryable model's cutoff is at or past the provisional
floor (2026-09-01). The other 14 candidates are not available through the Poe API at all, so they
cannot take part in this study. The probe is one-directional: a correct answer would prove
knowledge, "I don't know" only suggests the cutoff is earlier.

## Setup and caveats (read first)

- Script `scripts/floor_probe.py`, run 2026-09-26; raw data `runs/floor_probe_20260926T195150Z.jsonl`,
  summary `runs/floor_probe_20260926T195150Z_summary.csv`, audit log alongside.
- 32 models requested, **1 ask per model** (`--reps 1`), no tools, no web search, no judge
  (regex-parsed, raw replies kept). Temperature 0 where the model accepts it.
- Probe facts: US CPI 12-month change for August 2026 = 3.4% and core = 2.4% (BLS release,
  2026-09-11). Only two facts, so this tests the last few weeks only; it says nothing about
  whether cutoffs lie in, say, April versus August 2026.
- Self-reported cutoffs are unreliable (e.g. Claude-Opus-4.8 said early 2025 while a third-party
  tracker lists 2026-01); they are recorded, not trusted.

## Models queried (18): all answered "I don't know" on both CPI questions

| Model | Self-reported cutoff | CPI Aug 2026 | Core CPI Aug 2026 |
|---|---|---|---|
| GPT-5.4-Nano | no answer | don't know | don't know |
| Grok-4.7 | no answer | don't know | don't know |
| Kimi-K3 | no answer | don't know | don't know |
| Gemini-3.6-Flash | 2026-03 | don't know | don't know |
| Gemini-3.7-Flash | 2026-03 | don't know | don't know |
| Gemini-3.8-Flash | 2026-03 | don't know | don't know |
| Inkling | 2026-01 | don't know | don't know |
| Muse-Spark-1.1 | 2026-01 | don't know | don't know |
| Claude-Opus-4.8 | 2025-03 | don't know | don't know |
| Gemini-3.5-Flash | 2025-01 | don't know | don't know |
| Gemini-Omni-1.1-Flash | 2025-01 | don't know | don't know |
| Gemini-3.5-Flash-Lite | 2024-12 | don't know | don't know |
| GPT-5.4 | 2024-06 | don't know | don't know |
| GPT-5.4-Mini | 2024-06 | don't know | don't know |
| GPT-OSS-120B-CS | 2024-06 | don't know | don't know |
| Grok-4.3 | 2023-12 | don't know | don't know |
| Grok-4.5 | 2023-10 | don't know | don't know |
| Grok-4.6 | 2023-10 | don't know | don't know |

## Not queryable (14): no such model on Poe's live API (`/v1/models`, 343 ids)

Claude-Fable-5, Claude-Fable-5.1, Claude-Opus-5, Claude-Opus-5.5, Claude-Sonnet-5, GPT-5.5, GPT-5.5-Pro, GPT-5.6-Luna, GPT-5.6-Sol, GPT-5.6-Terra, GPT-6-Astra, GPT-6-Luna, GPT-6-Sol, Gemini-Omni-Flash.
Thirteen returned HTTP 404 "model not found"; Gemini-Omni-Flash returned HTTP 500 three times and
is not in the live list either (only `gemini-omni-1.1-flash` is). The Project doc "Poe Model
Names" lists UI names, and several of those (every Claude 5.x, every GPT-5.5+/GPT-6, GPT-6-Astra)
are not served by the API; the live id list is in `runs/poe_models_*.json`. Muse-Spark-1.1 is
listed as `muse-spark-1-1` but the dotted name worked.

## Implications for the design

1. The study can only include models reachable through Poe. Every model above the newest queryable
   ones (Claude 5.x, GPT-5.5+, GPT-6) is out of scope unless another route is added.
2. The newest self-reported cutoff among queryable models is 2026-03 (Gemini-3.6/3.7/3.8-Flash).
   If that holds, the floor could be much earlier than 2026-09-01 and the ~25-day window (the
   main constraint on getting 250 diverse items) could grow to several months. That needs an
   empirical check with a ladder of dated facts, not self-reports (proposed next step, not run).

## Next steps

1. Decide whether to run a graded ladder probe (monthly US CPI prints, Feb-Aug 2026) to bracket each
   model's real knowledge frontier and move the floor.
2. Clean up `MODELS` in `scripts/floor_probe.py` to the 18 queryable names once that is decided.
