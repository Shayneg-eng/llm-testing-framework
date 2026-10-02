# Adding a new study

Follow this every time. It takes five minutes and is the reason the directory stays clean.

## 1. Scaffold it

```
python tools/new_study.py <area> <study_slug> "<one-line research question>"
```

This copies `templates/study/` to `studies/<area>/<study_slug>/`, fills in the README fact
block, assigns the next study ID, and appends a row to `INDEX.md`. If the area does not exist
yet it is created, and you are reminded to add it to the area table in `ORGANIZATION.md`.

Doing it by hand: copy `templates/study/`, rename, fill the README, add the `INDEX.md` row.

Choosing the slug: lowercase snake_case, names what the study varies or asks, no date, no
model name. Check `INDEX.md` first: if the idea is a follow-up on an existing study (same
harness, more models or replicates, same design), it does **not** get a new folder. Add runs
to that study and write a new dated note in its `notes/`.

New study or same study?

| Situation | Decision |
|---|---|
| Same design, more replicates or more models | Same study |
| Same design, bug fixed, rerun | Same study; move the bad data to `runs_superseded/<label>/` |
| Design change that makes old data non-comparable | New study; cross-link the READMEs |
| New question, even reusing the same harness code | New study; shared code moves to `shared/` |

## 2. Write the code

- Run script: `scripts/<study>_study.py` (RSPA-style studies keep the `rspa_` prefix).
  Output goes to `runs/` next to `scripts/`.
- Analysis script: `scripts/<study>_analysis.py`. Reads `runs/`, writes to `charts/`.
- Use the path bootstrap from `docs/CONVENTIONS.md` so `shared/` is importable and paths are
  independent of the working directory. The template script already has it.
- Anything a second study will need (seeds, scorers, API helpers) goes to `shared/`, not
  copied. If you are about to copy a function from another study's `scripts/`, stop and move
  it to `shared/` instead.
- If the study reuses another study's data, read it by path from `ROOT`
  (`ROOT / "studies" / "bias" / "congruency" / "runs"`); never copy it.

## 3. Run and record

1. Run the study. Raw data lands in `runs/` automatically.
2. Score it (hand or LLM-judge) and run the analysis script. Figures land in `charts/`.
3. Write `notes/YYYY-MM-DD-<topic>.md` with the findings, caveats (replicate counts, single
   rater, single model, incomplete cells) and next steps.
4. Update the study `README.md`: status, models, headline finding, links to notes and charts.
5. Update the `INDEX.md` row: status, date, one-line headline.

## 4. Package standouts (optional)

If a finding is worth handing to someone else, create `results/<short-name>/` with a README,
copied charts, and a data extract. See `ORGANIZATION.md` section 4.

## 5. Close out

- Run `python tools/check_structure.py`. Fix everything it reports.
- If the session added anything cross-cutting (an audit, a synthesis), put it in
  `cross_study_notes/`.
- If the study is finished or abandoned, set its status accordingly. Abandoned studies move to
  `archive/studies/<area>/<study>/` (keep the README, add why to `docs/CHANGELOG.md`).

## Status vocabulary (README and INDEX use exactly these)

`planned` → `running` → `scoring` → `complete`.  Off-path: `paused`, `superseded` (replaced by
a newer study; name it), `abandoned` (archived).
