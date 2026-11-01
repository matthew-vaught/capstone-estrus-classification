"""Alisha's within-mouse DTW time-shift features for retrospective complete-recording classification.

Run from the repository root:
    python "Alisha Feature Engineering/features.py"
The first run computes DTW alignments (under a minute); later runs reuse outputs/cache/.
The training pipeline reads outputs/features.csv, without executing this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtw import DAYS, SCOPES, SIGNALS, load_or_compute  # noqa: E402

from estrus.contracts import export_features  # noqa: E402
from estrus.data import ANALYSIS_DAYS, find_root  # noqa: E402

OWNER = "Alisha"


def mean_over_other_days(matrix):
    """(mice, 14, 14) pairwise values -> (mice, 14) mean over each day's other 13 days."""
    others = ~np.eye(DAYS, dtype=bool)
    return np.stack([matrix[:, d, others[d]].mean(axis=1) for d in range(DAYS)], axis=1)


def build_features(shifts, mouse_ids):
    """One row per mouse and recording day 1-14, unprefixed feature columns."""
    columns = {}
    for signal in SIGNALS:
        for s in range(len(SCOPES)):
            scope = "whole" if s == 0 else f"seg{s}"
            columns[f"dtw_shift_{scope}_{signal}"] = mean_over_other_days(shifts[signal][:, s])
    index = pd.MultiIndex.from_product([mouse_ids, range(1, DAYS + 1)], names=["mouse_id", "day_index"])
    return pd.DataFrame({name: values.ravel() for name, values in columns.items()}, index=index).reset_index()


def main():
    root = find_root()
    frame = build_features(load_or_compute(root, "female", cleaned=False), [f"f{i}" for i in range(1, 14)])
    frame = frame[frame.day_index.isin(ANALYSIS_DAYS)]
    frame = frame.rename(columns={c: f"{OWNER.lower()}__{c}" for c in frame.columns[2:]})
    path = export_features(frame, root, OWNER)
    print(f"Validated and exported {path}")


if __name__ == "__main__":
    main()
