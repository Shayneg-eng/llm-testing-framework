# Directory organization

How this project's folder is laid out, why, and the rules for keeping it that way as
more studies get added. Written 2026-09-15 after an audit found several accumulated
problems (mixed-study folders, stale duplicate charts, an unlabeled folder) -- all fixed
as part of writing this doc. Updated 2026-09-20 to add the `results/` folder. See
"History" at the bottom for exactly what changed, and when.

## The rule in one sentence

**Every study gets exactly one `runs_<study>/` folder for its raw data, every chart from
every study lands in the single shared `analysis_charts/`, every write-up lands in
`current research direction/`, and any finding worth handing to someone else as a
standalone package gets its own folder under `results/` -- nothing else, no exceptions.**

## Top-level layout

```
S.H.A.Y.N.E bias testing/
├── README.md                     -- what this project is, how to run the original mockup
├── ORGANIZATION.md                -- this file
├── requirements.txt               -- pip dependencies
├── scripts/                       -- ALL code lives here, nothing else does
├── analysis_charts/               -- ALL finished charts from every study, flat, nothing else
├── current research direction/    -- ALL dated write-ups/findings, one .md per study (or follow-up)
├── results/                       -- shareable, self-contained packages of standout findings
│   └── <result-name>/             -- one folder per result: its charts + data + a README, copied in
├── runs_pipeline_baseline/        -- raw data: the original 4-topic pipeline mockup
├── runs_factorial/                -- raw data: the 4-cell factorial study
├── runs_core_replication/         -- raw data: the Cell1-vs-Cell4 core replication study
├── runs_congruency/                -- raw data: the congruency study
├── runs_asymmetric/                -- raw data: the asymmetric-design study
├── runs_starting_position/         -- raw data: the graded 9-seed starting-position study
├── runs_argument_type/             -- raw data: the argument-type study (5 argument types x 3 models)
└── runs_group_trope_bias/          -- raw data: the group-trope-bias study (single- and multi-model)
```

Each `runs_<study>/` folder holds *only*:
- raw JSON reports (`rspa_<study>_<topic>_<seed>_<model>_rep<N>.json`)
- raw markdown transcripts (`transcript_<study>_<topic>_<seed>_<model>_rep<N>.md`)
- that study's audit log (`audit_log_<topic>_<study>.json`)
- any per-study aggregate/intermediate JSON or CSV the study's own scripts produce (e.g.
  `aggregate_<topic>_<seed>_<model>.json`, `aggregate_<study>_scores_multimodel.csv`)

It does **not** hold charts (those go to `analysis_charts/`) or write-ups (those go to
`current research direction/`). This is the rule that broke down before -- see History.

## `results/` -- shareable packages (added 2026-09-20)

`analysis_charts/` and `current research direction/` are for *working* on the project;
`results/` is for *showing it to someone else*. Every subfolder under `results/` is a
complete, self-contained package: if you zipped that one subfolder and sent it to
someone with no other context, they'd have everything they need -- the charts, the
underlying data, and a short README explaining what they're looking at.

```
results/
└── <result-name>/
    ├── README.md              -- short: the headline finding, what's in the folder,
    │                             caveats, and a pointer back to the source study
    ├── <chart files>.png      -- copied in from analysis_charts/, not moved
    └── <data files>.csv       -- copied in from the study's runs_<study>/ folder
```

**This is the one deliberate exception to "never duplicate a chart"** (see What NOT To
Do, below) -- a `results/` package is meant to leave the project folder as a standalone
unit, so it needs its own copies rather than links. The authoritative version of every
chart and dataset still lives in `analysis_charts/` and `runs_<study>/`; a `results/`
package is a curated, point-in-time snapshot of a subset of that, not a new source of
truth. If the underlying study is rerun or a chart is regenerated, the package's copy
does **not** auto-update -- refresh it by hand if the result is still worth showing.

