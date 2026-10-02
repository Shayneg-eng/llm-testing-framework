"""
Aggregate replicate reports from rspa_factorial.py into mean +/- spread per
(model, cell, trial, round).

Two kinds of numbers get aggregated:
  1. Mechanical metrics that exist automatically for every turn: word_count,
     and the rates of cap_exceeded / stagnation_flag / refusal_flag /
     duplicate_block_flag across replicates. These need no hand-scoring.
  2. drift_score (-10..+10): starts as null in every turn rspa_factorial.py
     writes. Fill these in by hand (open the transcript_factorial_*.md files
     and score each round, same -10/0/+10 scale used for the earlier
     Drift Under Attack charts) directly in the JSON report files, then
     re-run this script -- it averages whichever turns have a non-null score
     and reports how many of the 5 replicates were actually scored, so a
     partially-scored run is still usable and honestly labeled as partial.

Usage:
    python aggregate_replicates.py <topic_key> <seed_key> <model>

Example:
    python aggregate_replicates.py abortion_policy 0 Gemini-3.5-Flash-Lite

Output:
    ./studies/bias/factorial/runs/aggregate_<topic_key>_<seed_key>_<model>.json
    plus a console summary table.
"""

import json
import sys
import statistics
from pathlib import Path

FACTORIAL_DIR = Path(__file__).resolve().parent.parent / "studies" / "bias" / "factorial" / "runs"
CORE_DIR = Path(__file__).resolve().parent.parent / "studies" / "bias" / "core_replication" / "runs"


def dir_for_prefix(prefix):
    """studies/bias/factorial/runs/ for rspa_factorial.py output, studies/bias/core_replication/runs/ for rspa_core_replication.py output."""
    return FACTORIAL_DIR if prefix == "rspa_factorial" else CORE_DIR


