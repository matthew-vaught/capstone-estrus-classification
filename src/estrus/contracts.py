"""Isolate contributors at a CSV boundary; never execute submitted code in training."""
from __future__ import annotations

import json
import re
from fnmatch import fnmatchcase
from pathlib import Path

import numpy as np
import pandas as pd

from .data import KEYS, canonical_keys, find_root

DEFAULT_OWNERS = ("Matthew", "Vivian", "Brandon", "Alisha")
OWNERS = (*DEFAULT_OWNERS, "Mouse Baseline", "LA CBT Relationship")


def feature_prefix(owner):
    return owner.lower().replace(" ", "_") + "__"


def resolve_owners(owners=None):
    """Explicit feature-family lists enable experiments without changing defaults."""
    if owners is None:
        return DEFAULT_OWNERS
    if (not isinstance(owners, (list, tuple)) or not owners
            or any(not isinstance(owner, str) or owner not in OWNERS for owner in owners)
            or len(set(owners)) != len(owners)):
        raise ValueError(f"feature_owners must be a nonempty list of distinct registered names: {OWNERS}.")
    return tuple(owners)


def input_requirements(columns, root: Path | None = None):
    """Read matching notes from contributors' optional input_requirements.json.

    Definitions stay with their owner; training reads JSON without importing
    extraction code. An explicit root supports running against another checkout.
    """
    columns = set(columns)
    notes = []
    for owner in OWNERS:
        prefix = feature_prefix(owner)
        if not any(column.startswith(prefix) for column in columns):
            continue
        if root is None:
            root = find_root(Path(__file__).parent)
        path = root / f"{owner} Feature Engineering" / "input_requirements.json"
        if not path.exists():
            continue
        rules = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rules, list):
            raise ValueError(f"{path}: expected a list of feature requirement rules.")
        for rule in rules:
            if (not isinstance(rule, dict) or set(rule) != {"features", "note"}
                    or not isinstance(rule["features"], list) or not rule["features"]
                    or not all(isinstance(pattern, str) and pattern.startswith(prefix)
                               for pattern in rule["features"])
                    or not isinstance(rule["note"], str) or not rule["note"].strip()):
                raise ValueError(f"{path}: each rule needs owner-prefixed features and a nonempty note.")
            if any(fnmatchcase(column, pattern) for column in columns for pattern in rule["features"]):
                notes.append(rule["note"])
    return notes


def feature_path(root: Path, owner: str) -> Path:
    """Locate one owner's handoff CSV without importing their extractor."""
    if owner not in OWNERS:
        raise ValueError(f"Unknown owner {owner!r}; choose {OWNERS}.")
    return root / f"{owner} Feature Engineering" / "outputs/features.csv"


def validate_features(frame: pd.DataFrame, owner: str) -> pd.DataFrame:
    """Validate coverage, keys, names, and numeric values; return canonical order.

    Reject the whole export on a schema violation. Partial numeric missingness
    is retained for training-fold imputation, without modifying the input frame.
    """
    prefix = feature_prefix(owner)
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
    """Load and validate a handoff, rejecting duplicate headers before parsing."""
    # pandas silently renames duplicate CSV headers, so reject them before parsing.
    import csv
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV headers.")
    return validate_features(pd.read_csv(path, encoding="utf-8-sig"), owner)


def export_features(frame: pd.DataFrame, root: Path, owner: str) -> Path:
    """Validate then atomically replace an owner's CSV; preserve it on failure."""
    clean = validate_features(frame, owner)
    path = feature_path(root, owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    clean.to_csv(temporary, index=False)
    temporary.replace(path)
    return path


def collect_features(root: Path, baseline: pd.DataFrame, destination: Path, *, baseline_only=False, owners=None):
    """Use valid team exports alone, or reference features when none are valid."""
    combined = canonical_keys()
    diagnostics = []
    for owner in resolve_owners(owners):
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
