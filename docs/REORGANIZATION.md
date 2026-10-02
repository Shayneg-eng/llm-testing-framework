# When and how to reorganize

The structure is designed so most growth needs no reorganization: a new study is a new folder,
a new area is a new folder. Reorganize only when one of the triggers below fires, and do it
deliberately, not opportunistically.

## Routine hygiene (every session that adds files)

1. Put each new file in its home when you create it (decision list in `ORGANIZATION.md` §5).
2. Run `python tools/check_structure.py`. It must end with `0 problems`.
3. If you touched a study's status or results, update its README and its `INDEX.md` row.
4. `__pycache__` folders are ignored and safe to delete; never treat them as content.

## Scheduled hygiene

| When | Do |
|---|---|
| Before starting any new study | Skim `INDEX.md` for overlap; run the checker |
| Monthly (first working day) | Run the checker; clear `scratch/` items older than 30 days; check that every `running` study is still actually running |
| After finishing a study | README + INDEX final; decide whether a `results/` package is warranted; archive nothing yet |
| Quarterly | Read `INDEX.md` top to bottom; archive `abandoned` studies, mark `superseded` ones; check if any trigger below is close |

## Triggers

**T1: Loose files.** Anything at the top level that is not on the allowed list, or any file
outside the anatomy of its study folder. *Action:* route it with the decision list. Do this
immediately; it is never a "later" job.

**T2: A `runs/` folder gets unwieldy.** More than ~500 files, or more than ~200 MB.
*Action:* split by model or phase into subfolders (`runs/<model>/`, `runs/phase2/`), update the
study's scripts to write to and read from the subfolders, and note the new layout in the README.
Or, for finished studies, zip old replicate blocks into `runs_superseded/`-style archives. Do
not split at a lower threshold; flat is easier to script against.

**T3: An area gets crowded.** More than ~12 studies in one area, or two clearly separate
sub-themes. *Action:* introduce sub-areas by promoting the sub-theme to its own area
(`studies/bias/` → `studies/bias/` + `studies/group_bias/`), or a family folder if studies
share a harness. Update `INDEX.md` paths, the area table, and every script's `ROOT / "studies" /
...` cross-references (grep for the old path).

**T4: A second study needs code from a first.** *Action:* move that code into `shared/`,
update both studies' imports, note it in the CHANGELOG. Do not copy.

**T5: `notes/` or `charts/` gets long.** More than ~40 files. *Action:* for `notes/`, add
`notes/<year>/` folders or fold superseded notes into a single "state of the study" README
section; for `charts/`, group by phase (`charts/phase1/`).

**T6: Naming drift.** Files or folders that break `docs/CONVENTIONS.md`. *Action:* rename in
one batch, update references (grep), record in the CHANGELOG.

**T7: A convention stops fitting reality.** You keep bending a rule. *Action:* change the
rule (in `ORGANIZATION.md` / `CONVENTIONS.md`) on purpose, apply it everywhere in one pass,
and record it in the CHANGELOG. A rule that everyone works around is worse than no rule.

**T8: The top level wants a new folder.** Almost always wrong. *Action:* look for the existing
home first (decision list). If truly none fits, discuss and add it to `ORGANIZATION.md` §1 and
the checker's allow-list in the same edit.

## Procedure for a structural change

1. Write down what is moving where (a short mapping table) before touching anything.
2. Take a manifest first: `python tools/check_structure.py --manifest scratch/manifest_before.json`
   records every file's hash.
3. Move with `mv`/`shutil.move`, never copy-then-delete. Do not overwrite anything.
4. Fix references: scripts' paths, README links, notes that cite paths, `INDEX.md`.
5. Verify: run the checker, run `--manifest scratch/manifest_after.json`, and confirm every file
   in the "before" manifest exists in "after" (path may change, hash must not).
6. Record it in `docs/CHANGELOG.md`: date, what moved, why, which trigger.
7. If it was a big one-off, keep the script in `tools/migrations/`.

## What never gets reorganized away

Raw run data and dated write-ups are the research record. They can be moved, split, zipped, or
archived. They are never deleted, edited to "tidy" them, or merged into summaries that replace
them.
