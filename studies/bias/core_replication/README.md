# Core replication (Cell 1 vs Cell 4)

| | |
|---|---|
| **ID** | S003 |
| **Study slug** | `core_replication` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-11 |
| **Models** | Gemini-3.5-Flash-Lite |
| **Question** | Does the 'memory matters' contrast (Cell 1 both stateful vs Cell 4 both stateless) replicate across the three Triangulated Seed Protocol seeds? |

## Design

Cell 1 vs Cell 4 on abortion_policy, seeds `0`, `+a`, `+b`, several replicates each; hand-scored (`fill_core_hand_scores.py` writes the hand scores into the reports).

## How to run

```
python studies/bias/core_replication/scripts/rspa_core_replication.py
python studies/bias/core_replication/scripts/analyze_core_replication.py
```

Scripts: rspa_core_replication.py (run), fill_core_hand_scores.py (hand-score entry), analyze_core_replication.py (charts). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Memory matters replicates on all three seeds; the size and direction of the asymmetry depend on the seed (`notes/2026-09-11-core-replication.md`, `notes/2026-09-11-seed-dependent-asymmetry.md`). Charts in `charts/core_replication_*.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Split out of the old mixed `runs_factorial/` on 2026-09-15. Follows S002.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
