"""
Analysis for rspa_group_trope_bias_study.py output.
Reads the hand-scored aggregate (aggregate_group_trope_bias_scores.json) and writes
three charts to charts/, prefixed group_trope_bias_*, per ORGANIZATION.md.

Usage: python group_trope_bias_analysis.py
"""

import csv
import json
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE.parent / "runs"
CHARTS_DIR = HERE.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# Fixed categorical order / colors (dataviz skill default palette, slots 1-3)
RELIGION_COLOR = {
    "jewish": "#2a78d6",     # slot 1, blue
    "christian": "#eb6834",  # slot 2, orange
    "muslim": "#1baf7a",     # slot 3, aqua
}
RELIGION_LABEL = {"jewish": "Jewish", "christian": "Christian", "muslim": "Muslim"}
TROPE_LABEL = {
    "greed_theft": "Greed / theft\n(business partner)",
    "control_nepotism": "Control / nepotism\n(manager favoritism)",
    "dual_loyalty": "Dual loyalty\n(coworker statement)",
}
TROPES = ["greed_theft", "control_nepotism", "dual_loyalty"]
RELIGIONS = ["jewish", "christian", "muslim"]

INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "font.family": "sans-serif",
    "text.color": INK,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": SECONDARY_INK,
    "xtick.color": SECONDARY_INK,
    "ytick.color": SECONDARY_INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def load_scores():
    rows = []
    with open(RUNS_DIR / "aggregate_group_trope_bias_scores.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "trope": r["trope"], "religion": r["religion"], "dir": r["dir"],
                "rep": int(r["rep"]), "round": int(r["round"]), "score": int(r["score"]),
            })
    return rows


def mean_by(rows, round_num):
    out = defaultdict(list)
    for r in rows:
        if r["round"] == round_num:
            out[(r["trope"], r["religion"], r["dir"])].append(r["score"])
    return {k: sum(v) / len(v) for k, v in out.items()}


def chart_round5_bars(rows):
    """Grouped bars: round-5 mean score by trope x religion, one panel per direction."""
    means5 = mean_by(rows, 5)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=False)
    bar_w = 0.25
    x = range(len(TROPES))

    for ax, direction, dtitle in zip(
        axes, ["A", "B"],
        ["Direction A: pushed toward ESCALATION\n(higher = more punitive)",
         "Direction B: pushed toward RECONCILIATION\n(lower = more lenient)"]
    ):
        for i, religion in enumerate(RELIGIONS):
            vals = [means5[(t, religion, direction)] for t in TROPES]
            offsets = [xi + (i - 1) * bar_w for xi in x]
            bars = ax.bar(offsets, vals, width=bar_w, color=RELIGION_COLOR[religion],
                           label=RELIGION_LABEL[religion], zorder=3)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + (0.3 if v >= 0 else -0.3),
                        f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top",
                        fontsize=8.5, color=SECONDARY_INK)
        ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
        ax.set_ylim(-10.5, 10.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels([TROPE_LABEL[t] for t in TROPES], fontsize=9)
        ax.set_title(dtitle, fontsize=10.5, color=INK, pad=10)
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

    axes[0].set_ylabel("Mean score after 5 rounds\n(-10 fully reconciliatory .. +10 fully escalatory)",
                        fontsize=9)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.03),
               ncol=3, frameon=False, fontsize=10)
    fig.suptitle("Where each scenario ends up after 5 rounds of pressure, by religion",
                 fontsize=13, color=INK, y=1.12)
    fig.text(0.5, -0.02,
              "Same scenario text in all three religion conditions, except the religion word. n=2 replicates per bar.",
              ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    out = CHARTS_DIR / "group_trope_bias_round5_by_religion.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"-> wrote {out}")


def chart_trajectory(rows, trope, direction, title, fname, ylim=(-10.5, 10.5)):
    """Line chart: round-by-round mean score (across reps) for each religion, one trope+direction."""
    fig, ax = plt.subplots(figsize=(7.5, 5))
    rounds = [1, 2, 3, 4, 5]

    end_values = {}
    for religion in RELIGIONS:
        means_per_round = []
        for rnd in rounds:
            vals = [r["score"] for r in rows
                    if r["trope"] == trope and r["religion"] == religion
                    and r["dir"] == direction and r["round"] == rnd]
            means_per_round.append(sum(vals) / len(vals))
        ax.plot(rounds, means_per_round, marker="o", markersize=7, linewidth=2.5,
                color=RELIGION_COLOR[religion], label=RELIGION_LABEL[religion], zorder=3)
        end_values[religion] = means_per_round[-1]

    # Stagger end-of-line labels that would otherwise overlap (within 0.6 of each other)
    order = sorted(RELIGIONS, key=lambda r: end_values[r])
    placed = []
    for religion in order:
        y = end_values[religion]
        while placed and (y - placed[-1]) < 0.7 - 1e-9:
            y = placed[-1] + 0.7
        placed.append(y)
        ax.text(rounds[-1] + 0.08, y, RELIGION_LABEL[religion],
                color=RELIGION_COLOR[religion], fontsize=10, va="center", fontweight="bold")

    ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
    ax.set_xticks(rounds)
    ax.set_xticklabels([f"Round {r}" if r in (1, 5) else str(r) for r in rounds])
    ax.set_xlim(0.8, 5.9)
    ax.set_ylim(*ylim)
    ax.set_ylabel("Mean score (-10 reconciliatory .. +10 escalatory)", fontsize=9)
    ax.set_title(title, fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    fig.text(0.5, 0.01, "Each point is the mean of 2 replicates.", ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    out = CHARTS_DIR / fname
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"-> wrote {out}")


def main():
    rows = load_scores()
    chart_round5_bars(rows)
    chart_trajectory(
        rows, "greed_theft", "A",
        "Greed/theft scenario, argued toward ESCALATION\n(\"a [religion] business partner stole from my business\")",
        "group_trope_bias_greed_theft_dirA_trajectory.png",
    )
    chart_trajectory(
        rows, "dual_loyalty", "B",
        "Dual-loyalty scenario, argued toward RECONCILIATION\n(\"a [religion] coworker said group loyalty comes first\")",
        "group_trope_bias_dual_loyalty_dirB_trajectory.png",
    )


if __name__ == "__main__":
    main()
