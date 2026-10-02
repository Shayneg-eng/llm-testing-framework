# Conventions

Naming, file formats and code patterns shared by every study. Study-specific details go in the
study README.

## Naming

| Thing | Pattern | Example |
|---|---|---|
| Area | lowercase word / snake_case | `bias`, `architecture` |
| Study slug | lowercase snake_case, no date, no model | `argument_type` |
| Study ID | `S` + 3 digits, assigned in order of creation, never reused | `S007` |
| Run script | `<study>_study.py` (RSPA family: `rspa_<study>_study.py`) | `rspa_congruency_study.py` |
| Analysis script | `<study>_analysis.py` | `congruency_analysis.py` |
| Report JSON (RSPA) | `rspa_<study>_<topic>_<seed>_<model>_rep<N>.json` | |
| Transcript | `transcript_<study>_<topic>_<seed>_<model>_rep<N>.md` | |
| Audit log | `audit_log_<topic>_<study>.json` | |
| Aggregate | `aggregate_<what>.json` / `.csv` | |
| Note | `YYYY-MM-DD-<short-topic>.md` | `2026-09-19-antisemitism-pilot-results.md` |
| Chart | descriptive snake_case | `round5_by_religion.png` |
| Result package | `results/<short-descriptive-name>/` | `claude-sonnet-4.6-religion-split/` |
| Archive entry | same relative path as before, under `archive/` | |
| Superseded data | `runs_superseded/<reason>_<YYYY-MM-DD>/` | `xor_state_2026-09-24` |

Seed keys containing `+` are filename-escaped as `plus_` (`+++a` → `plus_plus_plus_a`) using the
study's `safe_seed()` helper. Keep using that pattern; do not invent another.

Model names in filenames use the Poe bot name as-is (`GPT-OSS-120B-CS`); model slugs for
sequential probes use lowercase underscores (`gpt_4_turbo`).

## Code pattern: locating things

Every script under `studies/<area>/<study>/scripts/` starts its imports of local code with:

```python
import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[4]          # .../LLM Testing
_sys.path.insert(0, str(ROOT / "shared"))            # so `import seeds` works
```

and defines its paths relative to itself:

```python
STUDY_DIR  = _Path(__file__).resolve().parent.parent
OUTPUT_DIR = STUDY_DIR / "runs"      # run scripts write here (mkdir(exist_ok=True))
CHARTS_DIR = STUDY_DIR / "charts"    # analysis scripts write here (mkdir(exist_ok=True))
```

`parents[4]` is correct for the standard depth `studies/<area>/<study>/scripts/<file>.py`.
Reading another study's data: `ROOT / "studies" / "<area>" / "<other_study>" / "runs"`.
Shared code that operates on more than one study's data takes the directory as an argument
(or a documented `prefix` that maps to it) instead of hardcoding one.

## Data conventions

- Raw data is append-only: reruns write new files (or new `rep<N>`), they do not edit old ones.
  Hand scores are added *into* the report JSON as fields (e.g. `drift_score_hand`); that is the
  only sanctioned edit to raw reports, and it is described in the study README.
- Every run script writes an audit log alongside the data.
- Scales are stated in the study README (e.g. drift −10…+10), including the sign convention.
- Every write-up states its caveats: replicates per cell, number of models, rater setup, any
  missing or halted trials.

## Documents

- Markdown, UTF-8, LF line endings preferred.
- Fact block at the top of every study README (see template), dates as `YYYY-MM-DD`.
- Cross-references use paths relative to the directory root (`studies/bias/congruency/notes/...`),
  so they survive moves that keep the root fixed and are easy to grep when something moves.
- When quoting a project-store doc that has no local copy yet, cite it as
  `Project: claude/<name>.md`.

## Secrets

API keys are hardcoded in scripts during testing (project policy). Consequences: scripts are
never copied into `results/` packages; the directory is not published or shared as-is; keys
are rotated before anything leaves this machine.
