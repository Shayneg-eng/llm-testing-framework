#!/usr/bin/env python3
"""One-shot migration: flat single-project layout -> studies/<area>/<study>/ layout.

Dry run (default, changes nothing):
    python tools/migrations/2026-09-25_restructure.py

Apply:
    python tools/migrations/2026-09-25_restructure.py --apply [--docs PATH_TO_NEW_DOCS_TREE]

What it does (see docs/CHANGELOG.md for the full old -> new map):
  1. Refuses to run if anything in the current tree is not accounted for by the mapping.
  2. Hashes every file, MOVES (never copies) runs/charts/notes/scripts into their study folders.
  3. Rewrites path handling inside the moved scripts (relative to each script's own location).
  4. Verifies every moved file arrived byte-identical (scripts excluded: edited on purpose),
     that all scripts compile, and that their path constants resolve.
  5. Optionally copies the new docs tree (README, ORGANIZATION, INDEX, docs/, tools/, templates/,
     study READMEs...) into place, never overwriting an existing file.
Nothing is deleted except empty legacy folders and __pycache__ (regenerable).
"""
import hashlib
import json
import py_compile
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = "--apply" in sys.argv
DOCS = None
if "--docs" in sys.argv:
    DOCS = Path(sys.argv[sys.argv.index("--docs") + 1]).resolve()

# ---------------------------------------------------------------- mapping
# study key -> (area, slug)
S = {
    "pipeline_baseline": ("bias", "pipeline_baseline"),
    "factorial": ("bias", "factorial"),
    "core_replication": ("bias", "core_replication"),
    "congruency": ("bias", "congruency"),
    "asymmetric": ("bias", "asymmetric"),
    "starting_position": ("bias", "starting_position"),
    "argument_type": ("bias", "argument_type"),
    "antisemitism": ("bias", "antisemitism"),
    "antisemitism_definitional": ("bias", "antisemitism_definitional"),
    "group_trope_bias": ("bias", "group_trope_bias"),
    "sequential_depth_probe": ("architecture", "sequential_depth_probe"),
}
RUN_DIRS = {  # old run folder -> study
    "runs_pipeline_baseline": "pipeline_baseline",
    "runs_factorial": "factorial",
    "runs_core_replication": "core_replication",
    "runs_congruency": "congruency",
    "runs_asymmetric": "asymmetric",
    "runs_starting_position": "starting_position",
    "runs_argument_type": "argument_type",
    "runs_antisemitism": "antisemitism",
    "runs_antisemitism_definitional": "antisemitism_definitional",
    "runs_group_trope_bias": "group_trope_bias",
    "runs_sequential_depth_probe": "sequential_depth_probe",
}
LEGACY_RUNS = {  # old folder -> (study, destination under the study)
    "runs_sequential_depth_probe_legacy_xor_state_2026_09_24":
        ("sequential_depth_probe", "runs_superseded/xor_state_2026-09-24"),
}
SHARED_SCRIPTS = {"seeds.py", "aggregate_replicates.py", "lexical_drift_scorer.py"}
SCRIPTS = {
    "pipeline_baseline": ["rspa_pipeline.py"],
    "factorial": ["rspa_factorial.py"],
    "core_replication": ["rspa_core_replication.py", "analyze_core_replication.py", "fill_core_hand_scores.py"],
    "congruency": ["rspa_congruency_study.py", "congruency_analysis.py"],
    "asymmetric": ["rspa_asymmetric_study.py", "asymmetric_analysis.py"],
    "starting_position": ["rspa_starting_position_study.py", "starting_position_analysis.py"],
    "argument_type": ["rspa_argument_type_study.py", "argument_type_analysis.py"],
    "antisemitism": ["rspa_antisemitism_study.py"],
    "antisemitism_definitional": ["rspa_antisemitism_definitional_study.py"],
    "group_trope_bias": ["rspa_group_trope_bias_study.py", "group_trope_bias_analysis.py",
                         "group_trope_bias_multimodel_analysis.py"],
    "sequential_depth_probe": ["sequential_depth_probe_study.py"],
}
CHART_PREFIX = [  # longest prefix first
    ("antisemitism_definitional_", "antisemitism_definitional"),
    ("group_trope_bias_", "group_trope_bias"),
    ("starting_position_", "starting_position"),
    ("core_replication_", "core_replication"),
    ("argument_type_", "argument_type"),
    ("asymmetric_", "asymmetric"),
    ("congruency_", "congruency"),
]
CHART_EXACT = {
    "all_four_cells_memory_factorial.png": "factorial",
    "hand_vs_lexical_scorer_comparison.png": "factorial",
    "stateful_vs_stateless_handscored.png": "factorial",
    "cell1_vs_cell4_memory_matters.png": "factorial",
}
NOTES = {  # filename in "current research direction" -> study (or None = cross_study_notes)
    "2026-09-10.md": None,
    "2026-09-10-followup.md": "factorial",
    "2026-09-10-followup2.md": "factorial",
    "2026-09-10-followup3.md": "factorial",
    "2026-09-11-core-replication.md": "core_replication",
    "2026-09-11-seed-dependent-asymmetry.md": "core_replication",
    "2026-09-11-congruency-pivot.md": "congruency",
    "2026-09-11-congruency-results.md": "congruency",
    "2026-09-12-starting-position-null.md": "starting_position",
    "2026-09-14-asymmetric-design-results.md": "asymmetric",
    "2026-09-15-argument-type-results.md": "argument_type",
    "2026-09-15-starting-position-results.md": "starting_position",
}
RENAME_NOTES = {"2026-09-10.md": "2026-09-10-research-direction.md"}  # so it matches YYYY-MM-DD-<topic>.md
OLD_TOP_FILES = {"README.md", "ORGANIZATION.md", "requirements.txt"}
OLD_TOP_DIRS = set(RUN_DIRS) | set(LEGACY_RUNS) | {"scripts", "analysis_charts", "current research direction", "results"}
NEW_TOP = {"studies", "shared", "cross_study_notes", "docs", "templates", "tools", "archive", "scratch"}
IGNORE = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"}


