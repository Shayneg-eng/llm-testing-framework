"""Post cutoff event forecasting: run script.

Question: Which LLMs forecast real-world binary events best (per category: economics/finance, sports, politics/policy/world, culture/science/tech) when every outcome resolved after the models' knowledge cutoffs and each item is given a leak-checked pre-event brief?
Output:   ../runs/   (raw data, written by this script)
"""
import sys as _sys
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parents[4]          # .../LLM Testing
_sys.path.insert(0, str(ROOT / "shared"))            # so shared modules import cleanly
# from seeds import get_seed, TOPICS                 # example shared import

STUDY_DIR = _Path(__file__).resolve().parent.parent
OUTPUT_DIR = STUDY_DIR / "runs"
OUTPUT_DIR.mkdir(exist_ok=True)

# API_KEY = "..."   # hardcoded for testing per project policy; rotate before sharing


def main():
    raise NotImplementedError("write the study here")


if __name__ == "__main__":
    main()
