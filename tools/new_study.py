#!/usr/bin/env python3
"""Scaffold a new study.

    python tools/new_study.py <area> <study_slug> "<one-line research question>"

Copies templates/study/ to studies/<area>/<study_slug>/, fills the README, assigns the next
study ID and inserts a row in INDEX.md. See docs/ADDING_A_STUDY.md.
"""
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MARKER = "<!-- NEW STUDIES ARE INSERTED ABOVE THIS LINE by tools/new_study.py -->"


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    area, slug, question = sys.argv[1], sys.argv[2], sys.argv[3]
    for label, val in (("area", area), ("study slug", slug)):
        if not SLUG_RE.match(val):
            print(f"error: {label} '{val}' must be lowercase snake_case")
            return 2
    dest = ROOT / "studies" / area / slug
    if dest.exists():
        print(f"error: {dest} already exists")
        return 2
    index = ROOT / "INDEX.md"
    text = index.read_text(encoding="utf-8")
    if MARKER not in text:
        print("error: INDEX.md is missing the insertion marker")
        return 2
    ids = [int(x) for x in re.findall(r"\|\s*S(\d{3})\s*\|", text)]
    new_id = f"S{(max(ids) + 1) if ids else 1:03d}"
    if slug in re.findall(r"\|\s*S\d{3}\s*\|\s*([a-z0-9_]+)\s*\|", text):
        print(f"error: slug '{slug}' already exists in INDEX.md (is this really a new study? see ADDING_A_STUDY.md)")
        return 2

    new_area = not (ROOT / "studies" / area).exists()
    shutil.copytree(ROOT / "templates" / "study", dest)
    title = slug.replace("_", " ").capitalize()
    subs = {"{{TITLE}}": title, "{{ID}}": new_id, "{{SLUG}}": slug, "{{AREA}}": area,
            "{{DATE}}": date.today().isoformat(), "{{QUESTION}}": question}
    for f in list(dest.rglob("*")):
        if f.is_file() and f.suffix in {".md", ".template"}:
            t = f.read_text(encoding="utf-8")
            for k, v in subs.items():
                t = t.replace(k, v)
            f.write_text(t, encoding="utf-8")
        if f.is_file() and "STUDY_SLUG" in f.name:
            target = f.with_name(f.name.replace("STUDY_SLUG", slug).replace(".template", ""))
            f.rename(target)

    row = (f"| {new_id} | {slug} | {area} | planned | {date.today().isoformat()} | (tbd) | "
           f"{question} | (none yet) | `studies/{area}/{slug}` |")
    index.write_text(text.replace(MARKER, row + "\n" + MARKER), encoding="utf-8")

    print(f"created {dest.relative_to(ROOT)}  ({new_id})")
    print("added row to INDEX.md")
    if new_area:
        print(f"NOTE: '{area}' is a new area. Add a row for it to the area table in ORGANIZATION.md section 2.")
    print("next: write scripts/, run, score, then notes/ + README + INDEX row (docs/ADDING_A_STUDY.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