def sd(study):
    a, s = S[study]
    return ROOT / "studies" / a / s


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- planning
moves = []   # (src Path, dst Path)
edits = {}   # dst script Path -> kind ("study" | "shared")
errors = []

top = [c for c in ROOT.iterdir() if c.name not in IGNORE]
for c in top:
    if c.is_file() and c.name not in OLD_TOP_FILES and c.name != "INDEX.md":
        errors.append(f"unmapped top-level file: {c.name}")
    if c.is_dir() and c.name not in OLD_TOP_DIRS and c.name not in NEW_TOP:
        errors.append(f"unmapped top-level folder: {c.name}")

for old, study in RUN_DIRS.items():
    if (ROOT / old).is_dir():
        moves.append((ROOT / old, sd(study) / "runs"))
for old, (study, sub) in LEGACY_RUNS.items():
    if (ROOT / old).is_dir():
        moves.append((ROOT / old, sd(study) / sub))

scripts_dir = ROOT / "scripts"
if scripts_dir.is_dir():
    claimed = set(SHARED_SCRIPTS)
    for study, files in SCRIPTS.items():
        claimed |= set(files)
    for c in sorted(scripts_dir.iterdir()):
        if c.name in IGNORE or c.name == "__pycache__":
            continue
        if c.name in SHARED_SCRIPTS:
            moves.append((c, ROOT / "shared" / c.name))
            edits[ROOT / "shared" / c.name] = "shared"
            continue
        owner = next((st for st, fs in SCRIPTS.items() if c.name in fs), None)
        if owner is None:
            errors.append(f"unmapped script: scripts/{c.name}")
        else:
            dst = sd(owner) / "scripts" / c.name
            moves.append((c, dst))
            edits[dst] = "study"

charts_dir = ROOT / "analysis_charts"
if charts_dir.is_dir():
    for c in sorted(charts_dir.iterdir()):
        if c.name in IGNORE:
            continue
        owner = CHART_EXACT.get(c.name) or next((st for pre, st in CHART_PREFIX if c.name.startswith(pre)), None)
        if owner is None:
            errors.append(f"unmapped chart: analysis_charts/{c.name}")
        else:
            moves.append((c, sd(owner) / "charts" / c.name))

notes_dir = ROOT / "current research direction"
if notes_dir.is_dir():
    for c in sorted(notes_dir.iterdir()):
        if c.name in IGNORE:
            continue
        if c.name not in NOTES:
            errors.append(f"unmapped note: current research direction/{c.name}")
        else:
            owner = NOTES[c.name]
            newname = RENAME_NOTES.get(c.name, c.name)
            dst = (ROOT / "cross_study_notes" / newname) if owner is None else (sd(owner) / "notes" / newname)
            moves.append((c, dst))

