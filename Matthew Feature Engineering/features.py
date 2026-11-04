"""Matthew's four features for retrospective complete-recording classification.

Run from the repository root: python "Matthew Feature Engineering/features.py"
The training pipeline reads outputs/features.csv, without executing this file.
"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from estrus.contracts import export_features, validate_features
from estrus.data import ANALYSIS_DAYS, MINUTES_PER_DAY, MICE, find_root, load_signals, sha256
# Resolve sibling helpers when loaded from a notebook or through importlib, too.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wavelets import (CIRCADIAN_PERIODS_HOURS, ULTRADIAN_PERIODS_HOURS,
                      recording_band_amplitude)

OWNER = "Matthew"
CBT_THRESHOLD = 37.2  # °C; frozen from the development-only exploratory notebook.
LA_THRESHOLD = 15.0  # counts/minute; same exploratory selection.
MIN_COVERAGE = 0.80
FEATURE_NAMES = (
    "circadian_la_amplitude_next_day_delta",
    "cbt_ultradian_amplitude_h0_12",
    "cbt_fraction_above_37_2_h6_12",
    "la_fraction_above_15_h6_12",
)


def extract_features(day):
    """The two day-local fractions; the wavelet features need recording context."""
    if len(day) != MINUTES_PER_DAY or not {"cbt", "la"}.issubset(day.columns):
        raise ValueError("Expected exactly 1440 rows and cbt/la columns in day order")
    window = day.iloc[360:720]
    result = {}
    for signal, threshold, name in [
        ("cbt", CBT_THRESHOLD, FEATURE_NAMES[2]),
        ("la", LA_THRESHOLD, FEATURE_NAMES[3]),
    ]:
        values = window[signal].to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError("Infinite readings are invalid; use NaN for missing readings")
        observed = values[np.isfinite(values)]
        result[name] = (float((observed > threshold).mean())
                        if observed.size >= int(np.ceil(MIN_COVERAGE * 360)) else np.nan)
    return result


def extract_recording_features(la, cbt, *, boundary="periodic"):
    """Return all recording-day features and LA components for one mouse.

    Day indices are 1-based. The last recording day is a wavelet buffer, not a
    next-day amplitude source. The preceding day's model delta is therefore NaN.
    Untrimmed values are kept separately for boundary diagnostics only.
    """
    la, cbt = np.asarray(la, dtype=float), np.asarray(cbt, dtype=float)
    if la.ndim != 1 or cbt.ndim != 1 or la.shape != cbt.shape:
        raise ValueError("CBT and LA must be aligned one-dimensional recordings")
    circadian = recording_band_amplitude(la, CIRCADIAN_PERIODS_HOURS,
                                         nonnegative=True, boundary=boundary)
    ultradian = recording_band_amplitude(cbt, ULTRADIAN_PERIODS_HOURS,
                                         boundary=boundary)
    amplitude = circadian.mean(axis=1)  # Band maximum was taken before averaging.
    untrimmed_following = np.r_[amplitude[1:], np.nan]
    following = untrimmed_following.copy()
    following[-2:] = np.nan  # No comparison into the final buffer or beyond it.
    records = []
    for offset in range(len(amplitude)):
        start = offset * MINUTES_PER_DAY
        day = pd.DataFrame({"la": la[start:start + MINUTES_PER_DAY],
                            "cbt": cbt[start:start + MINUTES_PER_DAY]})
        records.append({
            "day_index": offset + 1,
            FEATURE_NAMES[0]: following[offset] - amplitude[offset],
            FEATURE_NAMES[1]: float(ultradian[offset, :720].mean()),
            **extract_features(day),
            "circadian_la_amplitude": amplitude[offset],
            "circadian_la_amplitude_next_day": following[offset],
            "circadian_la_amplitude_next_day_untrimmed": untrimmed_following[offset],
            "circadian_la_next_day_delta_untrimmed": untrimmed_following[offset] - amplitude[offset],
            "la_next_day_delta_excluded": offset >= len(amplitude) - 2,
        })
    return pd.DataFrame(records)


def build_features(root: Path):
    """Build the canonical export and a separate, non-model inspection table."""
    signals = load_signals(root)
    records = []
    for mouse in MICE:
        daily = extract_recording_features(signals["la"][mouse], signals["cbt"][mouse])
        daily.insert(0, "mouse_id", mouse)
        records.append(daily[daily.day_index.isin(ANALYSIS_DAYS)].copy())
    inspection = pd.concat(records, ignore_index=True)
    inspection["next_day_index"] = inspection.day_index + 1
    inspection["next_day_is_buffer"] = inspection.day_index.eq(13)
    columns = {name: f"matthew__{name}" for name in FEATURE_NAMES}
    frame = inspection[["mouse_id", "day_index", *FEATURE_NAMES]].rename(columns=columns)
    return validate_features(frame, OWNER), inspection


def feature_metadata(root, frame):
    return {
        "owner": OWNER,
        "input_policy": "retrospective_complete_recording",
        "information_cutoff": "Complete 14-day recording required; not end-of-day or online prediction",
        "day_anchor": "1-based consecutive 1440-row segments; clock/light alignment unconfirmed",
        "sample_minutes": 1,
        "analysis_days": list(ANALYSIS_DAYS),
        "transform": "analytic generalized Morse CWT, beta=5, gamma=3, peak response=2",
        "detrending": "linear, separately within each mouse's complete recording",
        "boundary": "periodic; endpoints are joined",
        "quantity": "absolute coefficient amplitude abs(W), not squared power",
        "aggregation": "maximum across sampled band periods at each minute, then time mean",
        "circadian_periods_hours": CIRCADIAN_PERIODS_HOURS.tolist(),
        "ultradian_periods_hours": ULTRADIAN_PERIODS_HOURS.tolist(),
        "circadian_comparison": "A[d+1] - A[d] for days 2-12; day 13 delta is NaN",
        "buffer_policy": "Transform all 14 days; export days 2-13. Day 14 provides wavelet context, never a model comparison amplitude",
        "edge_effects": "Exclude day 13 LA delta because day 14 amplitude is endpoint-sensitive; residual wavelet edge effects remain",
        "missingness": "Day 13 LA delta is missing for each mouse and uses fitting-fold median imputation in the model; reject nonfinite wavelet recordings and negative LA; fractions require 80% window coverage",
        "missing_values_per_feature": frame.iloc[:, 2:].isna().sum().to_dict(),
        "feature_units": dict(zip(FEATURE_NAMES, ["counts/minute", "degrees C", "fraction", "fraction"])),
        "thresholds": {"cbt_degrees_C": CBT_THRESHOLD, "la_counts_per_minute": LA_THRESHOLD},
        "threshold_provenance": "Frozen from exploratory analysis.ipynb on development mice; supervised exploratory choices, not fitted again here",
        "evaluation": "Group all days and wavelet context by mouse; validation scores are exploratory after feature design",
        "input_sha256": {f"data/inputs/{name}": sha256(root / "data/inputs" / name)
                         for name in ["fem_act.csv", "fem_temp.csv"]},
        "source_sha256": {str(path.relative_to(root)): sha256(path) for path in [
            Path(__file__).resolve(), Path(__file__).with_name("wavelets.py").resolve(),
            Path(__file__).with_name("README.md").resolve(),
            Path(__file__).with_name("input_requirements.json").resolve(),
            root / "Matthew Feature Engineering/exploratory analysis.ipynb",
        ]},
        "feature_columns": list(frame.columns[2:]),
        "versions": {name: importlib.metadata.version(name) for name in ["numpy", "scipy", "pandas"]},
    }


def main():
    root = find_root()
    frame, inspection = build_features(root)
    metadata = feature_metadata(root, frame)
    path = export_features(frame, root, OWNER)
    inspection.to_csv(path.parent / "wavelet_inspection.csv", index=False)
    metadata["feature_csv_sha256"] = sha256(path)
    (path.parent / "feature_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Validated and exported {len(frame)} rows, 4 features to {path}")
    print("Retrospective inputs: complete recordings, including next-day/future context.")
    print("Inspection amplitudes and reproducibility metadata saved beside the feature CSV.")


if __name__ == "__main__":
    main()
