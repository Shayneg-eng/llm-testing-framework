# Group trope bias

| | |
|---|---|
| **ID** | S010 |
| **Study slug** | `group_trope_bias` |
| **Area** | bias |
| **Status** | scoring |
| **Started** | 2026-09-19 |
| **Models** | GPT-OSS-120B-CS (pilot); multi-model run adds more models (see write-ups) |
| **Question** | With byte-identical scenarios, does the named religion (Jewish / Christian / Muslim) change how far the model is pushed toward escalation or reconciliation under pressure? |

## Design

3 tropes (greed_theft, control_nepotism, dual_loyalty) x 3 religions x 2 directions (A escalation-first, B reconciliation-first) = 18 conditions, Cell 1. Pilot: GPT-OSS-120B-CS, n=2. Multi-model follow-up: several models, n=3, hand-scored on -10 (reconciliation absolutism) .. +10 (escalation absolutism). `--calibrate` mode of the run script estimates cost before a full run.

## How to run

```
python studies/bias/group_trope_bias/scripts/rspa_group_trope_bias_study.py --calibrate
python studies/bias/group_trope_bias/scripts/rspa_group_trope_bias_study.py
python studies/bias/group_trope_bias/scripts/group_trope_bias_multimodel_analysis.py
```

Scripts: rspa_group_trope_bias_study.py (run), group_trope_bias_analysis.py (single-model charts), group_trope_bias_multimodel_analysis.py (multi-model charts). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Pilot: round-1 baselines do not differ by religion; two trope-specific asymmetries (greed_theft / Jewish / escalation, dual_loyalty / Jewish / reconciliation), no blanket single-religion pattern. Multi-model: Claude Sonnet 4.6 was the only model with a real per-religion split; packaged in `results/claude-sonnet-4.6-religion-split/`. Design and results write-ups are in the Project store (see `INDEX.md`).

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Israel-specific dual-loyalty follow-up (Jewish vs no-religion control) is planned as a separate study. Uses S004's Cell 1 harness.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
