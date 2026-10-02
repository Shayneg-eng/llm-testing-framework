#!/usr/bin/env python3
"""S012 wisdom_of_crowd_btc: analysis. Reads runs/, writes aggregate_* to runs/ and figures to charts/.

    python wisdom_of_crowd_btc_analysis.py            # live data in ../runs/
    python wisdom_of_crowd_btc_analysis.py --dry-run  # scratch/btc_dryrun/ (offline test data)

Scoring conventions
  * A forecaster is "correct" on a window if its predicted direction (pred > 100 up, < 100 down)
    equals the realized direction of close(T+15) vs close(T).
  * A prediction of exactly 100 (or a 5-5 vote) is a NO CALL and counts as incorrect.
  * Model accuracy is over windows where the model returned a valid prediction; missing
    predictions are reported separately. Aggregates use whichever models answered that window.
"""
import argparse
import csv
import itertools
import json
import random
import statistics
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[4]
_sys.path.insert(0, str(ROOT / "shared"))
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import btc_lib as B  # noqa: E402

STUDY_DIR = Path(__file__).resolve().parent.parent

INK, MUTED, GRID = "#1f2933", "#6b7785", "#e4e7eb"
C_MODEL, C_CROWD, C_BASE = "#4a6fa5", "#d9822b", "#9aa5b1"


def load(runs):
    wdata = json.loads((runs / "windows.json").read_text())
    windows = wdata["windows"]
    last = {}
    for line in (runs / "trials.jsonl").read_text().splitlines():
        r = json.loads(line)
        last[(r["window_id"], r["model"])] = r          # later rows supersede earlier ones
    return wdata, windows, last


