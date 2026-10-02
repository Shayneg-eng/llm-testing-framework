# ORGANIZATION.md — how this directory is laid out and kept clean

This is the single source of truth for where everything in `LLM Testing/` lives. If a file
has no obvious home under these rules, that is a signal to fix the rules (see
`docs/REORGANIZATION.md`), not to improvise a new folder.

**The one-sentence rule:** every experiment is a self-contained *study folder* under
`studies/<area>/<study>/`; anything used by two or more studies lives in `shared/`;
everything else has exactly one named home listed below.

Last structural change: see `docs/CHANGELOG.md`.

---

## 1. Top-level layout

```
LLM Testing/
├── README.md              what this directory is, start here
├── ORGANIZATION.md        this file: the rules
├── INDEX.md               registry of every study (id, area, status, question, headline finding)
├── requirements.txt       Python dependencies for everything under studies/ and shared/
│
├── studies/               ALL experiments, one self-contained folder each
│   └── <area>/<study>/    e.g. studies/bias/congruency/
│
├── shared/                code and reference data used by 2+ studies (seeds, scorers, helpers)
├── results/               polished, hand-off-ready packages of standout findings
├── cross_study_notes/     dated write-ups that span several studies (audits, syntheses, direction notes)
│
├── docs/                  process docs: adding a study, when to reorganize, conventions, changelog
├── templates/             copy-me scaffolds (the study template)
├── tools/                 small maintenance scripts (check_structure.py, new_study.py, old migrations)
│
├── archive/               retired studies and superseded material; never deleted, never edited
└── scratch/               disposable work area; anything here may be deleted at any time
```

Nothing else is allowed at the top level. `tools/check_structure.py` flags anything that is.

---

## 2. Areas (`studies/<area>/`)

An **area** is a research theme. It groups studies that ask related questions.

| Area | What belongs in it |
|---|---|
| `bias` | Directional bias, drift under adversarial pressure, framing sensitivity, group/trope bias (all RSPA-style studies) |
| `architecture` | Probing model internals-by-behaviour: sequential reasoning depth, memory, context handling, tokenization effects |
| `teamwork` | Multi-agent collaboration, role division, debate/consensus, delegation |
| `forecasting` | Prediction tasks scored against real outcomes: wisdom-of-crowd ensembles, calibration, backtests on market data |

**Adding an area:** create `studies/<new_area>/` when you start the first study that does not
fit an existing area, then add a row to the table above in the same edit. Area names are
one lowercase word (or snake_case) and describe a *question type*, not a model or a date.
If you are unsure which area, use the one whose existing studies you would want to read first
when interpreting the new one.

**Splitting an area:** when an area holds more than ~12 studies, or two clearly distinct
sub-themes have emerged, split it (see `docs/REORGANIZATION.md`, trigger T3).

---

## 3. Anatomy of a study folder

Every study, regardless of area, has the same shape:

```
studies/<area>/<study_slug>/
├── README.md      required. Question, design, status, how to run, findings summary, links
├── scripts/       code that runs the study and analyses it (flat, no subfolders)
├── runs/          raw data written by the run scripts (flat, machine-written)
├── charts/        finished figures produced by the analysis scripts (flat)
└── notes/         dated human write-ups about this study
```

Optional, only when needed:

```
├── runs_superseded/<label>/   raw data from an earlier design of the SAME study that no longer
│                              applies but is kept for the record (label = why + date)
└── design/                    long design docs / prompt templates that are too big for the README
```

Rules for each part:

**`README.md`** starts with a small fact block (ID, area, status, dates, models, question),
then design, how to run, findings, caveats, next steps. Use `templates/study/README.md`.
It is the first thing to update when the study's status or headline result changes, and
`INDEX.md` gets updated in the same edit.

**`scripts/`** holds code only. Convention: `rspa_<study>_study.py` (or `<study>_study.py`)
runs the study and writes to `runs/`; `<study>_analysis.py` reads `runs/` and writes to
`charts/`. Scripts locate everything relative to `Path(__file__)` (never the current working
directory) and reach shared code through the 3-line bootstrap in `docs/CONVENTIONS.md`.
`__pycache__` folders are regenerable noise: ignored by the checker and safe to delete any time.

**`runs/`** holds only raw or per-run machine output: report JSON, transcripts, audit logs,
aggregate CSV/JSON that the study's own scripts produce. No charts, no prose. Filenames
follow `docs/CONVENTIONS.md`.

**`charts/`** holds only finished figures (`.png`, `.svg`, `.pdf`). No data, no prose.
Because each study has its own `charts/`, chart filenames do not need a study prefix, but
descriptive names are required (`round5_by_religion.png`, not `chart1.png`).

