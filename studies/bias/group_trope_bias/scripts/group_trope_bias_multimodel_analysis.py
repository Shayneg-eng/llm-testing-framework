"""
Multi-model analysis for rspa_group_trope_bias_study.py output.
Reads the merged multi-model aggregate (aggregate_group_trope_bias_scores_multimodel.csv,
which has a `model` column) and writes three charts to charts/, prefixed
group_trope_bias_multimodel_*, per ORGANIZATION.md.

Same chart *types* as the original single-model pilot (group_trope_bias_analysis.py):
  1. grouped bars of round-5 mean score by trope x religion, direction A vs B
  2. round-by-round trajectory line chart, one trope+direction, by religion
Extended here with one small-multiple panel per model, since this run covers 5 models
instead of 1. Grok-4.5's run is incomplete (only greed_theft in full, plus one
control_nepotism/jewish/A cell) -- panels/lines with no data are simply omitted rather
than drawn as zero, and a footnote calls out the gap.

Usage: python group_trope_bias_multimodel_analysis.py
"""

import csv
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE.parent / "runs"
CHARTS_DIR = HERE.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# Fixed categorical order / colors (dataviz skill default palette, slots 1-3) -- kept
# identical to the single-model pilot so religion colors mean the same thing everywhere.
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
# Shorter labels for the dense multi-model grid, where each panel is narrow.
TROPE_LABEL_SHORT = {
    "greed_theft": "Greed/\ntheft",
    "control_nepotism": "Control/\nnepotism",
    "dual_loyalty": "Dual\nloyalty",
}
TROPES = ["greed_theft", "control_nepotism", "dual_loyalty"]
RELIGIONS = ["jewish", "christian", "muslim"]

# Model display order -- roughly cost tier / release recency, matches the run order.
MODELS = ["GPT-OSS-120B-CS", "GPT-5.4-Mini", "Claude-Sonnet-4.6", "Gemini-3.5-Flash-Lite", "Grok-4.5"]
MODEL_LABEL = {
    "GPT-OSS-120B-CS": "GPT-OSS-120B-CS",
    "GPT-5.4-Mini": "GPT-5.4-Mini",
    "Claude-Sonnet-4.6": "Claude Sonnet 4.6",
    "Gemini-3.5-Flash-Lite": "Gemini 3.5 Flash-Lite",
    "Grok-4.5": "Grok 4.5*",
}
MODEL_REPS = {
    "GPT-OSS-120B-CS": 3, "GPT-5.4-Mini": 3, "Claude-Sonnet-4.6": 3,
    "Gemini-3.5-Flash-Lite": 3, "Grok-4.5": 3,
}

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
    with open(RUNS_DIR / "aggregate_group_trope_bias_scores_multimodel.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "model": r["model"], "trope": r["trope"], "religion": r["religion"], "dir": r["dir"],
                "rep": int(r["rep"]), "round": int(r["round"]), "score": int(r["score"]),
            })
    return rows


def mean_by(rows, round_num):
    out = defaultdict(list)
    for r in rows:
        if r["round"] == round_num:
            out[(r["model"], r["trope"], r["religion"], r["dir"])].append(r["score"])
    return {k: sum(v) / len(v) for k, v in out.items()}


def chart_round5_bars(rows):
    """Grid: one row per model, one column per direction. Each panel is the same
    grouped-bar layout as the single-model pilot (trope on x, bars colored by religion)."""
    means5 = mean_by(rows, 5)

    n_models = len(MODELS)
    fig, axes = plt.subplots(n_models, 2, figsize=(12.5, 3.1 * n_models), sharey=True)
    bar_w = 0.25
    x = list(range(len(TROPES)))

    dir_titles = {
        "A": "Direction A: pushed toward ESCALATION",
        "B": "Direction B: pushed toward RECONCILIATION",
    }

    for row, model in enumerate(MODELS):
        for col, direction in enumerate(["A", "B"]):
            ax = axes[row, col]
            any_bar = False
            for i, religion in enumerate(RELIGIONS):
                vals, offsets = [], []
                for xi, t in zip(x, TROPES):
                    key = (model, t, religion, direction)
                    if key in means5:
                        vals.append(means5[key])
                        offsets.append(xi + (i - 1) * bar_w)
                if not vals:
                    continue
                any_bar = True
                bars = ax.bar(offsets, vals, width=bar_w, color=RELIGION_COLOR[religion],
                               label=RELIGION_LABEL[religion], zorder=3)
                for b, v in zip(bars, vals):
                    ax.text(b.get_x() + b.get_width() / 2, v + (0.3 if v >= 0 else -0.3),
                            f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top",
                            fontsize=7.5, color=SECONDARY_INK)
            ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
            ax.set_ylim(-10.5, 10.5)
            ax.set_xticks(x)
            ax.set_xticklabels([TROPE_LABEL_SHORT[t] for t in TROPES], fontsize=8.5)
            if row == 0:
                ax.set_title(dir_titles[direction], fontsize=10, color=INK, pad=8)
            ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            if not any_bar:
                ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center",
                        color=MUTED, fontsize=9, style="italic")
            if col == 0:
                ax.text(-0.32, 0.5, MODEL_LABEL[model], transform=ax.transAxes,
                        ha="right", va="center", fontsize=10.5, color=INK, fontweight="bold",
                        rotation=0)

    handles, labels = None, None
    for row in range(n_models):
        h, l = axes[row, 0].get_legend_handles_labels()
        if h:
            handles, labels = h, l
            break
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.008),
               ncol=3, frameon=False, fontsize=10)
    fig.suptitle("Where each scenario ends up after 5 rounds of pressure, by religion -- across models",
                 fontsize=13.5, color=INK, y=1.025)
    fig.text(0.5, -0.005,
              "Same scenario text in all three religion conditions, except the religion word. "
              "n=2-3 replicates per bar. *Grok-4.5's run ended early (points exhausted) -- only "
              "greed/theft is complete for it; other cells show \"no data\".",
              ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=[0.06, 0.0, 1, 0.99])
    out = CHARTS_DIR / "group_trope_bias_multimodel_round5_by_religion.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"-> wrote {out}")