def correct(pred_dir, outcome):
    return 1 if pred_dir == outcome else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    base = ROOT / "scratch" / "btc_dryrun" if a.dry_run else STUDY_DIR
    runs = base if a.dry_run else base / "runs"
    charts = (base / "charts") if a.dry_run else (STUDY_DIR / "charts")
    charts.mkdir(parents=True, exist_ok=True)

    wdata, windows, last = load(runs)
    models = sorted({m for _, m in last})
    W = len(windows)
    outcome = [w["outcome"] for w in windows]
    end_idx = np.array([w["end_price"] / w["start_price"] * 100 for w in windows])

    P = np.full((W, len(models)), np.nan)                 # predictions
    for i, w in enumerate(windows):
        for j, m in enumerate(models):
            r = last.get((w["window_id"], m))
            if r and r["pred"] is not None:
                P[i, j] = r["pred"]

    # ---- per model ----
    res = {"n_windows": W, "seed": wdata["seed"], "skipped_ties": wdata["skipped_ties"],
           "base_rate_up": sum(o == "up" for o in outcome) / W, "models": {}, "aggregates": {}, "baselines": {}}
    corr_model = {}
    for j, m in enumerate(models):
        valid = ~np.isnan(P[:, j])
        c = np.array([correct(B.direction(P[i, j]) if valid[i] else None, outcome[i]) if valid[i] else np.nan
                      for i in range(W)])
        n, k = int(valid.sum()), int(np.nansum(c))
        lo, hi = B.wilson(k, n)
        err = P[valid, j] - end_idx[valid]
        n_nocall = int(sum(1 for i in range(W) if valid[i] and B.direction(P[i, j]) is None))
        n_called = n - n_nocall
        clo, chi = B.wilson(k, n_called)
        res["models"][m] = {"n_valid": n, "n_missing": W - n, "correct": k,
                            "n_nocall": n_nocall, "accuracy_on_calls": k / n_called if n_called else None,
                            "calls_ci_lo": clo, "calls_ci_hi": chi, "calls_p_vs_50": B.binom_two_sided_p(k, n_called),
                            "accuracy": k / n if n else None, "ci_lo": lo, "ci_hi": hi,
                            "p_vs_50": B.binom_two_sided_p(k, n),
                            "mae_index": float(np.mean(np.abs(err))) if n else None}
        corr_model[m] = c

    # ---- aggregates ----
    agg_rows, agg_corr = [], {k: [] for k in ("mean", "median", "trimmed", "vote")}
    agg_vals = {k: np.full(W, np.nan) for k in ("mean", "median", "trimmed")}
    share_correct, n_used = [], []
    for i, w in enumerate(windows):
        preds = [float(x) for x in P[i] if not np.isnan(x)]
        ag = B.aggregate(preds)
        n_used.append(len(preds))
        if ag is None:
            for k in agg_corr:
                agg_corr[k].append(np.nan)
            share_correct.append(np.nan)
            agg_rows.append({"window_id": w["window_id"], "outcome": w["outcome"]})
            continue
        for k in ("mean", "median", "trimmed"):
            agg_vals[k][i] = ag[k]
            agg_corr[k].append(correct(B.direction(ag[k]), w["outcome"]))
        agg_corr["vote"].append(correct(ag["vote"], w["outcome"]))
        share_correct.append(np.mean([correct(B.direction(p), w["outcome"]) for p in preds]))
        agg_rows.append({"window_id": w["window_id"], "outcome": w["outcome"], "n_models": len(preds),
                         "ups": ag["ups"], "downs": ag["downs"], **{f"agg_{k}": round(ag[k], 4) for k in ("mean", "median", "trimmed")},
                         "vote": ag["vote"], **{m: (None if np.isnan(P[i, j]) else P[i, j]) for j, m in enumerate(models)}})
    scored = [i for i in range(W) if not np.isnan(share_correct[i])]
    for k, v in agg_corr.items():
        arr = np.array(v, dtype=float)[scored]
        n, kk = len(arr), int(arr.sum())
        lo, hi = B.wilson(kk, n)
        vv = agg_vals.get(k)
        res["aggregates"][k] = {"n_windows": n, "correct": kk, "accuracy": kk / n, "ci_lo": lo, "ci_hi": hi,
                                "p_vs_50": B.binom_two_sided_p(kk, n),
                                "mae_index": float(np.mean(np.abs(vv[scored] - end_idx[scored]))) if vv is not None else None}
    res["min_models_per_window"], res["mean_models_per_window"] = min(n_used), statistics.fmean(n_used)

    # ---- baselines ----
    up_share = res["base_rate_up"]
    mom = [correct(w["momentum"], w["outcome"]) for w in windows]
    for name, vec in (("always_up", [1 if o == "up" else 0 for o in outcome]),
                      ("always_down", [1 if o == "down" else 0 for o in outcome]), ("momentum", mom)):
        k = int(sum(vec)); lo, hi = B.wilson(k, W)
        res["baselines"][name] = {"accuracy": k / W, "ci_lo": lo, "ci_hi": hi, "p_vs_50": B.binom_two_sided_p(k, W)}
    res["baselines"]["flat_forecast_mae_index"] = float(np.mean(np.abs(100 - end_idx)))

    # ---- paired comparisons (crowd = mean aggregate) ----
    crowd = [agg_corr["mean"][i] for i in scored]
    comps = {"crowd_minus_avg_model": [share_correct[i] for i in scored],
             "crowd_minus_momentum": [mom[i] for i in scored],
             "crowd_minus_always_up": [1 if outcome[i] == "up" else 0 for i in scored]}
    best = max(res["models"], key=lambda m: res["models"][m]["accuracy"] or 0)
    comps[f"crowd_minus_best_model_POSTHOC[{best}]"] = [corr_model[best][i] if not np.isnan(corr_model[best][i]) else 0 for i in scored]
    res["paired"] = {k: B.paired_bootstrap_diff(crowd, v, n_boot=5000, seed=1) for k, v in comps.items()}

    # ---- diversity ----
    E = P - end_idx[:, None]
    cm = np.full((len(models), len(models)), np.nan)
    for x, y in itertools.product(range(len(models)), repeat=2):
        ok = ~np.isnan(E[:, x]) & ~np.isnan(E[:, y])
        if ok.sum() > 2:
            cm[x, y] = np.corrcoef(E[ok, x], E[ok, y])[0, 1]
    off = cm[~np.eye(len(models), dtype=bool)]
    dirs = np.where(np.isnan(P), np.nan, np.sign(P - 100))
    agree = [np.mean(dirs[ok, x] == dirs[ok, y]) for x, y in itertools.combinations(range(len(models)), 2)
             for ok in [~np.isnan(dirs[:, x]) & ~np.isnan(dirs[:, y])] if ok.sum()]
    res["diversity"] = {"mean_pairwise_error_correlation": float(np.nanmean(off)),
                        "mean_pairwise_direction_agreement": float(np.mean(agree))}
    # accuracy by consensus strength
    strong = [i for i in scored if max(agg_rows[i]["ups"], agg_rows[i]["downs"]) / agg_rows[i]["n_models"] >= 0.8]
    weak = [i for i in scored if i not in set(strong)]
    def acc(idx): return (float(np.mean([agg_corr["vote"][i] for i in idx])) if idx else None, len(idx))
    res["consensus"] = {"strong_ge_80pct_agree": acc(strong), "weaker": acc(weak)}

    # ---- crowd-size curve ----
    rng = random.Random(3)
    curve = []
    valid_cols = list(range(len(models)))
    for k in range(1, len(models) + 1):
        subsets = list(itertools.combinations(valid_cols, k))
        if len(subsets) > 300:
            subsets = rng.sample(subsets, 300)
        accs = []
        for s in subsets:
            cs = []
            for i in range(W):
                pv = [P[i, j] for j in s if not np.isnan(P[i, j])]
                if pv:
                    cs.append(correct(B.direction(statistics.fmean(pv)), outcome[i]))
            accs.append(np.mean(cs))
        curve.append((k, float(np.mean(accs)), float(np.percentile(accs, 10)), float(np.percentile(accs, 90))))
    res["crowd_size_curve"] = [{"k": k, "mean_acc": m, "p10": lo, "p90": hi} for k, m, lo, hi in curve]

    # ---- write data ----
    (runs / "aggregate_results.json").write_text(json.dumps(res, indent=1, default=float))
    with open(runs / "aggregate_by_model.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["model", "n_valid", "n_missing", "n_nocall", "accuracy", "ci_lo", "ci_hi", "p_vs_50",
                                         "accuracy_on_calls", "calls_ci_lo", "calls_ci_hi", "calls_p_vs_50", "mae_index"])
        for m, d in res["models"].items():
            wr.writerow([m, d["n_valid"], d["n_missing"], d["n_nocall"], d["accuracy"], d["ci_lo"], d["ci_hi"], d["p_vs_50"],
                         d["accuracy_on_calls"], d["calls_ci_lo"], d["calls_ci_hi"], d["calls_p_vs_50"], d["mae_index"]])
    keys = sorted({k for r in agg_rows for k in r}, key=lambda k: (k in models, k))
    with open(runs / "aggregate_per_window.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys); wr.writeheader(); wr.writerows(agg_rows)

    # ---- charts ----
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": GRID, "text.color": INK,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    rows = [(f"Crowd: {k}", d["accuracy"], d["ci_lo"], d["ci_hi"], C_CROWD) for k, d in res["aggregates"].items()]
    rows += [(m + (f" ({d['n_nocall']} no-calls)" if d["n_nocall"] else ""), d["accuracy"], d["ci_lo"], d["ci_hi"], C_MODEL) for m, d in sorted(res["models"].items(), key=lambda x: -(x[1]["accuracy"] or 0))]
    rows += [(f"Baseline: {k.replace('_', ' ')}", d["accuracy"], d["ci_lo"], d["ci_hi"], C_BASE) for k, d in res["baselines"].items() if isinstance(d, dict)]
    fig, ax = plt.subplots(figsize=(8, 0.34 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    for yy, (name, acc_, lo, hi, col) in zip(y, rows):
        ax.plot([lo, hi], [yy, yy], color=col, lw=1.5, solid_capstyle="round")
        ax.plot(acc_, yy, "o", color=col, ms=6, mec="white", mew=1.5)
        ax.text(1.005, yy, f"{acc_ * 100:.0f}%", transform=ax.get_yaxis_transform(), va="center", fontsize=8.5, color=INK)
    ax.axvline(0.5, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0.3, 0.8); ax.xaxis.set_major_formatter(lambda v, _: f"{v * 100:.0f}%")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(f"Direction accuracy, {W} random 15-minute windows", fontsize=11, loc="left", color=INK)
    ax.set_xlabel("dashed line = coin flip; bars = Wilson 95% CI; a no-call (prediction of exactly 100) counts as wrong")
    fig.tight_layout(); fig.savefig(charts / "accuracy_by_forecaster.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(models))); ax.set_xticklabels(models, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(models))); ax.set_yticklabels(models, fontsize=8)
    for x, y_ in itertools.product(range(len(models)), repeat=2):
        if not np.isnan(cm[x, y_]):
            ax.text(y_, x, f"{cm[x, y_]:.2f}", ha="center", va="center", fontsize=7, color="white" if cm[x, y_] > 0.55 else INK)
    fig.colorbar(im, shrink=0.8, label="correlation of price errors")
    ax.set_title("Error correlation between models", fontsize=11, loc="left")
    fig.tight_layout(); fig.savefig(charts / "error_correlation.png", dpi=160); plt.close(fig)

    ks = [c[0] for c in curve]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.fill_between(ks, [c[2] for c in curve], [c[3] for c in curve], color=C_CROWD, alpha=0.18, lw=0)
    ax.plot(ks, [c[1] for c in curve], color=C_CROWD, lw=2, marker="o", ms=5, mec="white", mew=1.2)
    ax.axhline(0.5, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v * 100:.0f}%"); ax.set_xticks(ks)
    ax.set_xlabel("models in the crowd (random subsets of the 10)"); ax.set_ylabel("direction accuracy of mean forecast")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.set_title("Does adding models help?", fontsize=11, loc="left")
    ax.text(0.99, 0.03, "line = mean over subsets; band = 10th-90th pct", transform=ax.transAxes, ha="right", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(charts / "crowd_size_curve.png", dpi=160); plt.close(fig)

    # ---- console summary ----
    print(f"windows={W} (skipped ties {wdata['skipped_ties']}), mean models/window={res['mean_models_per_window']:.1f}")
    for k, d in res["aggregates"].items():
        print(f"crowd {k:8s} acc {d['accuracy']:.3f} [{d['ci_lo']:.3f},{d['ci_hi']:.3f}] p={d['p_vs_50']:.3f} MAE {d['mae_index']}")
    for m, d in res["models"].items():
        print(f"{m:24s} acc {d['accuracy']:.3f} n={d['n_valid']} missing={d['n_missing']} p={d['p_vs_50']:.3f} | "
              f"no-calls={d['n_nocall']} acc_on_calls={d['accuracy_on_calls']:.3f} (p={d['calls_p_vs_50']:.3f})")
    print("baselines:", {k: (round(v['accuracy'], 3) if isinstance(v, dict) else round(v, 4)) for k, v in res["baselines"].items()})
    print("paired:", {k: {a_: round(b_, 3) for a_, b_ in v.items()} for k, v in res["paired"].items()})
    print("diversity:", res["diversity"], "consensus:", res["consensus"])
    print(f"wrote aggregates to {runs} and figures to {charts}")


if __name__ == "__main__":
    main()