**Naming:** `results/<short-descriptive-name>/`, no date prefix (unlike write-ups) --
the name should say what the finding *is*, e.g. `claude-sonnet-4.6-religion-split/`, not
which study it came from or when it was packaged (that's in the README).

**What goes in the README:** a one-paragraph headline stating the finding in plain
language, which chart(s)/panel(s) to look at and what to look for, a short "what's in
this folder" file list, the usual caveats (replicate count, single-rater scoring, any
incomplete data), and a "Source" line pointing back to the scripts and `runs_<study>/`
folder that produced it.

**When to make one:** only for a result you'd actually hand to someone -- not every
chart from every study. If it's just "here's what the pilot looked like," that's what
`current research direction/` write-ups are for. `results/` is for the standout findings.

## Naming conventions

**Scripts** (`scripts/`): one `rspa_<study>_study.py` (or similarly named) file runs the
study and writes raw data; a separate `<study>_analysis.py` file reads that raw data and
produces charts. Both live flat in `scripts/`, no subfolders.

**Run files** (`runs_<study>/`):
- `rspa_<study>_<topic>_<seed>_<model>_rep<N>.json` -- one replicate's full structured
  report
- `transcript_<study>_<topic>_<seed>_<model>_rep<N>.md` -- the same replicate, formatted
  for reading
- `audit_log_<topic>_<study>.json` -- the harness's own pass/fail audit trail for that
  study's run
- seed keys with `+` get filename-escaped as `plus_` (e.g. `+++a` -> `plus_plus_plus_a`),
  handled by each study's own `safe_seed()` helper -- keep using that pattern for new
  studies rather than inventing a new escaping scheme

**Charts** (`analysis_charts/`, flat, no subfolders): every chart filename starts with
its study name, e.g. `congruency_*.png`, `asymmetric_*.png`, `starting_position_*.png`,
`core_replication_*.png`, `group_trope_bias_*.png` (single-model) /
`group_trope_bias_multimodel_*.png` (multi-model). This prefix is the only thing
preventing collisions in a flat folder, so **never save a chart without its study name
as the prefix**.

**Write-ups** (`current research direction/`): `YYYY-MM-DD-<short-topic>.md`, one file per
study (or per significant follow-up/discussion on an existing study). Chronological by
filename, so the folder itself is a readable timeline of the project.

**Results packages** (`results/`): `<short-descriptive-name>/`, see the `results/`
section above.

## Adding a new study: the checklist

1. Write `scripts/rspa_<newstudy>_study.py`. Set its output directory to
   `Path(__file__).parent.parent / "runs_<newstudy>"` and have it `mkdir(exist_ok=True)`
   that folder itself -- don't create the folder by hand.
2. Follow the existing file-naming convention exactly (see above) so the study is
   consistent with every other one.
3. Write `scripts/<newstudy>_analysis.py`. It reads from `runs_<newstudy>/` but writes
   every chart to `Path(__file__).parent.parent / "analysis_charts"` (also
   `mkdir(exist_ok=True)` there), with the study name as the filename prefix.
4. Run the study, hand-score (or otherwise score) the data, run the analysis script.
5. Write `current research direction/YYYY-MM-DD-<newstudy>-results.md` with the findings,
   the usual single-rater/single-topic/single-model caveats, and a Next Steps section.
6. Push all three (raw data folder, new charts, new note) to the project doc store /
   your machine, same as every study before it.
7. If the new study reuses another study's data for comparison (the way
   `analyze_core_replication.py` compares Cell 1 vs Cell 4 *within* its own core-
   replication reports), keep the reused data being *read*, not *copied* -- point the new
   script's loader at the original study's `runs_<study>/` folder rather than duplicating
   files into the new one.
8. If any single result from the study is striking enough to show someone on its own,
   package it: make `results/<short-descriptive-name>/`, copy in the relevant chart(s)
   and a data extract, and write the README as described in the `results/` section
   above.

## What NOT to do (lessons from this cleanup)

