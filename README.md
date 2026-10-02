# LLM Testing

Home for all of my LLM testing: bias and drift under adversarial pressure, model architecture
probes, multi-agent teamwork, and whatever comes next. Built to keep growing without
reshuffling.

## Start here

| I want to... | Open |
|---|---|
| See every study and where it stands | `INDEX.md` |
| Know where a file goes / how the folders work | `ORGANIZATION.md` |
| Add a new study | `docs/ADDING_A_STUDY.md` (or run `python tools/new_study.py`) |
| Know when and how to tidy up | `docs/REORGANIZATION.md` |
| Check naming and code conventions | `docs/CONVENTIONS.md` |
| See what changed in the structure, and old-path → new-path | `docs/CHANGELOG.md` |
| Share a finding with someone | `results/` |

## Layout at a glance

```
studies/<area>/<study>/{README.md, scripts/, runs/, charts/, notes/}   every experiment
shared/                 code and data used by 2+ studies
results/                hand-off packages
cross_study_notes/      write-ups spanning several studies
docs/  templates/  tools/   the process around all of it
archive/  scratch/          retired material / disposable work
```

Areas today: `bias`, `architecture`, `teamwork` (empty so far).

## Setup

```
pip install -r requirements.txt
```

Run a study from anywhere: `python studies/<area>/<study>/scripts/<script>.py`. Scripts find
their own folders and `shared/` relative to their location, so the working directory does not
matter. Studies call the Poe API (`api.poe.com`) and need network access to it.

## Keeping it clean

Run `python tools/check_structure.py` at the end of any session that added files. It must
report `0 problems`.