# old top-level docs
if (ROOT / "README.md").exists() and "RSPA mockup" in (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore"):
    moves.append((ROOT / "README.md", sd("pipeline_baseline") / "design" / "original_mockup_README.md"))
    edits[sd("pipeline_baseline") / "design" / "original_mockup_README.md"] = "readme"
if (ROOT / "ORGANIZATION.md").exists() and "Directory organization" in (ROOT / "ORGANIZATION.md").read_text(encoding="utf-8", errors="ignore"):
    moves.append((ROOT / "ORGANIZATION.md", ROOT / "archive" / "ORGANIZATION_2026-09-20_pre-restructure.md"))

for src, dst in moves:
    if dst.exists():
        errors.append(f"destination already exists: {dst.relative_to(ROOT)}")

print(f"root: {ROOT}")
print(f"planned moves: {len(moves)} top-level items ({'APPLY' if APPLY else 'dry run'})")
for src, dst in moves:
    kind = "dir " if src.is_dir() else "file"
    print(f"  {kind} {src.relative_to(ROOT).as_posix()}  ->  {dst.relative_to(ROOT).as_posix()}")
if errors:
    print("\nBLOCKING PROBLEMS (nothing was changed):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
if not APPLY:
    print("\nDry run OK. Re-run with --apply to perform the migration.")
    sys.exit(0)

# ---------------------------------------------------------------- manifest before
before = {}
for p in ROOT.rglob("*"):
    if p.is_file() and "__pycache__" not in p.parts and p.name not in IGNORE:
        before[p.relative_to(ROOT).as_posix()] = sha(p)
print(f"\nhashed {len(before)} files before moving")

# ---------------------------------------------------------------- do the moves
file_moves = []  # (old_rel, new_rel) for every individual file
for src, dst in moves:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        for f in src.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                file_moves.append((f.relative_to(ROOT).as_posix(), (dst / f.relative_to(src)).relative_to(ROOT).as_posix()))
    else:
        file_moves.append((src.relative_to(ROOT).as_posix(), dst.relative_to(ROOT).as_posix()))
    shutil.move(str(src), str(dst))

# make sure every study has the standard skeleton
for study in S:
    for d in ("scripts", "runs", "charts", "notes"):
        (sd(study) / d).mkdir(parents=True, exist_ok=True)
for d in ("shared", "cross_study_notes", "archive", "scratch", "docs", "templates", "tools", "results"):
    (ROOT / d).mkdir(exist_ok=True)
(ROOT / "studies" / "teamwork").mkdir(exist_ok=True)

# ---------------------------------------------------------------- rewrite script paths
NAMES = "|".join(sorted(map(re.escape, list(RUN_DIRS) + ["runs_factorial", "runs_core_replication"]), key=len, reverse=True))


def rewrite(path, kind):
    raw = path.read_bytes().decode("utf-8")
    t = raw
    if kind == "readme":
        t = t.replace("./runs_pipeline_baseline/", "../runs/").replace("runs_pipeline_baseline/", "runs/")
        t = t.replace("pip install -r requirements.txt\npython rspa_pipeline.py",
                      "pip install -r ../../../../requirements.txt\npython ../scripts/rspa_pipeline.py")
        t = t.replace("\r\npython rspa_pipeline.py", "\r\npython ../scripts/rspa_pipeline.py")
        t = "> Moved here from the old top-level README on 2026-09-25 (see docs/CHANGELOG.md). Paths below are relative to this file.\n\n" + t
    elif kind == "shared":
        t = t.replace('Path(__file__).parent.parent / "runs_factorial"',
                      'Path(__file__).resolve().parent.parent / "studies" / "bias" / "factorial" / "runs"')
        t = t.replace('Path(__file__).parent.parent / "runs_core_replication"',
                      'Path(__file__).resolve().parent.parent / "studies" / "bias" / "core_replication" / "runs"')
        t = t.replace("runs_factorial/", "studies/bias/factorial/runs/")
        t = t.replace("runs_core_replication/", "studies/bias/core_replication/runs/")
        t = t.replace("analysis_charts/", "studies/<area>/<study>/charts/")
    else:  # study script
        if path.name == "asymmetric_analysis.py":
            t = t.replace('Path(__file__).parent.parent / "runs_congruency"',
                          'Path(__file__).resolve().parents[4] / "studies" / "bias" / "congruency" / "runs"')
        if path.name.startswith("rspa_asymmetric") or path.name == "asymmetric_analysis.py":
            t = t.replace("runs_congruency/", "studies/bias/congruency/runs/")
        t = re.sub(r'Path\(__file__\)\.parent\.parent / "(?:%s)"' % NAMES,
                   'Path(__file__).resolve().parent.parent / "runs"', t)
        t = t.replace('Path(__file__).parent.parent / "analysis_charts"',
                      'Path(__file__).resolve().parent.parent / "charts"')
        t = t.replace("HERE = Path(__file__).parent\n", "HERE = Path(__file__).resolve().parent\n")
        t = t.replace("HERE = Path(__file__).parent\r\n", "HERE = Path(__file__).resolve().parent\r\n")
        t = re.sub(r'HERE\.parent / "(?:%s)"' % NAMES, 'HERE.parent / "runs"', t)
        t = t.replace('HERE.parent / "analysis_charts"', 'HERE.parent / "charts"')
        t = re.sub(r"(?:\./)?(?:%s)/" % NAMES, "runs/", t)
        t = t.replace("analysis_charts/", "charts/")
        # seeds bootstrap
        nl = "\r\n" if "\r\n" in t else "\n"
        boot = nl.join([
            "import sys as _sys",
            "from pathlib import Path as _Path",
            '_sys.path.insert(0, str(_Path(__file__).resolve().parents[4] / "shared"))  # shared/ (seeds etc.)',
            ""])
        t = re.sub(r"^(from seeds import )", lambda m: boot + m.group(1), t, count=1, flags=re.M) if "from seeds import" in t else t
    if t != raw:
        path.write_bytes(t.encode("utf-8"))
    return t != raw


changed = [p.relative_to(ROOT).as_posix() for p, k in edits.items() if p.exists() and rewrite(p, k)]
print(f"rewrote paths in {len(changed)} files")

# ---------------------------------------------------------------- verification
problems = []
after = {}
for p in ROOT.rglob("*"):
    if p.is_file() and "__pycache__" not in p.parts and p.name not in IGNORE:
        after[p.relative_to(ROOT).as_posix()] = sha(p)

edited_new = set(changed)
for old_rel, new_rel in file_moves:
    if new_rel not in after:
        problems.append(f"missing after move: {new_rel}")
    elif new_rel not in edited_new and after[new_rel] != before[old_rel]:
        problems.append(f"content changed: {old_rel} -> {new_rel}")
print(f"verified {len(file_moves)} moved files")

for p, kind in edits.items():
    if kind == "readme" or not p.exists() or p.suffix != ".py":
        continue
    try:
        py_compile.compile(str(p), doraise=True, cfile=str(ROOT / "scratch" / "_verify.pyc"))
    except py_compile.PyCompileError as e:
        problems.append(f"does not compile: {p.relative_to(ROOT)}: {e}")
    text = p.read_text(encoding="utf-8")
    for m in re.finditer(r'(?:%s)|analysis_charts' % NAMES, text):
        line = text[:m.start()].count("\n") + 1
        problems.append(f"leftover old path in {p.relative_to(ROOT)}:{line}: {m.group(0)}")
    # evaluate top-level path constants
    ns = {"__file__": str(p), "Path": Path}
    for line in text.splitlines():
        if re.match(r"^(HERE|[A-Z_]*DIR)\s*=\s*(Path\(__file__\)|HERE)", line):
            try:
                exec(line, ns)
            except Exception as e:
                problems.append(f"cannot evaluate '{line.strip()}' in {p.name}: {e}")
    for k, v in ns.items():
        if isinstance(v, Path) and k.endswith("DIR") and k not in {"CHARTS_DIR", "OUTPUT_DIR"}:
            if not v.exists():
                problems.append(f"{p.relative_to(ROOT)}: {k} -> {v} does not exist")
    if "from seeds import" in text and not (ROOT / "shared" / "seeds.py").exists():
        problems.append(f"{p.name} imports seeds but shared/seeds.py is missing")
verify_pyc = ROOT / "scratch" / "_verify.pyc"
if verify_pyc.exists():
    verify_pyc.unlink()

# ---------------------------------------------------------------- tidy legacy folders
for d in ("scripts", "analysis_charts", "current research direction"):
    p = ROOT / d
    if p.is_dir():
        cache = p / "__pycache__"
        if cache.is_dir():
            try:
                shutil.rmtree(cache)
            except OSError as e:
                print(f"note: could not remove {cache}: {e}")
        left = [c for c in p.iterdir() if c.name not in IGNORE]
        if left:
            problems.append(f"legacy folder not empty: {d}: {[c.name for c in left]}")
        else:
            try:
                p.rmdir()
            except OSError as e:
                print(f"note: empty legacy folder '{d}' could not be removed ({e}); delete it by hand")

# ---------------------------------------------------------------- docs
if DOCS:
    copied = 0
    for f in DOCS.rglob("*"):
        if f.is_file():
            target = ROOT / f.relative_to(DOCS)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            copied += 1
    print(f"copied {copied} new doc/tool files from {DOCS}")

json.dump({"before": before, "moves": file_moves}, open(ROOT / "scratch" / "migration_2026-09-25.json", "w"))
print("\nRESULT:", "OK" if not problems else f"{len(problems)} PROBLEMS")
for p in problems:
    print("  -", p)
sys.exit(1 if problems else 0)
