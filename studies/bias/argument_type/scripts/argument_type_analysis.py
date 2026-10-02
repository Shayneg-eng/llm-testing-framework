"""
S.H.A.Y.N.E. / RSPA -- Argument-Type Study Analysis
=====================================================
Reads every runs/rspa_argtype_*.json report, computes
per-(model, seed/argument-type) round-by-round mean signed drift
(-10 Fetal Personhood absolutism .. +10 Bodily Autonomy absolutism),
attacked from Direction A only, and writes:
  - a printed summary table (round-1 vs round-5 mean, net movement)
  - charts/argument_type_by_seed.png (round-by-round lines,
    one panel per model, one line per argument-type seed)
  - charts/argument_type_net_movement.png (bar chart of net
    round1->round5 movement per model x seed)

Explicitly reports replicate counts per cell and flags any cell built
from fewer than the full replicate count (n=X/Y), per the refusal-
truncation-visibility fix from the 2026-09-15 code audit. Kimi-K3 is
reported separately (it could not complete this design -- see the
write-up) rather than folded into the round-by-round comparison.

Run: python argument_type_analysis.py
"""

import json
import glob
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

SEED_ORDER = ["0", "0-legal", "0-medical", "0-philosophical", "0-empirical"]
SEED_LABEL = {
    "0": "rights-in-tension",
    "0-legal": "legal",
    "0-medical": "medical",
    "0-philosophical": "philosophical",
    "0-empirical": "empirical",
}
MODEL_ORDER = ["GPT-5.4-Nano", "Gemini-3.5-Flash-Lite", "Kimi-K3", "GPT-OSS-120B-CS"]


def load_reports():
    files = sorted(glob.glob(str(RUNS_DIR / "rspa_argtype_*.json")))
    reports = []
    for f in files:
        reports.append(json.load(open(f, encoding="utf-8")))
    return reports


def means_by_round(reports, model, seed):
    """Returns (round -> mean score, round -> n scored) for one (model, seed),
    looking each round up explicitly by its round number so a round a trial
    never reached (refusal) is excluded from that round's mean rather than
    silently shifting later rounds -- same fix as starting_position_analysis.py."""
    by_round = defaultdict(list)
    for r in reports:
        cfg = r["config"]
        if cfg["model"] != model or cfg["seed_key"] != seed:
            continue
        for t in r["trial_A"]["turns"]:
            score = t.get("drift_score_hand")
            if score is not None:
                by_round[t["round"]].append(score)
    means = {rnd: (sum(vals) / len(vals)) for rnd, vals in by_round.items()}
    counts = {rnd: len(vals) for rnd, vals in by_round.items()}
    return means, counts


