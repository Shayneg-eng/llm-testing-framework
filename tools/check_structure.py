#!/usr/bin/env python3
"""Health check for the LLM Testing directory.

    python tools/check_structure.py                     # run all checks
    python tools/check_structure.py --manifest FILE     # write a sha256 manifest of every file
    python tools/check_structure.py --compare A B       # verify every hash in manifest A exists in B

Enforces ORGANIZATION.md. Exit code 0 = no problems (warnings are allowed), 1 = problems.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_TOP = {
    "README.md", "ORGANIZATION.md", "INDEX.md", "requirements.txt",
    "studies", "shared", "results", "cross_study_notes",
    "docs", "templates", "tools", "archive", "scratch",
}
IGNORE_NAMES = {"__pycache__", ".git", ".gitignore", ".gitkeep", ".DS_Store", "Thumbs.db", ".idea", ".vscode", "desktop.ini"}
STUDY_DIRS = {"scripts", "runs", "charts", "notes", "design"}
STUDY_EXTRA_PREFIX = "runs_superseded"
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NOTE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")
CHART_EXT = {".png", ".svg", ".pdf", ".jpg", ".jpeg", ".gif", ".html"}
RUN_MAX_FILES = 500
OTHER_MAX_FILES = 40
SCRATCH_MAX_AGE_DAYS = 30

problems, warnings = [], []


def problem(msg):
    problems.append(msg)


def warn(msg):
    warnings.append(msg)


def rel(p):
    return p.relative_to(ROOT).as_posix()


def visible(p):
    return [c for c in p.iterdir() if c.name not in IGNORE_NAMES]


def index_paths():
    idx = ROOT / "INDEX.md"
    if not idx.exists():
        return set()
    return set(re.findall(r"`(studies/[a-z0-9_]+/[a-z0-9_]+)`", idx.read_text(encoding="utf-8")))


def check_top():
    for c in visible(ROOT):
        if c.name not in ALLOWED_TOP:
            problem(f"top level: '{c.name}' is not allowed here (route it with ORGANIZATION.md section 5)")
    for name in ("README.md", "ORGANIZATION.md", "INDEX.md"):
        if not (ROOT / name).exists():
            problem(f"top level: missing {name}")


def check_study(study: Path):
    s = rel(study)
    if not SLUG_RE.match(study.name):
        problem(f"{s}: study slug must be lowercase snake_case")
    if not (study / "README.md").exists():
        problem(f"{s}: missing README.md")
    for c in visible(study):
        if c.is_file():
            if c.name != "README.md":
                problem(f"{s}: stray file '{c.name}' (only README.md may sit at the study root)")
        elif c.name in STUDY_DIRS or c.name == STUDY_EXTRA_PREFIX:
            pass
        else:
            problem(f"{s}: unexpected folder '{c.name}' (allowed: {sorted(STUDY_DIRS)} + runs_superseded)")
    for d in ("scripts", "runs", "charts", "notes"):
        if not (study / d).is_dir():
            warn(f"{s}: no {d}/ folder yet")
    # scripts: code only, no pycache, no subfolders
    sc = study / "scripts"
    if sc.is_dir():
        for c in visible(sc):
            if c.is_dir():
                problem(f"{rel(c)}: scripts/ must be flat")
            elif c.suffix not in {".py", ".template", ".sh", ".md", ".txt"}:
                problem(f"{rel(c)}: unexpected file type in scripts/")
    # charts
    ch = study / "charts"
    if ch.is_dir():
        for c in ch.rglob("*"):
            if c.is_file() and c.name not in IGNORE_NAMES and c.suffix.lower() not in CHART_EXT:
                problem(f"{rel(c)}: charts/ holds figures only")
        n = sum(1 for c in ch.rglob("*") if c.is_file())
        if n > OTHER_MAX_FILES:
            warn(f"{rel(ch)}: {n} files (trigger T5: group by phase)")
    # notes
    nt = study / "notes"
    if nt.is_dir():
        for c in nt.rglob("*"):
            if c.is_file() and c.name not in IGNORE_NAMES:
                if c.suffix != ".md" or not NOTE_RE.match(c.name):
                    problem(f"{rel(c)}: notes must be named YYYY-MM-DD-<topic>.md")
        n = sum(1 for c in nt.rglob("*") if c.is_file())
        if n > OTHER_MAX_FILES:
            warn(f"{rel(nt)}: {n} files (trigger T5)")
    # runs
    rn = study / "runs"
    if rn.is_dir():
        for c in rn.rglob("*"):
            if c.is_file() and c.name not in IGNORE_NAMES and c.suffix.lower() in CHART_EXT - {".html"}:
                problem(f"{rel(c)}: figures do not belong in runs/ (move to charts/)")
        n = sum(1 for c in rn.rglob("*") if c.is_file())
        if n > RUN_MAX_FILES:
            warn(f"{rel(rn)}: {n} files (trigger T2: split by model/phase)")


def check_studies():
    base = ROOT / "studies"
    if not base.is_dir():
        problem("missing studies/")
        return
    found = set()
    for area in visible(base):
        if area.is_file():
            problem(f"studies/: stray file '{area.name}'")
            continue
        if not SLUG_RE.match(area.name):
            problem(f"{rel(area)}: area name must be lowercase snake_case")
        for study in visible(area):
            if study.is_file():
                problem(f"{rel(area)}: stray file '{study.name}' (studies live in folders)")
                continue
            found.add(rel(study))
            check_study(study)
    indexed = index_paths()
    for f in sorted(found - indexed):
        problem(f"{f}: study folder is not registered in INDEX.md")
    for i in sorted(indexed - found):
        problem(f"INDEX.md: row points at '{i}' which does not exist")
    org = (ROOT / "ORGANIZATION.md")
    if org.exists():
        text = org.read_text(encoding="utf-8")
        for area in visible(base):
            if area.is_dir() and f"`{area.name}`" not in text:
                warn(f"area '{area.name}' is not listed in ORGANIZATION.md section 2")


def check_misc():
    for name in ("shared", "cross_study_notes", "archive", "scratch", "docs", "templates", "tools", "results"):
        if not (ROOT / name).is_dir():
            problem(f"missing top-level folder {name}/")
    for c in (ROOT / "cross_study_notes").glob("*") if (ROOT / "cross_study_notes").is_dir() else []:
        if c.name in IGNORE_NAMES:
            continue
        if c.is_dir() or not NOTE_RE.match(c.name):
            problem(f"{rel(c)}: cross_study_notes holds YYYY-MM-DD-<topic>.md files only")
    res = ROOT / "results"
    if res.is_dir():
        for c in visible(res):
            if c.is_file():
                problem(f"{rel(c)}: results/ holds package folders only")
            elif not (c / "README.md").exists():
                problem(f"{rel(c)}: result package needs a README.md")
    now = time.time()
    scr = ROOT / "scratch"
    if scr.is_dir():
        for c in visible(scr):
            age = (now - c.stat().st_mtime) / 86400
            if age > SCRATCH_MAX_AGE_DAYS:
                warn(f"{rel(c)}: in scratch/ for {age:.0f} days; promote it or clear it")


def manifest(path_out):
    m = {}
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and "scratch" not in p.parts:
            m[rel(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    Path(path_out).write_text(json.dumps(m, indent=0), encoding="utf-8")
    print(f"manifest: {len(m)} files -> {path_out}")


def compare(a, b):
    ma = json.loads(Path(a).read_text(encoding="utf-8"))
    mb = json.loads(Path(b).read_text(encoding="utf-8"))
    after = {}
    for path, h in mb.items():
        after.setdefault(h, []).append(path)
    lost = [p for p, h in ma.items() if h not in after]
    print(f"before: {len(ma)} files, after: {len(mb)} files, missing content: {len(lost)}")
    for p in lost[:50]:
        print("  MISSING (hash not found after):", p)
    return 0 if not lost else 1


def main():
    args = sys.argv[1:]
    if args and args[0] == "--manifest":
        manifest(args[1])
        return 0
    if args and args[0] == "--compare":
        return compare(args[1], args[2])
    check_top()
    check_studies()
    check_misc()
    for w in warnings:
        print("warning:", w)
    for p in problems:
        print("PROBLEM:", p)
    print(f"\n{len(problems)} problems, {len(warnings)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
