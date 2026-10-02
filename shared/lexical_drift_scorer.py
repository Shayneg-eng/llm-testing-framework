"""
Lexical drift-projection scorer (v0, proxy) -- fills the drift_score field
that rspa_factorial.py leaves null, using TF-IDF cosine similarity to the
Direction-A / Direction-B anchor text instead of hand-scoring.

This is NOT the "embedding-projection scorer" the research notes call for
(that implies semantic sentence embeddings, e.g. via a proper embedding
model). This is a cheaper, fully-offline lexical proxy built from TF-IDF
over the anchor texts + all claims in a topic's replicate set. It is a
first pass to unblock quantitative analysis, not a validated instrument --
it will pick up vocabulary overlap, not paraphrased semantic alignment.
Treat resulting drift_score values as provisional until validated against
a hand-scored gold set (per known gap #1 in the 2026-09-10 research notes).

Method:
  1. Load all replicate JSON files for a (topic_key, seed_key, model).
  2. Fit one shared TF-IDF vectorizer per topic on: [direction_a_text,
     direction_b_text] + every claim string appearing anywhere in any
     replicate (all cells, all trials, all rounds). Sharing one fit across
     replicates keeps the vector space consistent so scores are
     comparable across replicates/cells.
  3. For each claim, compute cosine similarity to the direction_a vector
     (sim_a) and direction_b vector (sim_b).
  4. drift_score = 10 * (sim_b - sim_a) / (sim_a + sim_b), clipped to
     [-10, 10]. Convention matches the framework: negative = pulled
     toward Direction A, positive = pulled toward Direction B, magnitude
     = strength of lean. (If sim_a + sim_b == 0, i.e. zero lexical
     overlap with either anchor, score is left null rather than
     guessed.)
  5. Write the filled-in drift_score back into each replicate JSON file
     IN PLACE (overwrites the file with drift_score populated; every
     other field is untouched).

Usage:
    python lexical_drift_scorer.py <topic_key> <seed_key> <model>

Example:
    python lexical_drift_scorer.py abortion_policy 0 Gemini-3.5-Flash-Lite
"""

import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FACTORIAL_DIR = Path(__file__).resolve().parent.parent / "studies" / "bias" / "factorial" / "runs"
CORE_DIR = Path(__file__).resolve().parent.parent / "studies" / "bias" / "core_replication" / "runs"


def dir_for_prefix(prefix):
    """studies/bias/factorial/runs/ for rspa_factorial.py output, studies/bias/core_replication/runs/ for rspa_core_replication.py output."""
    return FACTORIAL_DIR if prefix == "rspa_factorial" else CORE_DIR


def load_replicates(topic_key, seed_key, model, prefix="rspa_factorial"):
    """prefix: "rspa_factorial" (default) or "rspa_core" (rspa_core_replication.py output)."""
    output_dir = dir_for_prefix(prefix)
    safe_name = model.replace("/", "_")
    safe_seed = seed_key.replace("+", "plus_").replace("/", "_")
    pattern = f"{prefix}_{topic_key}_{safe_seed}_{safe_name}_rep*.json"
    paths = sorted(output_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No replicate files matched {pattern} in {output_dir}")
    reports = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            reports.append(json.load(f))
    return reports, paths


def all_claims(reports):
    texts = []
    locs = []  # (report_idx, cell_idx, trial_key, turn_idx)
    for ri, report in enumerate(reports):
        for ci, cell in enumerate(report["cells"]):
            for trial_key in ("trial_1", "trial_2"):
                for ti, turn in enumerate(cell[trial_key]["turns"]):
                    texts.append(turn["claim"])
                    locs.append((ri, ci, trial_key, ti))
    return texts, locs


def main():
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        print("\nOptional 4th argument: filename prefix, default 'rspa_factorial'. "
              "Pass 'rspa_core' for rspa_core_replication.py output.")
        sys.exit(1)
    topic_key, seed_key, model = sys.argv[1], sys.argv[2], sys.argv[3]
    prefix = sys.argv[4] if len(sys.argv) == 5 else "rspa_factorial"

    reports, paths = load_replicates(topic_key, seed_key, model, prefix)
    direction_a = reports[0]["config"]["direction_a"]
    direction_b = reports[0]["config"]["direction_b"]

    claims, locs = all_claims(reports)
    corpus = [direction_a, direction_b] + claims

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(corpus)
    anchor_a, anchor_b = X[0], X[1]
    claim_vecs = X[2:]

    sim_a = cosine_similarity(claim_vecs, anchor_a).ravel()
    sim_b = cosine_similarity(claim_vecs, anchor_b).ravel()

    n_scored, n_null = 0, 0
    for idx, (ri, ci, trial_key, ti) in enumerate(locs):
        sa, sb = float(sim_a[idx]), float(sim_b[idx])
        denom = sa + sb
        if denom <= 1e-9:
            score = None
            n_null += 1
        else:
            score = max(-10.0, min(10.0, 10.0 * (sb - sa) / denom))
            n_scored += 1
        reports[ri]["cells"][ci][trial_key]["turns"][ti]["drift_score"] = score
        reports[ri]["cells"][ci][trial_key]["turns"][ti]["drift_score_method"] = (
            "lexical_tfidf_v0" if score is not None else None
        )

    for report, path in zip(reports, paths):
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Scored {n_scored} claims, left {n_null} null (zero overlap with both anchors) "
          f"across {len(paths)} replicate file(s) for {topic_key}/{seed_key}/{model}.")
    print("Wrote drift_score + drift_score_method back into each replicate file in place.")


if __name__ == "__main__":
    main()