**`notes/`** holds dated Markdown write-ups, `YYYY-MM-DD-<short-topic>.md`. One file per
significant result, decision, or follow-up. The folder reads as the study's timeline.

**Study slug:** lowercase snake_case, describes what the study varies or asks, contains no
date and no model name (`argument_type`, not `argument_type_gpt_oss_2026_09`). The slug is
permanent; if the study is renamed, record the old name in the README and CHANGELOG.

**One question per study.** A change to the design that would make earlier data
non-comparable is a *new study* (or a `runs_superseded/` split), never a silent overwrite.
Follow-ups that reuse the same harness, add models, or add replicates stay in the same study.

---

## 4. The other top-level homes

**`shared/`** — code or reference data imported/read by two or more studies (`seeds.py`,
`lexical_drift_scorer.py`, `aggregate_replicates.py`, the topic and seed bank). Something
starts inside the first study that needs it; the moment a second study needs it, move it to
`shared/`. Shared code never writes into a study folder on its own; it receives the target
path from the calling script (or from a documented argument such as `prefix`).

**`results/`** — hand-off packages. `results/<short-descriptive-name>/` is a complete,
zip-and-send folder: `README.md` (headline, what to look at, caveats, source study),
copied-in charts, copied-in data extract. This is the *one* sanctioned duplication of
charts/data; the study folders stay authoritative and a package is a point-in-time snapshot.
Only standout findings get packaged. No date prefix in the name.

**`cross_study_notes/`** — dated write-ups (`YYYY-MM-DD-<topic>.md`) that are about the
project or several studies at once: code audits, synthesis across studies, research-direction
notes, methodology decisions. If a note is really about one study, it goes in that study's
`notes/` instead.

**`docs/`** — the process documents: `ADDING_A_STUDY.md`, `REORGANIZATION.md`,
`CONVENTIONS.md`, `CHANGELOG.md`. Rules about the directory, not research content.

**`templates/`** — copy-me scaffolds. `tools/new_study.py` copies `templates/study/`.

**`tools/`** — maintenance scripts about the directory itself, not experiments.
`tools/migrations/` keeps one-shot restructuring scripts after they have run, for the record.

**`archive/`** — where retired material goes instead of being deleted: an abandoned study
(`archive/studies/<area>/<study>/`), or old top-level material. Archived items keep their
internal structure and get a line in `docs/CHANGELOG.md`. Nothing in `archive/` is imported
or re-run. Deleting is allowed only for genuinely regenerable junk (`__pycache__`, `scratch/`
contents), never for data or write-ups.

**`scratch/`** — disposable. One-off experiments, throwaway outputs, half-formed drafts. If
something in `scratch/` turns out to matter, promote it: make it a study, or move it into one.
Contents older than 30 days are fair game to clear.

---

## 5. Where does this new file go? (decision list)

Work down the list and stop at the first match.

1. It is raw output written by a run script → `studies/<area>/<study>/runs/`
2. It is a figure made from that data → `studies/<area>/<study>/charts/`
3. It is code that runs or analyses one study → that study's `scripts/`
4. It is code or data reused by 2+ studies → `shared/`
5. It is a write-up about one study → that study's `notes/`
6. It is a write-up about several studies or the project → `cross_study_notes/`
7. It is a polished package for someone outside the project → `results/<name>/`
8. It is a process rule or how-to for this directory → `docs/`
9. It is a maintenance script for this directory → `tools/`
10. It is a copy-me scaffold → `templates/`
11. It is retired but worth keeping → `archive/`
12. It is disposable / unsure → `scratch/` (and decide within 30 days)

If two answers seem equally right, take the earlier one. If nothing fits, do not create a new
top-level folder: put it in `scratch/`, then propose a rule change via `docs/REORGANIZATION.md`.

---

## 6. Standing rules (short form)

- One study, one folder. Never point a new study's output at another study's `runs/`.
- Reading another study's data is fine and is done by path from `ROOT`; copying it is not.
- Every new study is registered in `INDEX.md` the moment its folder is created.
- Every file lands in its home when it is created, not "later".
- Scripts never depend on the working directory and never hardcode absolute paths.
- Nothing is deleted except regenerable junk; everything else is moved to `archive/`.
- API keys are hardcoded in scripts for now (project testing policy). Rotate them before any
  script leaves this machine; `results/` packages must never contain scripts with keys.
- Run `python tools/check_structure.py` before finishing any session that added files.

Process detail: adding a study → `docs/ADDING_A_STUDY.md`. Cleanup triggers and procedure →
`docs/REORGANIZATION.md`. Naming and code conventions → `docs/CONVENTIONS.md`.
