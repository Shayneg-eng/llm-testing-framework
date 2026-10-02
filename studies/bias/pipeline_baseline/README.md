# Pipeline baseline (RSPA mockup v0)

| | |
|---|---|
| **ID** | S001 |
| **Study slug** | `pipeline_baseline` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-10 |
| **Models** | GPT-5.4-Nano, Gemini-3.5-Flash-Lite |
| **Question** | Does the two-agent Recursive Self-Persuasion Audit mockup run end to end on a handful of political topics (encryption backdoors, immigration, minimum wage, firearms, abortion)? |

## Design

One topic/seed pair per invocation. The same model plays a stateful Defender (Agent A, full history replayed) and a stateless Attacker (Agent B, fresh call each turn), 5 rounds. No embeddings and no automated drift scoring: transcripts are read by hand. Seeds and topics come from `shared/seeds.py` (Triangulated Seed Protocol: `0` neutral, `+a`, `+b`). The original mockup README is preserved in `design/original_mockup_README.md`.

## How to run

```
python studies/bias/pipeline_baseline/scripts/rspa_pipeline.py
```

Scripts: rspa_pipeline.py (run script; edit `MODELS`, `TOPIC_KEY`, `SEED_KEY`, `ROUNDS` at the top). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Mechanics validated; this study is the harness ancestor of everything else. The direction it led to is described in `cross_study_notes/2026-09-10-research-direction.md`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Led directly to S002 (factorial).

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
