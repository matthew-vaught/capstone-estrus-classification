"""Small day-local LA–CBT descriptors inspired by Burks and Smarr (2026).

No recursive simulator, optimized dynamical parameters, staging labels, or
population reference is used. Run this extractor explicitly from the root.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrus.contracts import export_features, validate_features
from estrus.data import find_root, iter_days, sha256

OWNER = "LA CBT Relationship"
PREFIX = "la_cbt_relationship__"
BIN_MINUTES = 5
HORIZON_BINS = 2
MIN_DAY_BINS = 231  # ceil(.8 * 288), jointly observed bins
MIN_CORRELATION_PAIRS = 36
MIN_CONDITIONAL_PAIRS = 6
MIN_DIRECTION_PAIRS = 3
NUMERICAL_ZERO = 1e-12
PAPER_DOI = "10.1038/s41598-025-31953-8"
FEATURE_NAMES = (
    "activity_warming_partial_corr_10min",
    "quiet_cooling_weighted_change_10min",
    "low_activity_cbt_excess_h6_12",
    "activity_hysteresis_cbt_gap",
)


def bin_day(day):
    """Retain the time grid; a bin needs four observed minutes per signal."""
    if len(day) != 1440 or not {"la", "cbt"}.issubset(day.columns):
        raise ValueError("Expected one aligned 1440-minute day with la and cbt columns.")
    result = {}
    for name in ["la", "cbt"]:
        values = day[name].to_numpy(dtype=float)
        if np.isinf(values).any() or (name == "la" and (values < 0).any()):
            raise ValueError("Infinite readings and negative LA are invalid; missing readings must be NaN.")
        bins = values.reshape(288, BIN_MINUTES)
        count = np.isfinite(bins).sum(axis=1)
        result[name] = np.divide(np.nansum(bins, axis=1), count,
                                 out=np.full(288, np.nan), where=count >= 4)
    return result["la"], result["cbt"]


def weighted_mean(values, weights, minimum):
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if valid.sum() < minimum or weights[valid].sum() <= NUMERICAL_ZERO:
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def partial_correlation(activity, change, temperature):
    """Remove a linear association with current CBT before correlating changes.

    This is a descriptive per-day projection, not a physiological model fit.
    """
    valid = np.isfinite(activity) & np.isfinite(change) & np.isfinite(temperature)
    if valid.sum() < MIN_CORRELATION_PAIRS:
        return np.nan
    a, d, t = (x[valid] - x[valid].mean() for x in [activity, change, temperature])
    norm_t = float(t @ t)
    if norm_t > NUMERICAL_ZERO:
        a, d = a - t * (t @ a) / norm_t, d - t * (t @ d) / norm_t
    denominator = float(np.linalg.norm(a) * np.linalg.norm(d))
    return float(np.clip(a @ d / denominator, -1, 1)) if denominator > NUMERICAL_ZERO else np.nan


def hysteresis_gap(activity, temperature):
    """Compare falling/rising activity at broadly matched current LA levels."""
    observed = activity[np.isfinite(activity)]
    if not len(observed):
        return np.nan, 0
    edges = np.unique(np.quantile(observed, [.25, .5, .75]))
    current, delta, temp = activity[1:], np.diff(activity), temperature[1:]
    valid = np.isfinite(current) & np.isfinite(delta) & np.isfinite(temp)
    bucket = np.searchsorted(edges, current, side="right")
    gaps, weights = [], []
    for index in range(len(edges) + 1):
        falling = valid & (bucket == index) & (delta < 0)
        rising = valid & (bucket == index) & (delta > 0)
        if min(falling.sum(), rising.sum()) >= MIN_DIRECTION_PAIRS:
            gaps.append(float(temp[falling].mean() - temp[rising].mean()))
            weights.append(int(min(falling.sum(), rising.sum())))
    return (float(np.average(gaps, weights=weights)), len(gaps)) if gaps else (np.nan, 0)


def extract_features(day):
    """Return four fixed descriptors and separate coverage diagnostics."""
    activity, temperature = bin_day(day)
    result = {name: np.nan for name in FEATURE_NAMES}
    coverage = int((np.isfinite(activity) & np.isfinite(temperature)).sum())
    diagnostics = {"jointly_observed_bins": coverage}
    if coverage < MIN_DAY_BINS:
        return result, diagnostics
    # A[t] and A[t+1] span the ten minutes before the ending CBT sample T[t+2].
    exposure = (activity[:-2] + activity[1:-1]) / 2
    change = temperature[2:] - temperature[:-2]
    current = temperature[:-2]
    result[FEATURE_NAMES[0]] = partial_correlation(exposure, change, current)

    quiet_cut = float(np.nanquantile(activity, .25))
    low_temperature = float(np.nanquantile(temperature, .1))
    quiet = (activity[:-2] <= quiet_cut) & (activity[1:-1] <= quiet_cut)
    thermal_weights = np.where(quiet, np.maximum(current - low_temperature, 0), 0.)
    result[FEATURE_NAMES[1]] = weighted_mean(change, thermal_weights, MIN_CONDITIONAL_PAIRS)

    # Continuous low-activity weighting avoids discarding windows without zeros.
    recent = np.r_[np.nan, (activity[:-1] + activity[1:]) / 2]
    quiet_weights = 1 / (1 + recent)  # activity in counts/minute; no learned scale
    hours = np.arange(288) * BIN_MINUTES / 60
    window = (hours >= 6) & (hours < 12)
    result[FEATURE_NAMES[2]] = (
        weighted_mean(temperature[window], quiet_weights[window], MIN_CONDITIONAL_PAIRS)
        - weighted_mean(temperature[~window], quiet_weights[~window], MIN_CONDITIONAL_PAIRS))
    result[FEATURE_NAMES[3]], matched = hysteresis_gap(activity, temperature)
    diagnostics.update({
        "quiet_activity_q25": quiet_cut, "cbt_q10": low_temperature,
        "warming_complete_pairs": int((np.isfinite(exposure) & np.isfinite(change) & np.isfinite(current)).sum()),
        "quiet_weighted_complete_pairs": int((np.isfinite(change) & np.isfinite(thermal_weights) & (thermal_weights > 0)).sum()),
        "hysteresis_matched_buckets": matched,
    })
    return result, diagnostics


def build_features(root):
    rows, inspection = [], []
    for mouse, day_index, day in iter_days(root):
        values, diagnostics = extract_features(day)
        keys = {"mouse_id": mouse, "day_index": day_index}
        rows.append({**keys, **{PREFIX + name: value for name, value in values.items()}})
        inspection.append({**keys, **diagnostics})
    return validate_features(pd.DataFrame(rows), OWNER), pd.DataFrame(inspection)


def main():
    root = find_root()
    frame, inspection = build_features(root)
    sources = [Path(__file__).resolve(), Path(__file__).with_name("input_requirements.json"),
               root / "docs/features/la-cbt-relationship.md"]
    metadata = {
        "owner": OWNER, "paper_doi": PAPER_DOI, "input_policy": "complete_target_day_only",
        "method": "Descriptive conditional, lagged, and matched-state statistics; not a reproduction of the paper's simulator",
        "parameters": {"bin_minutes": BIN_MINUTES, "horizon_bins": HORIZON_BINS,
                       "minimum_joint_day_bins": MIN_DAY_BINS, "minimum_correlation_pairs": MIN_CORRELATION_PAIRS,
                       "minimum_conditional_pairs": MIN_CONDITIONAL_PAIRS, "minimum_direction_pairs": MIN_DIRECTION_PAIRS,
                       "quiet_quantile": .25, "temperature_reference_quantile": .1,
                       "hysteresis_activity_quantiles": [.25, .5, .75]},
        "units": dict(zip(FEATURE_NAMES, ["correlation", "degrees C per 10-minute interval", "degrees C", "degrees C"])),
        "feature_columns": list(frame.columns[2:]),
        "missing_values_per_feature": frame.iloc[:, 2:].isna().sum().to_dict(),
        "design": "Four definitions frozen before supervised model evaluation. Conditional-coverage checks used development mice only and no labels.",
        "input_sha256": {f"data/inputs/{name}": sha256(root / "data/inputs" / name) for name in ["fem_act.csv", "fem_temp.csv"]},
        "source_sha256": {str(path.relative_to(root)): sha256(path) for path in sources},
    }
    paper = root / "data/Important Data Files/estrus_detection_paper.pdf"
    if paper.exists():
        metadata["supplied_paper_sha256"] = sha256(paper)
    path = export_features(frame, root, OWNER)
    inspection.to_csv(path.parent / "relationship_inspection.csv", index=False)
    metadata["feature_csv_sha256"] = sha256(path)
    (path.parent / "feature_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Validated and exported {len(frame)} rows, {len(FEATURE_NAMES)} LA–CBT relationship features to {path}")
    print("No labels, stage-specific fits, other days/mice, or light-phase assumptions enter extraction.")


if __name__ == "__main__":
    main()