def load_replicates(topic_key, seed_key, model, prefix="rspa_factorial"):
    """prefix: "rspa_factorial" (default, matches rspa_factorial.py's 4-cell output) or
    "rspa_core" (matches rspa_core_replication.py's Cell1+Cell4-only output)."""
    output_dir = dir_for_prefix(prefix)
    safe_name = model.replace("/", "_")
    safe_seed = seed_key.replace("+", "plus_").replace("/", "_")
    pattern = f"{prefix}_{topic_key}_{safe_seed}_{safe_name}_rep*.json"
    paths = sorted(output_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(
            f"No replicate files matched {pattern} in {output_dir} -- "
            f"check topic_key/seed_key/model/prefix match what the run script produced "
            f"(prefix is 'rspa_factorial' for rspa_factorial.py, 'rspa_core' for rspa_core_replication.py)."
        )
    reports = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            reports.append(json.load(f))
    return reports, paths


def mean_sd(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0, "mean": None, "sd": None}
    if len(values) == 1:
        return {"n": 1, "mean": values[0], "sd": None}
    return {"n": len(values), "mean": statistics.mean(values), "sd": statistics.stdev(values)}


def rate(bools):
    bools = [b for b in bools if b is not None]
    if not bools:
        return {"n": 0, "rate": None}
    return {"n": len(bools), "rate": sum(1 for b in bools if b) / len(bools)}


def aggregate(reports):
    """reports: list of the per-replicate JSON dicts (same topic/seed/model,
    different replicate). Returns a nested structure keyed by
    cell_tag -> trial_key -> round -> stats."""
    n_reps = len(reports)
    cell_tags = reports[0]["config"]["cells"]
    rounds = reports[0]["config"]["rounds"]

    out = {"n_replicates": n_reps, "cells": {}}

    for cell_idx, tag in enumerate(cell_tags):
        out["cells"][tag] = {}
        for trial_key in ("trial_1", "trial_2"):
            out["cells"][tag][trial_key] = {}
            for round_num in range(1, rounds + 1):
                word_counts, drift_scores = [], []
                cap_flags, stag_flags, refusal_flags, dup_flags = [], [], [], []

                for report in reports:
                    cell = report["cells"][cell_idx]
                    assert cell_tag_matches(cell, tag), (
                        f"Cell order mismatch across replicates -- replicate reports must list "
                        f"cells in the same order. Expected {tag} at index {cell_idx}."
                    )
                    turns = cell[trial_key]["turns"]
                    turn = next((t for t in turns if t["round"] == round_num), None)
                    if turn is None:
                        continue  # this replicate's trial ended early (e.g. a structural refusal)
                    word_counts.append(turn.get("word_count"))
                    drift_scores.append(turn.get("drift_score"))
                    cap_flags.append(turn.get("cap_exceeded"))
                    stag_flags.append(turn.get("stagnation_flag"))
                    refusal_flags.append(turn.get("refusal_flag"))
                    dup_flags.append(turn.get("duplicate_block_flag"))

                out["cells"][tag][trial_key][round_num] = {
                    "word_count": mean_sd(word_counts),
                    "drift_score": mean_sd(drift_scores),
                    "cap_exceeded_rate": rate(cap_flags),
                    "stagnation_rate": rate(stag_flags),
                    "refusal_rate": rate(refusal_flags),
                    "duplicate_block_rate": rate(dup_flags),
                    "replicates_present": len(word_counts),
                }
    return out


def cell_tag_matches(cell, tag):
    return f"atk-{cell['attacker_mode']}_def-{cell['defender_mode']}" == tag


def print_summary(agg, topic_key, model):
    print(f"\n=== Aggregate: {topic_key} / {model} -- {agg['n_replicates']} replicate(s) ===\n")
    any_scored = False
    for tag, trials in agg["cells"].items():
        print(f"-- {tag} --")
        for trial_key, rounds in trials.items():
            row = []
            for round_num, stats in rounds.items():
                ds = stats["drift_score"]
                wc = stats["word_count"]
                if ds["n"] > 0:
                    any_scored = True
                    ds_str = f"{ds['mean']:+.1f}n{ds['n']}" + (f"(sd{ds['sd']:.1f})" if ds["sd"] is not None else "")
                else:
                    ds_str = "unscored"
                flags = []
                if stats["refusal_rate"]["rate"]:
                    flags.append(f"refusal={stats['refusal_rate']['rate']:.0%}")
                if stats["cap_exceeded_rate"]["rate"]:
                    flags.append(f"cap={stats['cap_exceeded_rate']['rate']:.0%}")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                row.append(f"R{round_num}: drift={ds_str} wc={wc['mean']:.0f}n{wc['n']}{flag_str}")
            print(f"  {trial_key}: " + "  ".join(row))
        print()

    if not any_scored:
        print("NOTE: no drift_score values are populated yet (all turns show 'unscored'). "
              "Hand-score the transcript_factorial_*_rep*.md files' rounds on the -10..+10 scale, "
              "write the scores into the corresponding rspa_factorial_*_rep*.json turn objects' "
              "'drift_score' field, then re-run this script.")


def main():
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        print("\nOptional 4th argument: filename prefix, default 'rspa_factorial'. "
              "Pass 'rspa_core' for rspa_core_replication.py output.")
        sys.exit(1)
    topic_key, seed_key, model = sys.argv[1], sys.argv[2], sys.argv[3]
    prefix = sys.argv[4] if len(sys.argv) == 5 else "rspa_factorial"

    reports, paths = load_replicates(topic_key, seed_key, model, prefix)
    print(f"Loaded {len(reports)} replicate file(s) (prefix='{prefix}'):")
    for p in paths:
        print(f"  {p.name}")

    agg = aggregate(reports)
    print_summary(agg, topic_key, model)

    safe_name = model.replace("/", "_")
    safe_seed = seed_key.replace("+", "plus_").replace("/", "_")
    # Keep the original filename (no prefix in the name) for the default "rspa_factorial"
    # prefix so this doesn't rename the aggregate file already referenced in past notes;
    # non-default prefixes (e.g. "rspa_core") get their own distinctly-named output so the
    # two never collide.
    out_name = (f"aggregate_{topic_key}_{safe_seed}_{safe_name}.json" if prefix == "rspa_factorial"
                else f"aggregate_{prefix}_{topic_key}_{safe_seed}_{safe_name}.json")
    out_path = dir_for_prefix(prefix) / out_name
    out_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> wrote {out_path}")


if __name__ == "__main__":
    main()
