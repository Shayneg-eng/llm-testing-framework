# Argument type

| | |
|---|---|
| **ID** | S007 |
| **Study slug** | `argument_type` |
| **Area** | bias |
| **Status** | complete |
| **Started** | 2026-09-15 |
| **Models** | GPT-5.4-Nano, Gemini-3.5-Flash-Lite, Kimi-K3; GPT-OSS-120B-CS replication (2026-09-19) |
| **Question** | Which style of neutral framing (rights-in-tension, legal, medical, philosophical, empirical) is most exploitable under sustained attack? |

## Design

Cell 1, abortion_policy, attacked from Direction A only, 5 neutral seeds x 5 replicates per model. The `MODELS` list in the run script was edited between the original three-model run and the GPT-OSS-120B-CS replication.

## How to run

```
python studies/bias/argument_type/scripts/rspa_argument_type_study.py
python studies/bias/argument_type/scripts/argument_type_analysis.py
```

Scripts: rspa_argument_type_study.py (run), argument_type_analysis.py (charts). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

Medical framing is the most exploitable for GPT-OSS-120B-CS and replicated cleanly (-6.40 here vs -6.80 in S005); a bimodal 'attractor' pattern appeared on 2 of 3 models (`notes/2026-09-15-argument-type-results.md`; the replication write-up is in the Project store, see `INDEX.md`). Charts: `charts/argument_type_by_seed.png`, `charts/argument_type_net_movement.png`.

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

Follows S005. One trial (`0-philosophical` rep 4) was halted by the harness audit for a forbidden meta-term.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
