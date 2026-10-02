# Structure changelog

Every change to the directory's *structure or rules* is recorded here, newest first. Research
results belong in study notes, not here.

Entry format: date, what changed, why (trigger from `REORGANIZATION.md` if any), and how to
find old things.

---

## 2026-09-26: new area `forecasting`

**Why:** S012 `wisdom_of_crowd_btc` (LLM ensembles predicting BTC direction, scored against real outcomes) fits no existing area (`ORGANIZATION.md` section 2, adding an area).

**What changed:** added `studies/forecasting/` and its row in the ORGANIZATION.md area table. No files moved.

---

## 2026-09-25: expandable multi-study layout (major restructure)

**Why:** the directory was a single-topic layout (`scripts/`, `analysis_charts/`,
`current research direction/`, flat `runs_<study>/` folders) built for one RSPA project. It is
now the home for all LLM testing (bias, architecture, teamwork, and future areas), so it needed
a structure that scales without reshuffling: T7 (convention no longer fits reality).

**What changed:**
- Every study became a self-contained folder `studies/<area>/<study>/` with `scripts/`,
  `runs/`, `charts/`, `notes/`, and a `README.md`.
- Shared code (`seeds.py`, `lexical_drift_scorer.py`, `aggregate_replicates.py`) moved to `shared/`.
- `analysis_charts/` (one flat folder) was split by study into each study's `charts/`.
- `current research direction/` write-ups were split into each study's `notes/`; the
  project-wide direction note went to `cross_study_notes/`.
- `runs_<study>/` folders became `studies/<area>/<study>/runs/`.
- `runs_sequential_depth_probe_legacy_xor_state_2026_09_24/` became
  `studies/architecture/sequential_depth_probe/runs_superseded/legacy_xor_state_2026-09-24/`.
- New: `INDEX.md`, `docs/`, `templates/`, `tools/`, `archive/`, `scratch/`, `cross_study_notes/`.
- All scripts had their paths rewritten to be relative to their own location (see
  `CONVENTIONS.md`); `asymmetric` now reads `congruency` data from its new location.
- `results/` is unchanged.

**Old → new path map:**

| Old | New |
|---|---|
| `runs_pipeline_baseline/` | `studies/bias/pipeline_baseline/runs/` |
| `runs_factorial/` | `studies/bias/factorial/runs/` |
| `runs_core_replication/` | `studies/bias/core_replication/runs/` |
| `runs_congruency/` | `studies/bias/congruency/runs/` |
| `runs_asymmetric/` | `studies/bias/asymmetric/runs/` |
| `runs_starting_position/` | `studies/bias/starting_position/runs/` |
| `runs_argument_type/` | `studies/bias/argument_type/runs/` |
| `runs_antisemitism/` | `studies/bias/antisemitism/runs/` |
| `runs_antisemitism_definitional/` | `studies/bias/antisemitism_definitional/runs/` |
| `runs_group_trope_bias/` | `studies/bias/group_trope_bias/runs/` |
| `runs_sequential_depth_probe/` | `studies/architecture/sequential_depth_probe/runs/` |
| `scripts/seeds.py`, `lexical_drift_scorer.py`, `aggregate_replicates.py` | `shared/` |
| `scripts/<other>.py` | `studies/<area>/<study>/scripts/` |
| `analysis_charts/<file>` | `studies/<area>/<study>/charts/` (by study) |
| `current research direction/<file>` | `studies/<area>/<study>/notes/` (or `cross_study_notes/`) |
| `current research direction/2026-09-10.md` | `cross_study_notes/2026-09-10-research-direction.md` (renamed to fit `YYYY-MM-DD-<topic>.md`; other historical notes cite it as `2026-09-10.md`) |
| old `README.md` (RSPA mockup) | `studies/bias/pipeline_baseline/design/original_mockup_README.md` |
| old `ORGANIZATION.md` | `archive/ORGANIZATION_2026-09-20_pre-restructure.md` |

Historical write-ups still mention the old paths (`runs_starting_position/`, `analysis_charts/`,
...). Those references are left as written, since they describe the state at the time; use the
table above to translate.

**Tooling:** the move was performed by `tools/migrations/2026-09-25_restructure.py`, with a
before/after file-hash manifest verifying that no file was lost or altered.

**Retired:** the previous 2026-09-15 / 2026-09-20 `ORGANIZATION.md` (single flat
`analysis_charts/` and `current research direction/` rules) is superseded by the current one.
The one-sentence rule and the "never duplicate charts except in `results/`" principle carry over.

---

## Earlier history (from the previous ORGANIZATION.md, condensed)

- **2026-09-20:** added `results/` for hand-off packages (first: `claude-sonnet-4.6-religion-split`).
- **2026-09-15:** split `runs_factorial/` into factorial and core-replication; renamed `runs/` to
  `runs_pipeline_baseline/`; removed the stale duplicate `Claude outputs/`; consolidated charts
  into a single `analysis_charts/`; made shared scorers pick the run folder per call; deleted
  orphaned `__pycache__`. No data was deleted.