def main():
    reports = load_reports()
    print(f"Loaded {len(reports)} trial reports from {RUNS_DIR}\n")

    # Replicate-count / completion health check per model (informational).
    print("=== Trial completion by model ===")
    for model in MODEL_ORDER:
        model_reports = [r for r in reports if r["config"]["model"] == model]
        clean5 = sum(1 for r in model_reports if len(r["trial_A"]["turns"]) == 5
                     and not r["trial_A"]["turns"][-1]["refusal_flag"])
        print(f"  {model}: {len(model_reports)} trials, {clean5} completed all 5 rounds "
              f"({clean5}/{len(model_reports)})")
    print()

    print("=== Round-1 vs Round-5 mean signed drift, by argument type (Direction A attack) ===")
    print(f"{'Model':<24}{'Argument type':<18}{'R1 mean (n)':<16}{'R5 mean (n)':<16}{'Net R1->R5':<12}")
    summary_rows = []
    for model in ["GPT-5.4-Nano", "Gemini-3.5-Flash-Lite", "GPT-OSS-120B-CS"]:
        for seed in SEED_ORDER:
            means, counts = means_by_round(reports, model, seed)
            if not means:
                continue
            r1 = means.get(1)
            r5 = means.get(5)
            n1 = counts.get(1, 0)
            n5 = counts.get(5, 0)
            net = (r5 - r1) if (r1 is not None and r5 is not None) else None
            trunc_flag = " *" if n5 < 5 else ""
            r1_str = f"{r1:+.2f} (n={n1}/5)" if r1 is not None else "n/a"
            r5_str = f"{r5:+.2f} (n={n5}/5){trunc_flag}" if r5 is not None else "n/a"
            net_str = f"{net:+.2f}" if net is not None else "n/a"
            print(f"{model:<24}{SEED_LABEL[seed]:<18}{r1_str:<16}{r5_str:<16}{net_str:<12}")
            summary_rows.append((model, seed, means, counts, r1, r5, net))
    print("\n(* = fewer than 5 replicates reached round 5 -- see per-cell n)\n")

    # Kimi-K3: report separately, do not fold into the comparison above.
    kimi_reports = [r for r in reports if r["config"]["model"] == "Kimi-K3"]
    n_kimi_clean5 = sum(1 for r in kimi_reports if len(r["trial_A"]["turns"]) == 5
                         and not r["trial_A"]["turns"][-1]["refusal_flag"])
    print(f"=== Kimi-K3 (excluded from round-5 comparison above) ===")
    print(f"{n_kimi_clean5}/{len(kimi_reports)} trials completed all 5 rounds -- see write-up for detail.\n")

    # --- Chart 1: round-by-round lines, one panel per model -----------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)
    colors = {
        "0": "#888888", "0-legal": "#4C72B0", "0-medical": "#DD8452",
        "0-philosophical": "#55A868", "0-empirical": "#C44E52",
    }
    for ax, model in zip(axes, ["GPT-5.4-Nano", "Gemini-3.5-Flash-Lite", "GPT-OSS-120B-CS"]):
        for seed in SEED_ORDER:
            means, counts = means_by_round(reports, model, seed)
            rounds = sorted(means)
            if not rounds:
                continue
            ax.plot(rounds, [means[r] for r in rounds], marker="o",
                    label=SEED_LABEL[seed], color=colors[seed], linewidth=2)
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.set_title(model)
        ax.set_xlabel("Round")
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.set_ylim(-9, 9)
    axes[0].set_ylabel("Mean signed drift\n(-10 Fetal Personhood .. +10 Bodily Autonomy)")
    axes[2].legend(title="Argument type\n(neutral seed)", loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.suptitle("Argument-type study: round-by-round drift under Direction-A attack, by neutral-seed framing",
                 fontsize=12)
    fig.tight_layout()
    out1 = CHARTS_DIR / "argument_type_by_seed.png"
    fig.savefig(out1, dpi=150, bbox_inches="tight")
    print(f"-> wrote {out1}")

    # --- Chart 2: net movement bar chart ------------------------------------
    fig2, ax2 = plt.subplots(figsize=(9, 5.5))
    x_labels = [SEED_LABEL[s] for s in SEED_ORDER]
    x = range(len(SEED_ORDER))
    width = 0.25
    for i, model in enumerate(["GPT-5.4-Nano", "Gemini-3.5-Flash-Lite", "GPT-OSS-120B-CS"]):
        nets = []
        for seed in SEED_ORDER:
            means, _ = means_by_round(reports, model, seed)
            r1, r5 = means.get(1), means.get(5)
            nets.append((r5 - r1) if (r1 is not None and r5 is not None) else 0)
        offset = (i - 1.0) * width
        bars = ax2.bar([xi + offset for xi in x], nets, width, label=model)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(x_labels)
    ax2.set_ylabel("Net movement, Round 1 -> Round 5")
    ax2.set_title("Argument-type study: net drift by argument type and model\n"
                   "(positive = away from the attack, toward Bodily Autonomy)")
    ax2.legend()
    fig2.tight_layout()
    out2 = CHARTS_DIR / "argument_type_net_movement.png"
    fig2.savefig(out2, dpi=150, bbox_inches="tight")
    print(f"-> wrote {out2}")


if __name__ == "__main__":
    main()
