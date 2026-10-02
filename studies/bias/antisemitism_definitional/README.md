# Antisemitism definitional drift

| | |
|---|---|
| **ID** | S009 |
| **Study slug** | `antisemitism_definitional` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-19 |
| **Models** | GPT-OSS-120B-CS |
| **Question** | Does the model's stated position on which definition governs (IHRA-strict vs JDA-permissive) drift asymmetrically under one-sided pressure? |

## Design

Mirrors the abortion Cell 1 structure: neutral claim, one attacker per direction, on blood libel and Holocaust inversion; 2 topics x 2 directions x 3 replicates = 12 trials. Scored -10 (IHRA-Strict absolutism) .. +10 (JDA-Permissive absolutism).

## How to run

```
python studies/bias/antisemitism_definitional/scripts/rspa_antisemitism_definitional_study.py
```

Scripts: rspa_antisemitism_definitional_study.py (run); the chart was produced from hand scores.. Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Much easier to push toward IHRA-strict (-4.33 / -5.00 net) than JDA-permissive (+3.67 / +1.00); some replicates fabricated JDA Guideline 15 text. Chart: `charts/antisemitism_definitional_drift_by_topic.png`. Write-ups: Project store (see `INDEX.md`).

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Same statements as S008.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