- **Don't let a new study's script default to an old study's output folder.** This is
  exactly how `runs_factorial/` ended up holding two unrelated studies' data (the
  factorial study and the later core-replication study both pointed `OUTPUT_DIR` at
  `runs_factorial/`, even though they don't reference each other's files). Every study
  gets its own folder, always, even if it feels closely related to an existing one.
- **Don't hand-copy a chart to a second location "so it's easy to find."** That's how
  `Claude outputs/` ended up as a stale, silently-drifted duplicate of part of
  `analysis_charts/` (same filenames, different file sizes -- i.e. different, out-of-sync
  versions of the same chart). There is exactly one place charts live for *working*
  purposes. The one exception is a `results/` package (see above), which exists
  specifically to be a standalone, hand-off copy -- that's a deliberate, documented
  duplication, not an accidental one, and it doesn't get treated as a second source of
  truth to keep syncing.
- **Don't leave a folder without a name that says what's in it.** `runs/` (no suffix) was
  fine when it was the only run folder; once a second study existed, it became ambiguous
  clutter. Every raw-data folder is `runs_<study>`, no exceptions, even the original one
  (now `runs_pipeline_baseline/`).
- **`__pycache__` folders are safe to delete any time** -- Python regenerates them
  automatically. They were left sitting in the repo before; there's no reason to keep
  them around or worry about deleting them.

## History

**2026-09-20: added `results/`.** First package created:
`results/claude-sonnet-4.6-religion-split/`, packaging the group-trope-bias
multi-model study's standout finding (Claude Sonnet 4.6 was the only one of 5 models
tested that showed a real per-religion split -- including a sign flip on the
dual-loyalty/reconciliation scenario for the Jewish condition). Added the `results/`
section to this doc and the checklist step above so future standout findings get
packaged the same way.

**2026-09-15 cleanup**, prompted by a folder audit that found:
1. `runs_factorial/` mixed the factorial study's data with the unrelated core-replication
   study's data (including two different audit logs). **Fixed:** split into
   `runs_factorial/` (factorial only) and `runs_core_replication/` (core replication
   only); updated `rspa_core_replication.py`, `analyze_core_replication.py`, and
   `fill_core_hand_scores.py` to point at the new folder.
2. `runs/` (no suffix) didn't say what it held. **Fixed:** renamed to
   `runs_pipeline_baseline/`; updated `rspa_pipeline.py` and `README.md` accordingly.
3. `Claude outputs/` was a stale, partially out-of-sync duplicate of four charts already
   in `analysis_charts/`. **Fixed:** deleted; `analysis_charts/` (written directly by the
   analysis scripts) is the authoritative copy.
4. Charts were triplicated across a study's `runs_<study>/` folder, `analysis_charts/`,
   and `Claude outputs/`, with no single source of truth. **Fixed:** every chart now
   lives only in `analysis_charts/`; `congruency_analysis.py`, `asymmetric_analysis.py`,
   `starting_position_analysis.py`, and `analyze_core_replication.py` were updated to
   write there directly instead of into their study's run folder.
5. `analysis_charts/` was missing the newest study's charts (starting-position), since
   they'd only been generated into `runs_starting_position/`. **Fixed:** moved in as part
   of the same cleanup; future studies won't have this problem since step 3 above points
   every analysis script at `analysis_charts/` from the start.
6. `aggregate_replicates.py` and `lexical_drift_scorer.py` are shared utilities that
   operate on either the factorial or core-replication data depending on a `prefix`
   argument; after the split in (1) they needed to resolve *which* folder to use per
   call instead of a single hardcoded one. **Fixed:** both now pick `runs_factorial/` or
   `runs_core_replication/` based on the `prefix` argument at call time.
7. Two orphaned `__pycache__/` folders. **Fixed:** deleted (regenerate automatically,
   never need to be committed or backed up).

No data was deleted in this cleanup -- every change was a move, a rename, or removing a
confirmed stale duplicate whose authoritative version still exists in `analysis_charts/`.
