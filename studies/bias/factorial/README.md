# Memory factorial

| | |
|---|---|
| **ID** | S002 |
| **Study slug** | `factorial` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-10 |
| **Models** | Gemini-3.5-Flash-Lite |
| **Question** | Does giving the attacker and/or defender memory (stateful vs stateless) change how far the defender drifts? (2x2 factorial on abortion_policy, 5 replicates per cell) |

## Design

Four cells crossing attacker and defender statefulness (Cell 1 both stateful ... Cell 4 both stateless). Reports contain per-cell trial data; a lexical drift scorer (`shared/lexical_drift_scorer.py`) and a hand-scored gold set (`drift_score_hand`, -10 Fetal Personhood absolutism .. +10 Bodily Autonomy absolutism) were compared.

## How to run

```
python studies/bias/factorial/scripts/rspa_factorial.py
```

Scripts: rspa_factorial.py. Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

The first automated scorer's ~2.8-point 'recursion amplification' number was not in the data; hand-scoring showed the lexical scorer's Cell 4 numbers were noise (`notes/2026-09-10-followup2.md`, `-followup3.md`). Charts: `charts/hand_vs_lexical_scorer_comparison.png`, `charts/stateful_vs_stateless_handscored.png`, `charts/all_four_cells_memory_factorial.png`, `charts/cell1_vs_cell4_memory_matters.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Data helpers `shared/aggregate_replicates.py` and `shared/lexical_drift_scorer.py` read this study's `runs/` and S003's. Followed by S003 (core_replication).

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
