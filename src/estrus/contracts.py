"""Isolate contributors at a CSV boundary; never execute submitted code in training."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .data import KEYS, canonical_keys

OWNERS = ("Matthew", "Vivian", "Brandon", "Alisha")


def input_requirements(columns):
    """Keep contributors' recording context and design provenance with models."""
    columns = set(columns)
    notes = []
    if any(column.startswith("alisha__dtw_shift_") for column in columns):
        notes.append("Alisha's DTW inputs compare each day with the same mouse's other 13 recording days, "
                     "including future days and buffers 1 and 14. They require the complete 14-day recording "
                     "for retrospective classification; an isolated day's signal is insufficient. "
                     "These comparisons use no labels or other mice.")
    if columns & {
        "matthew__circadian_la_amplitude_next_day_delta",
        "matthew__cbt_ultradian_amplitude_h0_12",
    }:
        notes.append("Matthew's wavelet inputs require the complete recording, including future samples. "
                     "This is retrospective classification; a target day's raw signal alone is insufficient.")
    if "matthew__circadian_la_amplitude_next_day_delta" in columns:
        notes.append("LA change is next-day minus current-day circadian amplitude. Recording day 13 "
                     "has a missing LA change to avoid the final buffer's endpoint-sensitive amplitude; "
                     "the model fills this using a median learned from its fitting data. All target days remain included.")
    if columns & {"matthew__cbt_fraction_above_37_2_h6_12", "matthew__la_fraction_above_15_h6_12"}:
        notes.append("Matthew's 37.2 °C and 15 counts/minute thresholds were chosen during development "
                     "exploration and frozen before this run. Validation scores after feature design are exploratory.")
    return notes


def feature_path(root: Path, owner: str) -> Path:
    if owner not in OWNERS:
        raise ValueError(f"Unknown owner {owner!r}; choose {OWNERS}.")
    return root / f"{owner} Feature Engineering" / "outputs/features.csv"


def validate_features(frame: pd.DataFrame, owner: str) -> pd.DataFrame:
    prefix = owner.lower() + "__"
    if not set(KEYS).issubset(frame.columns):
        raise ValueError("Missing mouse_id or day_index key columns.")
    if frame.columns.duplicated().any():
        raise ValueError("Duplicate column names.")
    if frame.duplicated(KEYS).any() or frame[KEYS].isna().any().any():
        raise ValueError("Duplicate or missing mouse-day keys.")
    features = [c for c in frame if c not in KEYS]
    if not features or any(not re.fullmatch(prefix + r"[a-z][a-z0-9_]*", c) for c in features):
        raise ValueError(f"All feature columns must match {prefix}<lowercase_name>; omit labels and metadata.")
    if any(re.search(r"(?:^|_)(?:label|estrus|target|day_index|mouse_id|cycle_day)(?:_|$)", c[len(prefix):]) for c in features):
        raise ValueError("Label, identity, calendar-day and cycle-day features are forbidden (leakage).")
    # Full coverage prevents accidental changes to the training cohort between submissions.
    keys = canonical_keys()
    coverage = keys.merge(frame[KEYS], on=KEYS, how="outer", indicator=True)
    if len(frame) != len(keys) or not coverage._merge.eq("both").all():
        raise ValueError("Expected exactly all 156 canonical female mouse-days (f1..f13, days 2..13). Use blank feature values when unavailable.")
    frame = frame.copy()
    for column in features:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"{column}: features must be numeric or blank, not text.")
        if np.isinf(frame[column].to_numpy(dtype=float)).any():
            raise ValueError(f"{column}: infinity is invalid; use blank for unavailable values.")
        if frame[column].isna().all():
            raise ValueError(f"{column}: entirely empty feature; remove it until implemented.")
    return keys.merge(frame, on=KEYS, how="left", validate="one_to_one")


def read_features(path: Path, owner: str) -> pd.DataFrame:
    # pandas silently renames duplicate CSV headers, so reject them before parsing.
    import csv
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV headers.")
    return validate_features(pd.read_csv(path, encoding="utf-8-sig"), owner)


def export_features(frame: pd.DataFrame, root: Path, owner: str) -> Path:
    clean = validate_features(frame, owner)
    path = feature_path(root, owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    clean.to_csv(temporary, index=False)
    temporary.replace(path)
    return path


def collect_features(root: Path, baseline: pd.DataFrame, destination: Path, *, baseline_only=False):
    """Use valid team exports alone, or reference features when none are valid."""
    combined = canonical_keys()
    diagnostics = []
    for owner in OWNERS:
        path = feature_path(root, owner)
        status = {"owner": owner, "path": str(path.relative_to(root))}
        if baseline_only:
            status.update(status="ignored", message="Explicit baseline run; contributor exports are not used.")
        elif not path.exists():
            status.update(status="missing", message="No export yet; skipped.")
        else:
            try:
                frame = read_features(path, owner)
                combined = combined.merge(frame, on=KEYS, how="left", validate="one_to_one")
                status.update(status="accepted", n_features=len(frame.columns) - 2)
            except Exception as exc:
                status.update(status="invalid", message=f"{owner}: fix {path.relative_to(root)}: {exc} See docs/FEATURE_CONTRACT.md. Submission skipped.")
        diagnostics.append(status)
        print(f"[{owner}: {status['status']}] {status.get('message', str(status.get('n_features')) + ' features')}")
    if not any(item["status"] == "accepted" for item in diagnostics):
        combined = baseline.copy()
        print("Feature inputs: reference baseline only.")
    else:
        print(f"Feature inputs: {len(combined.columns) - len(KEYS)} contributor features only; reference features excluded.")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "feature_validation.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    return combined, diagnostics
