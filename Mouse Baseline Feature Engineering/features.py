"""Four hypothesis-led within-mouse contrasts; no labels or population fitting.

Run: python "Mouse Baseline Feature Engineering/features.py"
The established Morse helper is reused read-only; no original export is changed.
"""
from __future__ import annotations

from functools import lru_cache
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrus.contracts import export_features, validate_features
from estrus.data import ANALYSIS_DAYS, KEYS, MICE, find_root, load_signals, sha256

OWNER = "Mouse Baseline"
PREFIX = "mouse_baseline__"
MIN_COVERAGE = .8
MIN_REFERENCE_DAYS = 9  # ceil(.8 * 11 other analysis days)
DENOMINATOR_FLOOR = 1e-12  # Numerical zero, not a data-tuned threshold.
FEATURE_NAMES = (
    "cbt_mean_h6_12_minus_median",
    "la_mean_h6_12_relative_median",
    "cbt_ultradian_amplitude_h0_12_relative_median",
    "circadian_la_next_day_delta_relative_median",
)
SUMMARY_NAMES = ("cbt_mean_h6_12", "la_mean_h6_12",
                 "cbt_ultradian_amplitude_h0_12", "circadian_la_amplitude")


@lru_cache(maxsize=None)
def wavelet_helper(root):
    path = root / "Matthew Feature Engineering/wavelets.py"
    spec = importlib.util.spec_from_file_location("mouse_baseline_morse", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def daily_summaries(la, cbt, helper):
    """Use the established windows/bands; do not infer light/clock alignment."""
    la, cbt = np.asarray(la, dtype=float), np.asarray(cbt, dtype=float)
    if la.shape != (20160,) or cbt.shape != (20160,):
        raise ValueError("Expected aligned 14-day, one-minute LA and CBT recordings.")
    # The existing helper rejects missing/nonfinite wavelet samples and negative LA.
    circadian = helper.recording_band_amplitude(la, helper.CIRCADIAN_PERIODS_HOURS, nonnegative=True)
    ultradian = helper.recording_band_amplitude(cbt, helper.ULTRADIAN_PERIODS_HOURS)
    amplitude = circadian.mean(axis=1)
    following = np.r_[amplitude[1:], np.nan]
    following[-2:] = np.nan  # Preserve exclusion of the final-buffer comparison.
    rows = []
    for day in ANALYSIS_DAYS:
        offset = day - 1
        window = slice(offset * 1440 + 360, offset * 1440 + 720)
        means = {}
        for signal, values in [("cbt", cbt[window]), ("la", la[window])]:
            observed = values[np.isfinite(values)]
            means[f"{signal}_mean_h6_12"] = (float(observed.mean()) if len(observed) >= 288 else np.nan)
        rows.append({
            "day_index": day, **means,
            "cbt_ultradian_amplitude_h0_12": float(ultradian[offset, :720].mean()),
            "circadian_la_amplitude": float(amplitude[offset]),
            "circadian_la_next_day_delta": float(following[offset] - amplitude[offset]),
        })
    return pd.DataFrame(rows)


def relative_features(daily):
    """One mouse only: reference medians exclude the target day's summary."""
    required = {"day_index", *SUMMARY_NAMES, "circadian_la_next_day_delta"}
    if (not required.issubset(daily) or len(daily) != 12
            or set(daily.day_index) != set(ANALYSIS_DAYS)
            or daily.day_index.duplicated().any()):
        raise ValueError("Supply exactly one mouse's 12 analysis-day summaries, days 2–13.")
    daily = daily.sort_values("day_index").reset_index(drop=True).copy()
    if np.isinf(daily[list(required - {"day_index"})].to_numpy(dtype=float)).any():
        raise ValueError("Daily summaries cannot contain infinity.")
    rows = []
    for index, row in daily.iterrows():
        record = row.to_dict()
        references = {}
        for name in SUMMARY_NAMES:
            others = daily.loc[daily.index != index, name].dropna()
            reference = float(others.median()) if len(others) >= MIN_REFERENCE_DAYS else np.nan
            references[name] = reference
            record[f"{name}_reference_median"] = reference
            record[f"{name}_reference_count"] = len(others)
        record[PREFIX + FEATURE_NAMES[0]] = row.cbt_mean_h6_12 - references[SUMMARY_NAMES[0]]
        for feature, value, reference_name, subtract_one in [
            (FEATURE_NAMES[1], row.la_mean_h6_12, SUMMARY_NAMES[1], True),
            (FEATURE_NAMES[2], row.cbt_ultradian_amplitude_h0_12, SUMMARY_NAMES[2], True),
            (FEATURE_NAMES[3], row.circadian_la_next_day_delta, SUMMARY_NAMES[3], False),
        ]:
            reference = references[reference_name]
            record[PREFIX + feature] = (float(value / reference - int(subtract_one))
                if np.isfinite(value) and np.isfinite(reference) and reference > DENOMINATOR_FLOOR else np.nan)
        rows.append(record)
    inspection = pd.DataFrame(rows)
    # Even externally supplied summaries cannot enable the final-buffer comparison.
    inspection.loc[inspection.day_index.eq(13), PREFIX + FEATURE_NAMES[3]] = np.nan
    return inspection


def build_features(root):
    signals, helper = load_signals(root), wavelet_helper(root)
    records = []
    for mouse in MICE:
        daily = daily_summaries(signals["la"][mouse], signals["cbt"][mouse], helper)
        frame = relative_features(daily)
        frame.insert(0, "mouse_id", mouse)
        records.append(frame)
    inspection = pd.concat(records, ignore_index=True)
    columns = [PREFIX + name for name in FEATURE_NAMES]
    return validate_features(inspection[KEYS + columns], OWNER), inspection


def main():
    root = find_root()
    frame, inspection = build_features(root)
    sources = [Path(__file__).resolve(), Path(__file__).with_name("input_requirements.json"),
               root / "Matthew Feature Engineering/wavelets.py", root / "docs/features/mouse-baseline.md"]
    metadata = {
        "owner": OWNER, "information_cutoff": "retrospective_complete_recording",
        "baseline": "Per target day, median of the other 11 analysis-day summaries of the same mouse; all labels ignored",
        "analysis_days": list(ANALYSIS_DAYS), "minimum_reference_days": MIN_REFERENCE_DAYS,
        "denominator_floor": DENOMINATOR_FLOOR,
        "inspiration": "Matthew's hours-6–12 threshold/mean exploration, first-half CBT ultradian suppression, and next-day circadian LA amplitude delta",
        "units": dict(zip(FEATURE_NAMES, ["degrees C", "fractional difference", "fractional difference", "fractional amplitude change"])),
        "missing_values_per_feature": frame.iloc[:, 2:].isna().sum().to_dict(),
        "wavelet": "Unchanged Matthew Morse helper: beta=5, gamma=3, peak-2, linear detrending, periodic boundary, band max absolute amplitude then window mean",
        "input_sha256": {f"data/inputs/{name}": sha256(root / "data/inputs" / name) for name in ["fem_temp.csv", "fem_act.csv"]},
        "source_sha256": {str(path.relative_to(root)): sha256(path) for path in sources},
        "feature_columns": list(frame.columns[2:]),
    }
    path = export_features(frame, root, OWNER)
    inspection.to_csv(path.parent / "baseline_inspection.csv", index=False)
    metadata["feature_csv_sha256"] = sha256(path)
    (path.parent / "feature_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Validated and exported {len(frame)} rows, {len(FEATURE_NAMES)} relative features to {path}")
    print("Label-free, same-mouse references; complete-recording retrospective input required.")


if __name__ == "__main__":
    main()
