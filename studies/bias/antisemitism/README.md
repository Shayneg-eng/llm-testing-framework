# Antisemitism classification pilot

| | |
|---|---|
| **ID** | S008 |
| **Study slug** | `antisemitism` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-19 |
| **Models** | GPT-OSS-120B-CS |
| **Question** | Under sustained minimization or overreach pressure, how stable are the model's verdict and confidence when classifying antisemitism-lexicon statements? |

## Design

Defender classifies a fixed statement each round (VERDICT / CONFIDENCE / REASONING) instead of evolving a claim. 2 categories (blood libel, Holocaust inversion) x 3 attack cells (minimization, overreach_same, overreach_paired) x 3 replicates = 18 trials, Cell 1, round 0 baseline + 5 rounds. Seed categories come from the Decoding Antisemitism Lexicon (Becker et al.); ground truth anchored to Becker et al. and the IHRA working definition.

## How to run

```
python studies/bias/antisemitism/scripts/rspa_antisemitism_study.py
```

Scripts: rspa_antisemitism_study.py (run). The harness output is the score, so there is no separate analysis script yet.. Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Clean statements keep their verdict but confidence roughly halves (6/6); blood-libel overreach converges to confident 'antisemitic' (3/3). Full write-up: Project store `claude/2026-09-19-antisemitism-pilot-results.md` (see `INDEX.md`).

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Superseded in design by S009 for the 'match the abortion structure' question; both remain valid.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
