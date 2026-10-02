# Asymmetric attacker memory

| | |
|---|---|
| **ID** | S006 |
| **Study slug** | `asymmetric` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-14 |
| **Models** | GPT-OSS-120B-CS |
| **Question** | Does a stateless attacker vs stateful defender produce drift, compared with the Cell 1 (both stateful) results? |

## Design

Stateless attacker (fresh single-message call every round) against a stateful defender, compared side by side against `studies/bias/congruency/runs/` (Cell 1).

## How to run

```
python studies/bias/asymmetric/scripts/rspa_asymmetric_study.py
python studies/bias/asymmetric/scripts/asymmetric_analysis.py
```

Scripts: rspa_asymmetric_study.py (run), asymmetric_analysis.py (charts; reads S004's runs). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Only Cell 1 (both stateful) produced real, sustained drift (`notes/2026-09-14-asymmetric-design-results.md`). Charts in `charts/asymmetric_*.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Reads S004 (congruency) data by path; does not copy it.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
