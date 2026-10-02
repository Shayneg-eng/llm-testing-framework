# {{TITLE}}

| | |
|---|---|
| **ID** | {{ID}} |
| **Study slug** | `{{SLUG}}` |
| **Area** | {{AREA}} |
| **Status** | planned |
| **Started** | {{DATE}} |
| **Models** | (fill in) |
| **Question** | {{QUESTION}} |

## Design

What is varied, what is held constant, replicates per cell, number of trials/calls, scoring
scale (state the sign convention), which harness/shared code it builds on.

## How to run

```
python studies/{{AREA}}/{{SLUG}}/scripts/{{SLUG}}_study.py
python studies/{{AREA}}/{{SLUG}}/scripts/{{SLUG}}_analysis.py
```

Output: `runs/` (raw data), `charts/` (figures). Notes on scoring/hand-editing of run files.

## Findings

Headline result(s) in 2-5 lines, then links to the dated write-ups in `notes/` and to the key
figures in `charts/`. Update `INDEX.md` when this changes.

## Caveats

Replicate counts, single rater / judge setup, number of models, halted or missing trials.

## Related

Studies this builds on or should be compared with (link their folders), and any
`results/` package made from this study.

## Next steps

1.
