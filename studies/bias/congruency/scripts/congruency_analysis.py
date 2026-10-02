"""
Analysis for the RSPA congruency study (rspa_congruency_study.py output).

Answers: does an attacker arguing FROM THE SAME side as the defender's
starting lean ("congruent") push the defender further in that direction,
or does an attacker arguing from the OPPOSITE side ("incongruent") do that
instead (the backfire/entrenchment pattern seen in the seed +b pilot read)?

Reads every rspa_congruency_<topic>_<seed>_<model>_rep*.json in
runs/, requires drift_score_hand to be filled in (signed,
-10..+10) on every turn -- turns still null are reported as missing and
excluded, not silently treated as 0.

Usage: python congruency_analysis.py [topic_key] [model]
Defaults: topic_key=abortion_policy, model=GPT-OSS-120B-CS
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)


def load_reports(topic_key, model):
    safe_name = model.replace("/", "_")
    reports = []
    for seed_key in ("+a", "+b"):
        safe_seed = seed_key.replace("+", "plus_")
        pattern = f"rspa_congruency_{topic_key}_{safe_seed}_{safe_name}_rep*.json"
        files = sorted(RUNS_DIR.glob(pattern))
        if not files:
            print(f"WARNING: no files matched {pattern} in {RUNS_DIR}")
        for f in files:
            reports.append(json.loads(f.read_text(encoding="utf-8")))
    return reports


def collect_by_round(reports):
    """
    Returns: {congruency: {round: [signed drift values across all reps/seeds]}}
    Also returns a count of turns still missing drift_score_hand (None),
    which are excluded rather than treated as 0.
    """
    by_round = defaultdict(lambda: defaultdict(list))
    missing = 0
    total = 0
    for report in reports:
        for trial_key in ("trial_A", "trial_B"):
            trial = report[trial_key]
            congruency = trial["congruency"]
            if congruency == "n/a":
                continue
            for turn in trial["turns"]:
                total += 1
                val = turn.get("drift_score_hand")
                if val is None:
                    missing += 1
                    continue
                by_round[congruency][turn["round"]].append(val)
    return by_round, missing, total


def summarize(by_round):
    rows = []
    all_rounds = sorted({r for cong in by_round.values() for r in cong.keys()})
    for r in all_rounds:
        row = {"round": r}
        for congruency in ("congruent", "incongruent"):
            vals = by_round.get(congruency, {}).get(r, [])
            row[f"{congruency}_mean"] = (sum(vals) / len(vals)) if vals else None
            row[f"{congruency}_n"] = len(vals)
        rows.append(row)
    return rows


def print_table(rows):
    print(f"{'Round':<6} {'Congruent mean':<16} {'N':<5} {'Incongruent mean':<18} {'N':<5}")
    for row in rows:
        cm = row["congruent_mean"]
        im = row["incongruent_mean"]
        print(f"{row['round']:<6} "
              f"{(f'{cm:+.2f}' if cm is not None else 'n/a'):<16} {row['congruent_n']:<5} "
              f"{(f'{im:+.2f}' if im is not None else 'n/a'):<18} {row['incongruent_n']:<5}")


def make_chart(rows, out_path):
    rounds = [row["round"] for row in rows]
    cong = [row["congruent_mean"] for row in rows]
    incong = [row["incongruent_mean"] for row in rows]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.plot(rounds, cong, marker="o", label="Congruent attack (matches seed's lean)")
    ax.plot(rounds, incong, marker="o", label="Incongruent attack (opposes seed's lean)")
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean signed drift_score_hand (-10..+10)")
    ax.set_title("Congruent vs incongruent attack: signed drift by round")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"-> wrote {out_path}")


def main():
    topic_key = sys.argv[1] if len(sys.argv) > 1 else "abortion_policy"
    model = sys.argv[2] if len(sys.argv) > 2 else "GPT-OSS-120B-CS"

    reports = load_reports(topic_key, model)
    if not reports:
        print("No reports found -- run rspa_congruency_study.py first.")
        return

    by_round, missing, total = collect_by_round(reports)
    if missing:
        print(f"NOTE: {missing}/{total} turns still have drift_score_hand = null and were EXCLUDED "
              f"from these means (not treated as 0). Hand-score them for a complete picture.\n")

    rows = summarize(by_round)
    print_table(rows)

    if any(row["congruent_mean"] is not None for row in rows) and \
       any(row["incongruent_mean"] is not None for row in rows):
        out_path = CHARTS_DIR / f"congruency_{topic_key}_{model.replace('/', '_')}.png"
        make_chart(rows, out_path)

    # Endpoint summary: does congruent or incongruent end up FURTHER from
    # zero by the final round (entrenchment), or closer (correction)?
    last_round = rows[-1] if rows else None
    if last_round and last_round["congruent_mean"] is not None and last_round["incongruent_mean"] is not None:
        cm, im = last_round["congruent_mean"], last_round["incongruent_mean"]
        print(f"\nFinal round ({last_round['round']}): congruent |{cm:.2f}| vs incongruent |{im:.2f}|")
        if abs(im) > abs(cm):
            print("-> INCONGRUENT attack produced MORE end-state drift magnitude "
                  "(consistent with the backfire/entrenchment pilot read).")
        elif abs(cm) > abs(im):
            print("-> CONGRUENT attack produced MORE end-state drift magnitude "
                  "(consistent with the naive echo-chamber prediction).")
        else:
            print("-> No clear difference in end-state magnitude.")


if __name__ == "__main__":
    main()
