# Starting position

| | |
|---|---|
| **ID** | S005 |
| **Study slug** | `starting_position` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-12 |
| **Models** | GPT-OSS-120B-CS |
| **Question** | How does drift depend on where the initial claim sits on a graded scale of starting positions? |

## Design

Nine abortion_policy seeds (`+++a`, `++a`, `+a`, `0`, `0-legal`, `0-medical`, `+b`, `++b`, `+++b`) x 2 attack directions x 5 replicates = 90 trials, Cell 1.

## How to run

```
python studies/bias/starting_position/scripts/rspa_starting_position_study.py
python studies/bias/starting_position/scripts/starting_position_analysis.py
```

Scripts: rspa_starting_position_study.py (run), starting_position_analysis.py (charts). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Initial null (`notes/2026-09-12-starting-position-null.md`), then a strong outlier on the `0-medical` neutral seed (about -6.8) in `notes/2026-09-15-starting-position-results.md`. Charts: `charts/starting_position_grid.png`, `charts/starting_position_intensity.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

The 0-medical outlier motivated S007 (argument_type).

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
