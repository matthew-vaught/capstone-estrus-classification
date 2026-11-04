"""Day-local, label-free reference features; all fitted preprocessing lives in CV."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pywt

from .data import KEYS, canonical_keys, iter_days


def _longest_run(mask):
    padded = np.r_[False, mask, False].astype(int)
    return float(np.max(np.flatnonzero(np.diff(padded) == -1) - np.flatnonzero(np.diff(padded) == 1), initial=0))


def extract_day(day: pd.DataFrame) -> dict[str, float]:
    """Features use only this day's 1440 readings; no labels or other animals.

    Interpolation is within-day, limited to 10-minute gaps. Remaining gaps
    use that day's median solely for signal transforms, never across days.
    Morlet 1-3h power is inspired by the paper, not its exact Morse analysis.
    """
    if len(day) != 1440 or not {"cbt", "la"}.issubset(day.columns):
        raise ValueError("A single day must have exactly 1440 rows and numeric cbt/la columns.")
    if np.isinf(day[["cbt", "la"]].to_numpy(dtype=float)).any():
        raise ValueError("Day measurements contain infinity; use NaN for unavailable values.")
    result = {}
    cleaned = {}
    for name in ["cbt", "la"]:
        raw = day[name].astype(float)
        result[f"{name}_missing_fraction"] = float(raw.isna().mean())
        if raw.notna().sum() < 720:
            # Keep schema even for largely unavailable sensor days.
            values = np.full(1440, np.nan)
        else:
            values = raw.interpolate(limit=10, limit_area="inside").fillna(raw.median()).to_numpy()
        cleaned[name] = values
        if np.isnan(values).all():
            for key in ["mean", "std", "iqr", "range", "high_fraction", "plateau_minutes", "roughness", "harmonic24_amplitude", "harmonic24_sin", "harmonic24_cos", "first_minus_second_half", "ur_power", "ur_first_minus_second_half"]:
                result[f"{name}_{key}"] = np.nan
            continue
        q10, q25, q75, q90 = np.quantile(values, [.1, .25, .75, .9])
        result.update({
            f"{name}_mean": float(values.mean()), f"{name}_std": float(values.std()),
            f"{name}_iqr": float(q75 - q25), f"{name}_range": float(values.max() - values.min()),
            f"{name}_high_fraction": float((values >= q10 + .75 * (q90 - q10)).mean()),
            f"{name}_plateau_minutes": _longest_run(pd.Series(values).rolling(31, center=True, min_periods=1).mean().to_numpy() >= q10 + .75 * (q90 - q10)),
            f"{name}_roughness": float(np.mean(np.abs(np.diff(values)))),
            f"{name}_first_minus_second_half": float(values[:720].mean() - values[720:].mean()),
        })
        t = np.arange(1440) * 2 * np.pi / 1440
        sine, cosine = [float(2 * np.mean((values - values.mean()) * basis)) for basis in (np.sin(t), np.cos(t))]
        result[f"{name}_harmonic24_sin"] = sine
        result[f"{name}_harmonic24_cos"] = cosine
        result[f"{name}_harmonic24_amplitude"] = float(np.hypot(sine, cosine))
        # Downsample to 5-min bins; center wavelet only on current day.
        binned = values.reshape(-1, 5).mean(axis=1)
        periods = np.linspace(60, 180, 13)
        wavelet = "cmor1.5-1.0"
        scales = pywt.central_frequency(wavelet) * periods / 5
        coef, _ = pywt.cwt(binned - binned.mean(), scales, wavelet, sampling_period=5)
        power = (np.abs(coef) ** 2).mean(axis=0)
        # Discard 3h at either edge. This reduces, but cannot eliminate, edge effects.
        result[f"{name}_ur_power"] = float(power[36:-36].mean())
        result[f"{name}_ur_first_minus_second_half"] = float(power[36:144].mean() - power[144:-36].mean())
    x, y = cleaned["cbt"], cleaned["la"]
    result["cbt_la_correlation"] = float(np.corrcoef(x, y)[0, 1]) if np.isfinite(x).all() and np.isfinite(y).all() and x.std() > 0 and y.std() > 0 else np.nan
    return result


def baseline_features(root):
    """Extract the reference schema for all canonical days in raw recordings."""
    return pd.DataFrame([
        {"mouse_id": mouse, "day_index": day, **{"baseline__" + key: value for key, value in extract_day(signal).items()}}
        for mouse, day, signal in iter_days(root)
    ])


def assemble_features(root, destination, *, baseline_only=False):
    """Join validated exports; compute reference features only when needed.

    No contributor code is executed and no contributor files are written.
    Validation diagnostics are saved at ``destination`` by the contract loader.
    """
    from .contracts import collect_features

    features, diagnostics = collect_features(
        root, canonical_keys(), destination, baseline_only=baseline_only
    )
    if len(features.columns) == len(KEYS):
        features = baseline_features(root)
    return features, diagnostics
