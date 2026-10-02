"""
Analysis for rspa_starting_position_study.py output.

Produces, once every turn's drift_score_hand is filled in:
  1. A table of round-5 mean signed drift, one row per seed, one column per
     attack direction (A / B) -- the core "does starting position matter"
     comparison, with attack direction held visible rather than pooled away.
  2. A line chart, one line per seed, x-axis = round, faceted by attack
     direction, so the whole starting-position x attack-direction grid is
     visible at once.
  3. A "does intensity matter" cut: for the pro-life and pro-choice legs,
     plots round-5 drift against nudge intensity (mild/moderate/strong) for
     each attack direction, to see whether a stronger starting lean produces
     more, less, or the same drift as its own-direction attack scales up.

Usage: python starting_position_analysis.py [topic_key] [model]
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

SEED_ORDER = ["+++a", "++a", "+a", "0", "0-legal", "0-medical", "+b", "++b", "+++b"]
SEED_LABELS = {
    "+++a": "+++a (strong pro-life)", "++a": "++a (moderate pro-life)", "+a": "+a (mild pro-life)",
    "0": "0 (neutral)", "0-legal": "0-legal (neutral)", "0-medical": "0-medical (neutral)",
    "+b": "+b (mild pro-choice)", "++b": "++b (moderate pro-choice)", "+++b": "+++b (strong pro-choice)",
}
PRO_LIFE_TIERS = ["+a", "++a", "+++a"]     # mild -> strong
PRO_CHOICE_TIERS = ["+b", "++b", "+++b"]   # mild -> strong


def safe_seed(seed_key):
    return seed_key.replace("+", "plus_").replace("/", "_")


def load_reports(topic_key, model):
    safe_name = model.replace("/", "_")
    reports = {}  # seed_key -> list of report dicts
    for seed_key in SEED_ORDER:
        pattern = f"rspa_startpos_{topic_key}_{safe_seed(seed_key)}_{safe_name}_rep*.json"
        files = sorted(RUNS_DIR.glob(pattern))
        if not files:
            print(f"WARNING: no files matched {pattern}")
        reports[seed_key] = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return reports


def means_by_round(reports_for_seed, trial_key):
    """Returns (means, counts, expected_n) for rounds 1..5.

    counts[r-1] is how many replicates actually contributed a non-null
    drift_score_hand at round r. This is deliberately computed by looking up
    each round by number out of a per-report dict (turns_by_round), rather
    than by iterating whatever turn objects happen to exist -- so a trial cut
    short by a structural refusal (which leaves NO turn object for later
    rounds, not a turn with drift_score_hand=None) is counted as missing at
    every round it never reached, not silently dropped from both the mean
    and the missing-data note."""
    expected_n = len(reports_for_seed)
    by_round = defaultdict(list)
    for report in reports_for_seed:
        turns_by_round = {t["round"]: t for t in report[trial_key]["turns"]}
        for r in range(1, 6):
            turn = turns_by_round.get(r)
            val = turn.get("drift_score_hand") if turn else None
            if val is not None:
                by_round[r].append(val)
    means = [sum(by_round[r]) / len(by_round[r]) if by_round[r] else None for r in range(1, 6)]
    counts = [len(by_round[r]) for r in range(1, 6)]
    return means, counts, expected_n


def main():
    topic_key = sys.argv[1] if len(sys.argv) > 1 else "abortion_policy"
    model = sys.argv[2] if len(sys.argv) > 2 else "GPT-OSS-120B-CS"

    reports = load_reports(topic_key, model)
    if not any(reports.values()):
        print("No starting-position reports found -- run rspa_starting_position_study.py first.")
        return

    means_a, means_b = {}, {}
    counts_a, counts_b = {}, {}
    expected_n = {}
    truncated_cells = []
    for seed_key in SEED_ORDER:
        rep_list = reports[seed_key]
        if not rep_list:
            means_a[seed_key] = [None] * 5
            means_b[seed_key] = [None] * 5
            counts_a[seed_key] = [0] * 5
            counts_b[seed_key] = [0] * 5
            expected_n[seed_key] = 0
            continue
        ma, ca, exp_a = means_by_round(rep_list, "trial_A")
        mb, cb, exp_b = means_by_round(rep_list, "trial_B")
        means_a[seed_key] = ma
        means_b[seed_key] = mb
        counts_a[seed_key] = ca
        counts_b[seed_key] = cb
        expected_n[seed_key] = exp_a  # trial_A and trial_B share the same replicate list
        for r_idx, (n_a, n_b) in enumerate(zip(ca, cb), start=1):
            if n_a < exp_a:
                truncated_cells.append(f"  seed {seed_key}, dir A, round {r_idx}: {n_a}/{exp_a} replicates")
            if n_b < exp_b:
                truncated_cells.append(f"  seed {seed_key}, dir B, round {r_idx}: {n_b}/{exp_b} replicates")

    if truncated_cells:
        print(f"NOTE: {len(truncated_cells)} (seed, direction, round) cell(s) built from fewer than "
              f"the full replicate count -- likely a structural refusal cut a trial short, or a turn "
              f"is not yet hand-scored. This includes rounds a trial never reached at all, not just "
              f"turns with drift_score_hand=null:")
        for line in truncated_cells:
            print(line)
        print()

    # --- Table 1: round-5 mean by seed x attack direction ---
    print("=== Round-5 mean signed drift, by starting position x attack direction ===")
    print(f"{'Seed':<28}{'Attacked from A':<22}{'Attacked from B':<22}")
    for seed_key in SEED_ORDER:
        a5 = means_a[seed_key][-1]
        b5 = means_b[seed_key][-1]
        exp = expected_n[seed_key]
        n_a5 = counts_a[seed_key][-1]
        n_b5 = counts_b[seed_key][-1]
        a_str = f"{a5:+.2f}" if a5 is not None else "n/a"
        b_str = f"{b5:+.2f}" if b5 is not None else "n/a"
        if exp and n_a5 < exp:
            a_str += f" (n={n_a5}/{exp})"
        if exp and n_b5 < exp:
            b_str += f" (n={n_b5}/{exp})"
        print(f"{SEED_LABELS[seed_key]:<28}{a_str:<22}{b_str:<22}")

    make_grid_chart(means_a, means_b)
    make_intensity_chart(means_a, means_b)


def make_grid_chart(means_a, means_b):
    rounds = list(range(1, 6))
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    cmap = plt.get_cmap("RdBu")
    # Color each seed by its lean: pro-life (A) = blue end, neutral = gray, pro-choice (B) = red end
    color_by_seed = {
        "+++a": cmap(0.05), "++a": cmap(0.20), "+a": cmap(0.35),
        "0": "#888888", "0-legal": "#aaaaaa", "0-medical": "#666666",
        "+b": cmap(0.65), "++b": cmap(0.80), "+++b": cmap(0.95),
    }
    for ax, means, title in ((axes[0], means_a, "Attacked from Direction A (toward Fetal Personhood)"),
                              (axes[1], means_b, "Attacked from Direction B (toward Bodily Autonomy)")):
        ax.axhline(0, color="gray", linewidth=0.8, linestyle=":")
        for seed_key in SEED_ORDER:
            ax.plot(rounds, means[seed_key], marker="o", color=color_by_seed[seed_key],
                     linestyle="--" if seed_key.startswith("0") else "-",
                     label=SEED_LABELS[seed_key])
        ax.set_xlabel("Round")
        ax.set_title(title)
        ax.set_ylim(-10, 10)
    axes[0].set_ylabel("Mean signed drift_score_hand\n(-10 Fetal Personhood .. +10 Bodily Autonomy)")
    axes[1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.suptitle("Starting position x attack direction: where does the defender end up?")
    fig.tight_layout()
    out_path = CHARTS_DIR / "starting_position_grid.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n-> wrote {out_path}")


def make_intensity_chart(means_a, means_b):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    tiers = ["mild", "moderate", "strong"]

    ax = axes[0]
    pro_life_own = [means_a[k][-1] for k in PRO_LIFE_TIERS]   # attacked from A = congruent for pro-life seeds
    pro_life_opp = [means_b[k][-1] for k in PRO_LIFE_TIERS]   # attacked from B = incongruent
    ax.plot(tiers, pro_life_own, marker="o", label="Attacked from own side (A, congruent)")
    ax.plot(tiers, pro_life_opp, marker="s", label="Attacked from opposite side (B, incongruent)")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle=":")
    ax.set_title("Pro-life seeds (+a / ++a / +++a): round-5 drift by nudge intensity")
    ax.set_ylabel("Round-5 mean signed drift")
    ax.legend(fontsize=8)

    ax2 = axes[1]
    pro_choice_own = [means_b[k][-1] for k in PRO_CHOICE_TIERS]  # attacked from B = congruent for pro-choice seeds
    pro_choice_opp = [means_a[k][-1] for k in PRO_CHOICE_TIERS]  # attacked from A = incongruent
    ax2.plot(tiers, pro_choice_own, marker="o", color="#b03a2e", label="Attacked from own side (B, congruent)")
    ax2.plot(tiers, pro_choice_opp, marker="s", color="#1f618d", label="Attacked from opposite side (A, incongruent)")
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle=":")
    ax2.set_title("Pro-choice seeds (+b / ++b / +++b): round-5 drift by nudge intensity")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    out_path = CHARTS_DIR / "starting_position_intensity.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"-> wrote {out_path}")


if __name__ == "__main__":
    main()
