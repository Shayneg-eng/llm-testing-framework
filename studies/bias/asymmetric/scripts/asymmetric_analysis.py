"""
Analysis for rspa_asymmetric_study.py output (stateless attacker / stateful
defender), and a direct comparison against the Cell-1 congruency study
(studies/bias/congruency/runs/, both stateful) already on file.

Usage: python asymmetric_analysis.py [topic_key] [model]
Defaults: topic_key=abortion_policy, model=GPT-OSS-120B-CS
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ASYM_DIR = Path(__file__).resolve().parent.parent / "runs"
CONG_DIR = Path(__file__).resolve().parents[4] / "studies" / "bias" / "congruency" / "runs"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)


def load_reports(base_dir, prefix, topic_key, model):
    safe_name = model.replace("/", "_")
    reports = []
    for seed_key in ("+a", "+b"):
        safe_seed = seed_key.replace("+", "plus_")
        pattern = f"{prefix}_{topic_key}_{safe_seed}_{safe_name}_rep*.json"
        files = sorted(base_dir.glob(pattern))
        if not files:
            print(f"WARNING: no files matched {pattern} in {base_dir}")
        for f in files:
            reports.append(json.loads(f.read_text(encoding="utf-8")))
    return reports


def collect_by_round(reports, by="congruency"):
    """by='congruency' -> congruent/incongruent; by='direction' -> A/B.

    Looks each round up by number out of a per-trial dict (turns_by_round)
    rather than iterating whatever turn objects exist, so a trial cut short
    by a structural refusal (no turn object at all for later rounds) is
    counted as missing at every round it never reached, not silently dropped
    from expected_n along with the mean."""
    by_key = defaultdict(lambda: defaultdict(list))
    expected_n = defaultdict(int)
    for report in reports:
        for trial_key in ("trial_A", "trial_B"):
            trial = report[trial_key]
            key = trial["congruency"] if by == "congruency" else trial["attack_direction"]
            if by == "congruency" and key == "n/a":
                continue
            expected_n[key] += 1
            turns_by_round = {t["round"]: t for t in trial["turns"]}
            for r in range(1, 6):
                turn = turns_by_round.get(r)
                val = turn.get("drift_score_hand") if turn else None
                if val is not None:
                    by_key[key][r].append(val)
    return by_key, expected_n


def means_and_counts_by_round(by_key, keys):
    rounds = range(1, 6)
    means = {k: [sum(by_key[k][r]) / len(by_key[k][r]) if by_key[k][r] else None for r in rounds] for k in keys}
    counts = {k: [len(by_key[k][r]) for r in rounds] for k in keys}
    return means, counts


def print_round_table(means, counts, expected_n):
    print(f"{'Round':<8}{'Congruent':<18}{'Incongruent':<18}")
    for i, r in enumerate(range(1, 6)):
        c = means["congruent"][i]
        ic = means["incongruent"][i]
        c_str = f"{c:+.2f}" if c is not None else "n/a"
        ic_str = f"{ic:+.2f}" if ic is not None else "n/a"
        if expected_n.get("congruent") and counts["congruent"][i] < expected_n["congruent"]:
            c_str += f" (n={counts['congruent'][i]}/{expected_n['congruent']})"
        if expected_n.get("incongruent") and counts["incongruent"][i] < expected_n["incongruent"]:
            ic_str += f" (n={counts['incongruent'][i]}/{expected_n['incongruent']})"
        print(f"{r:<8}{c_str:<18}{ic_str:<18}")


def print_truncation_note(label, counts, expected_n):
    lines = []
    for key in ("congruent", "incongruent"):
        exp = expected_n.get(key, 0)
        for i, r in enumerate(range(1, 6)):
            n = counts[key][i]
            if exp and n < exp:
                lines.append(f"  {key}, round {r}: {n}/{exp} replicates")
    if lines:
        print(f"NOTE ({label}): {len(lines)} (key, round) cell(s) built from fewer than the full "
              f"replicate count -- a structural refusal likely cut a trial short, or a turn is not "
              f"yet hand-scored. This includes rounds a trial never reached at all:")
        for line in lines:
            print(line)
        print()


def main():
    topic_key = sys.argv[1] if len(sys.argv) > 1 else "abortion_policy"
    model = sys.argv[2] if len(sys.argv) > 2 else "GPT-OSS-120B-CS"

    asym_reports = load_reports(ASYM_DIR, "rspa_asymmetric", topic_key, model)
    cong_reports = load_reports(CONG_DIR, "rspa_congruency", topic_key, model)

    if not asym_reports:
        print("No asymmetric-design reports found -- run rspa_asymmetric_study.py first.")
        return

    asym_by_cong, asym_expected = collect_by_round(asym_reports, by="congruency")
    asym_means, asym_counts = means_and_counts_by_round(asym_by_cong, ["congruent", "incongruent"])
    print_truncation_note("Asymmetric design", asym_counts, asym_expected)

    print("=== Asymmetric design (stateless attacker / stateful defender) ===")
    print_round_table(asym_means, asym_counts, asym_expected)

    if not cong_reports:
        print("\n(No Cell-1 studies/bias/congruency/runs/ data found for comparison -- skipping side-by-side.)")
        make_chart_single(asym_means)
        return

    cong_by_cong, cong_expected = collect_by_round(cong_reports, by="congruency")
    cong_means, cong_counts = means_and_counts_by_round(cong_by_cong, ["congruent", "incongruent"])

    print("\n=== Cell 1 (both stateful) -- for comparison, from studies/bias/congruency/runs/ ===")
    print_round_table(cong_means, cong_counts, cong_expected)
    print_truncation_note("Cell 1 (congruency study)", cong_counts, cong_expected)

    # Effect-size comparison at round 5
    print("\n=== Round-5 magnitude comparison ===")
    for key in ("congruent", "incongruent"):
        a5 = asym_means[key][-1]
        c5 = cong_means[key][-1]
        if a5 is not None and c5 is not None:
            more = "ASYMMETRIC design" if abs(a5) > abs(c5) else "Cell 1 (both stateful)"
            print(f"{key}: asymmetric={a5:+.2f}  cell1={c5:+.2f}  -> {more} shows more drift magnitude")

    make_chart_comparison(asym_means, cong_means)


def make_chart_single(means):
    rounds = list(range(1, 6))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.plot(rounds, means["congruent"], marker="o", label="Congruent")
    ax.plot(rounds, means["incongruent"], marker="o", label="Incongruent")
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean signed drift_score_hand")
    ax.set_title("Asymmetric design: congruent vs incongruent")
    ax.legend()
    fig.tight_layout()
    out_path = CHARTS_DIR / "asymmetric_congruency.png"
    fig.savefig(out_path, dpi=150)
    print(f"-> wrote {out_path}")


def make_chart_comparison(asym_means, cong_means):
    rounds = list(range(1, 6))
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.plot(rounds, cong_means["congruent"], marker="o", linestyle="--", color="#1f618d", label="Cell 1: congruent")
    ax.plot(rounds, cong_means["incongruent"], marker="o", linestyle="--", color="#b03a2e", label="Cell 1: incongruent")
    ax.plot(rounds, asym_means["congruent"], marker="s", color="#1f618d", label="Asymmetric: congruent")
    ax.plot(rounds, asym_means["incongruent"], marker="s", color="#b03a2e", label="Asymmetric: incongruent")
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean signed drift_score_hand")
    ax.set_title("Cell 1 (both stateful, dashed) vs\nAsymmetric (stateless attacker, solid)")
    ax.legend(fontsize=8)

    ax2 = axes[1]
    labels = ["congruent R5", "incongruent R5"]
    cong_vals = [cong_means["congruent"][-1] or 0, cong_means["incongruent"][-1] or 0]
    asym_vals = [asym_means["congruent"][-1] or 0, asym_means["incongruent"][-1] or 0]
    x = range(len(labels))
    width = 0.35
    ax2.bar([i - width / 2 for i in x], cong_vals, width, label="Cell 1 (both stateful)")
    ax2.bar([i + width / 2 for i in x], asym_vals, width, label="Asymmetric (stateless attacker)")
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Round-5 mean signed drift")
    ax2.set_title("Round-5 magnitude: design comparison")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    out_path = CHARTS_DIR / "asymmetric_vs_cell1_comparison.png"
    fig.savefig(out_path, dpi=150)
    print(f"-> wrote {out_path}")


if __name__ == "__main__":
    main()