def chart_trajectory_multimodel(rows, trope, direction, title, fname, models=None, ylim=(-10.5, 10.5)):
    """Small multiples: one panel per model, each panel is the same line-chart layout
    as the single-model pilot (round on x, one line per religion)."""
    use_models = models if models is not None else MODELS
    n = len(use_models)
    ncols = min(n, 3)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.6 * nrows), squeeze=False)
    rounds = [1, 2, 3, 4, 5]

    for idx, model in enumerate(use_models):
        ax = axes[idx // ncols][idx % ncols]
        end_values = {}
        plotted_any = False
        for religion in RELIGIONS:
            means_per_round = []
            ok = True
            for rnd in rounds:
                vals = [r["score"] for r in rows
                        if r["model"] == model and r["trope"] == trope and r["religion"] == religion
                        and r["dir"] == direction and r["round"] == rnd]
                if not vals:
                    ok = False
                    break
                means_per_round.append(sum(vals) / len(vals))
            if not ok:
                continue
            plotted_any = True
            ax.plot(rounds, means_per_round, marker="o", markersize=6, linewidth=2.2,
                    color=RELIGION_COLOR[religion], label=RELIGION_LABEL[religion], zorder=3)
            end_values[religion] = means_per_round[-1]

        order = sorted(end_values, key=lambda r: end_values[r])
        placed = []
        for religion in order:
            y = end_values[religion]
            while placed and (y - placed[-1]) < 0.9 - 1e-9:
                y = placed[-1] + 0.9
            placed.append(y)
            ax.text(rounds[-1] + 0.1, y, RELIGION_LABEL[religion],
                    color=RELIGION_COLOR[religion], fontsize=9, va="center", fontweight="bold")

        ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
        ax.set_xticks(rounds)
        ax.set_xlim(0.8, 6.3)
        ax.set_ylim(*ylim)
        ax.set_title(MODEL_LABEL[model], fontsize=11, color=INK, pad=8)
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        if not plotted_any:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center",
                    color=MUTED, fontsize=9, style="italic")

    # hide unused axes in the grid
    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis("off")

    axes[0][0].set_ylabel("Mean score (-10 reconciliatory .. +10 escalatory)", fontsize=9)
    fig.suptitle(title, fontsize=13, color=INK, y=1.0)
    fig.text(0.5, -0.01, "Each point is the mean of 2-3 replicates.", ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.01, 1, 0.94])
    out = CHARTS_DIR / fname
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"-> wrote {out}")


def main():
    rows = load_scores()
    chart_round5_bars(rows)
    chart_trajectory_multimodel(
        rows, "greed_theft", "A",
        "Greed/theft scenario, argued toward ESCALATION, across models\n"
        "(\"a [religion] business partner stole from my business\")",
        "group_trope_bias_multimodel_greed_theft_dirA_trajectory.png",
    )
    # Grok-4.5 has no dual_loyalty data at all -- drop it from this panel rather than
    # drawing an empty/misleading subplot.
    models_with_dual_loyalty = [m for m in MODELS if m != "Grok-4.5"]
    chart_trajectory_multimodel(
        rows, "dual_loyalty", "B",
        "Dual-loyalty scenario, argued toward RECONCILIATION, across models\n"
        "(\"a [religion] coworker said group loyalty comes first\")\n"
        "Grok-4.5 omitted -- its run ended before reaching this scenario",
        "group_trope_bias_multimodel_dual_loyalty_dirB_trajectory.png",
        models=models_with_dual_loyalty,
    )


if __name__ == "__main__":
    main()
