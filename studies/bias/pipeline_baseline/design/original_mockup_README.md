> Moved here from the old top-level README on 2026-09-25 (see docs/CHANGELOG.md). Paths below are relative to this file.

# RSPA mockup v0

First runnable mockup of the S.H.A.Y.N.E. Recursive Self-Persuasion Audit.
No embeddings, no automated drift scoring -- it runs the two symmetric
adversarial trials per model and writes transcripts for manual review.

## Setup

```
pip install -r ../../../../requirements.txt
python ../scripts/rspa_pipeline.py
```

Output lands in `../runs/`:
- `rspa_report_<topic>_<seed>_<model>.json` -- structured transcript
  (matches the schema in the `rspa-bias-audit` skill, minus the
  drift-scoring section)
- `transcript_<topic>_<seed>_<model>.md` -- the same content formatted for
  quick reading

## Topics and seeds (`seeds.py`)

Four topics are pre-loaded in `seeds.py`, each with genuinely opposed
DIRECTION_A/DIRECTION_B poles and three claim variants (Triangulated Seed
Protocol): `"0"` (neutral), `"+a"` (tilt toward A), `"+b"` (tilt toward B).

- `encryption_backdoors` -- State Security vs. Universal Liberty
- `immigration_enforcement` -- Sovereign Border Control vs. Freedom of Movement
- `minimum_wage` -- Free Market vs. Labor Protection
- `firearm_regulation` -- Individual Rights vs. Collective Safety

Pick which one runs by setting `TOPIC_KEY` and `SEED_KEY` at the top of
`rspa_pipeline.py`. This mockup runs one topic/seed pair per invocation
(cheap and easy to eyeball); run it three times with `SEED_KEY` set to
`"0"`, `"+a"`, `"+b"` in turn to get the full triangulated picture for one
topic. Add a new topic by adding another entry to the `TOPICS` dict in
`seeds.py` -- keep the two directions genuine opposites on the same axis,
not a strawman on one side and a moderate position on the other.

## What's in this mockup

- **Models:** `GPT-5.4-Nano`, `Gemini-3.5-Flash-Lite` (cheap tier, per your
  pick). Add/remove models in the `MODELS` list in `rspa_pipeline.py`.
- **Same model plays both agents** (Agent A defender, Agent B attacker),
  per the framework's bifurcated bias taxonomy -- an attack deficit or an
  asymmetric collapse under the model's own attacks is the signal, not
  something to normalize away by mixing models.
- **Agent A is genuinely stateful**: full message history is replayed to
  the model every turn.
- **Agent B is genuinely stateless**: every critique is a fresh API call
  with only the current claim + reasoning, no prior turns.
- **ROUNDS = 5** (framework default is 15) -- kept small so a first mockup
  run is cheap. Bump it once you like what you see.
- Heuristic flags per turn: `cap_exceeded` (word count check),
  `stagnation_flag` (>=90% text-similarity to the previous claim),
  `refusal_flag` (Agent A stopped emitting the REASONING/CURRENT CLAIM
  block -- trial stops early when this fires).

## What's intentionally left out (for now)

- No embedding-based drift vectors.
- No automated LLM-judge scoring pass (skill step 3). Read the
  `transcript_*.md` files yourself for now; the judge step is easy to
  bolt on once the trial mechanics look right.
- No automated loop across all topics x seeds x models -- one topic/seed
  pair runs per invocation, by design, so a run stays cheap while you're
  still validating the mechanics.
- Trials run sequentially, not in parallel.

## One thing to know about where this runs

This cloud session's network policy blocks `api.poe.com` (403 at the
egress gateway) -- confirmed when testing this script. Run
`rspa_pipeline.py` on your own machine, not from this container; a normal
Python environment on your side should reach Poe's API without issue.

## Editing a run

Everything you'd change between runs is at the top of `rspa_pipeline.py`:
`MODELS`, `TOPIC_KEY`, `SEED_KEY`, `ROUNDS`, `CLAIM_CAP`. `TOPIC`,
`NEUTRAL_CLAIM`, `DIRECTION_A`/`DIRECTION_B` are now derived automatically
from `seeds.py` -- don't hand-edit those directly, edit `seeds.py` instead.

The Poe API key is hardcoded in the script per the project's testing
instructions -- rotate it before this file goes anywhere outside your own
machine.
