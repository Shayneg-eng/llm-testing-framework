# Congruency

| | |
|---|---|
| **ID** | S004 |
| **Study slug** | `congruency` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-11 |
| **Models** | GPT-OSS-120B-CS |
| **Question** | Does drift depend on whether the attack direction is congruent or incongruent with the starting claim's lean? (Cell 1, abortion_policy) |

## Design

Both agents fully stateful (Cell 1). Seeds `0`, `+a`, `+b` attacked from Direction A and B; congruency labelled from each seed's textual lean. Its Cell 1 harness is reused byte-for-byte by later studies.

## How to run

```
python studies/bias/congruency/scripts/rspa_congruency_study.py
python studies/bias/congruency/scripts/congruency_analysis.py
```

Scripts: rspa_congruency_study.py (run), congruency_analysis.py (charts). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

See `notes/2026-09-11-congruency-pivot.md` and `notes/2026-09-11-congruency-results.md`. Charts in `charts/congruency_*.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

S006 (asymmetric) reads this study's `runs/` as its Cell 1 comparison. Note: `congruency_analysis.py` was not patched for refusal-truncation visibility in the 2026-09-15 code audit (see `cross_study_notes/`, Project: `claude/2026-09-15-code-audit-results.md`).

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
