# Sequential depth probe

| | |
|---|---|
| **ID** | S011 |
| **Study slug** | `sequential_depth_probe` |
| **Area** | architecture |
| **Status** | running |
| **Started** | 2026-09-24 |
| **Models** | gpt_4_turbo, llama_3_3_70b_t (legacy design also ran gpt_oss_120b_cs, grok_4_5) |
| **Question** | How many sequential reasoning steps can a model chain before its accuracy falls to chance? |

## Design

One trial file per call (`trial_L<LL>_rep<N>_<model_slug>.json`) plus a per-model summary JSON with a robust upper-bound estimate; the run stops early when results sit at or below chance for consecutive lengths and can resume from an existing summary. The first design (XOR-state) was scrapped on 2026-09-24 because it produced misleading results; its data is kept in `runs_superseded/xor_state_2026-09-24/`.

## How to run

```
python studies/architecture/sequential_depth_probe/scripts/sequential_depth_probe_study.py
```

Scripts: sequential_depth_probe_study.py (run, summary, resume). Output: `runs/` (raw data), `charts/` (figures). Scripts locate their
own folders and `shared/` relative to their location, so the working directory does not matter.

## Findings

No headline yet: the redesigned run is in progress (gpt_4_turbo has data through L04).

## Caveats

Single rater / single scoring pass, small replicate counts, and (unless stated) a single model, as in every RSPA-style study here. Status was inferred from the write-ups during the 2026-09-25 restructure.

## Related

First study in the `architecture` area.

## Folder contents

`scripts/`, `runs/`, `charts/`, `notes/` as described in `ORGANIZATION.md` section 3. Structure
history: moved into this layout on 2026-09-25 (`docs/CHANGELOG.md`).
