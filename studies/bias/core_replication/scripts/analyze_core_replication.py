"""
Analyze the rspa_core_* replication (Cell1 stateful/stateful vs Cell4 stateless/stateless,
3 seeds x 5 reps, abortion_policy, Gemini-3.5-Flash-Lite) using the hand-scored
drift_score_hand field, and produce summary charts.

Metric charted: mean |drift_score_hand| by round, averaged across trial_1/trial_2 and
across the 5 replicates -- consistent with the "memory matters" magnitude-of-drift
framing used earlier in this project (Cell4 as the null baseline).
"""
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "runs"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)
SEEDS = {"0": "0", "+a": "plus_a", "+b": "plus_b"}
SEED_LABELS = {"0": "Seed 0 (neutral)", "+a": "Seed +A (tilt toward Fetal Personhood)", "+b": "Seed +B (tilt toward Bodily Autonomy)"}
CELL_TAGS = ["atk-stateful_def-stateful", "atk-stateless_def-stateless"]
CELL_LABELS = {"atk-stateful_def-stateful": "Cell 1: stateful/stateful (memory)",
               "atk-stateless_def-stateless": "Cell 4: stateless/stateless (no memory)"}


def load(seed_key):
    safe = SEEDS[seed_key]
    reports = []
    for rep in range(1, 6):
        p = OUTPUT_DIR / f"rspa_core_abortion_policy_{safe}_Gemini-3.5-Flash-Lite_rep{rep}.json"
        reports.append(json.loads(p.read_text(encoding="utf-8")))
    return reports


def mean_abs_by_round(reports, tag):
    """Returns {round: mean |drift_score_hand| across both trials and all 5 reps}."""
    by_round = {r: [] for r in range(1, 6)}
    for report in reports:
        cell = next(c for c in report["cells"] if f"atk-{c['attacker_mode']}_def-{c['defender_mode']}" == tag)
        for trial_key in ("trial_1", "trial_2"):
            for turn in cell[trial_key]["turns"]:
                v = turn.get("drift_score_hand")
                if v is not None:
                    by_round[turn["round"]].append(abs(v))
    return {r: statistics.mean(vals) if vals else None for r, vals in by_round.items()}


def main():
    data = {}  # seed_key -> tag -> {round: mean_abs}
    for seed_key in SEEDS:
        reports = load(seed_key)
        data[seed_key] = {tag: mean_abs_by_round(reports, tag) for tag in CELL_TAGS}

    # console summary
    print("=== rspa_core replication: mean |drift_score_hand| by round ===\n")
    for seed_key in SEEDS:
        print(f"-- {SEED_LABELS[seed_key]} --")
        for tag in CELL_TAGS:
            rounds = data[seed_key][tag]
            row = "  ".join(f"R{r}={rounds[r]:.2f}" for r in range(1, 6))
            print(f"  {CELL_LABELS[tag]:38s} {row}")
        print()

    # --- Chart 1: 3-panel, one per seed, Cell1 vs Cell4 lines ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    rounds = list(range(1, 6))
    colors = {"atk-stateful_def-stateful": "#c0392b", "atk-stateless_def-stateless": "#7f8c8d"}
    for ax, seed_key in zip(axes, SEEDS):
        for tag in CELL_TAGS:
            vals = [data[seed_key][tag][r] for r in rounds]
            ax.plot(rounds, vals, marker="o", linewidth=2.5, color=colors[tag], label=CELL_LABELS[tag])
        ax.set_title(SEED_LABELS[seed_key], fontsize=11)
        ax.set_xlabel("Round")
        ax.set_xticks(rounds)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Mean |drift_score_hand| (0-10)")
    axes[0].legend(loc="upper left", fontsize=9)
    fig.suptitle("RSPA Cell1 (memory) vs Cell4 (no memory) -- abortion_policy, N=5 replicates/seed, hand-scored",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(CHARTS_DIR / "core_replication_3seeds_cell1_vs_cell4.png", dpi=150)
    print("-> wrote core_replication_3seeds_cell1_vs_cell4.png")

    # --- Chart 2: combined -- all 3 seeds overlaid per cell (2 panels) ---
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    seed_colors = {"0": "#2c3e50", "+a": "#2980b9", "+b": "#8e44ad"}
    for ax, tag in zip(axes2, CELL_TAGS):
        for seed_key in SEEDS:
            vals = [data[seed_key][tag][r] for r in rounds]
            ax.plot(rounds, vals, marker="o", linewidth=2.5, color=seed_colors[seed_key], label=SEED_LABELS[seed_key])
        ax.set_title(CELL_LABELS[tag], fontsize=12)
        ax.set_xlabel("Round")
        ax.set_xticks(rounds)
        ax.grid(alpha=0.3)
    axes2[0].set_ylabel("Mean |drift_score_hand| (0-10)")
    axes2[1].legend(loc="upper left", fontsize=9)
    fig2.suptitle("Replication across the Triangulated Seed Protocol (N=5 reps/seed, hand-scored)",
                  fontsize=13, fontweight="bold")
    fig2.tight_layout(rect=[0, 0, 1, 0.93])
    fig2.savefig(CHARTS_DIR / "core_replication_seed_stability.png", dpi=150)
    print("-> wrote core_replication_seed_stability.png")

    # --- Chart 3: pooled across all 3 seeds (mean of seed means), single clean panel ---
    fig3, ax3 = plt.subplots(figsize=(7, 5.5))
    for tag in CELL_TAGS:
        pooled = [statistics.mean(data[sk][tag][r] for sk in SEEDS) for r in rounds]
        ax3.plot(rounds, pooled, marker="o", linewidth=3, markersize=8, color=colors[tag], label=CELL_LABELS[tag])
    ax3.set_title("Memory matters: pooled across 3 seeds x 5 replicates (N=15/cell/round)", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Round")
    ax3.set_ylabel("Mean |drift_score_hand| (0-10)")
    ax3.set_xticks(rounds)
    ax3.grid(alpha=0.3)
    ax3.legend(loc="upper left", fontsize=10)
    fig3.tight_layout()
    fig3.savefig(CHARTS_DIR / "core_replication_pooled.png", dpi=150)
    print("-> wrote core_replication_pooled.png")


if __name__ == "__main__":
    main()
