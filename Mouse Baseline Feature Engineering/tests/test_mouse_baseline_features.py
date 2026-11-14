import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from estrus.data import ANALYSIS_DAYS, MICE

spec = importlib.util.spec_from_file_location("mouse_baseline_features", Path(__file__).parents[1] / "features.py")
features = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features)


def daily():
    days = np.array(ANALYSIS_DAYS)
    return pd.DataFrame({
        "day_index": days, "cbt_mean_h6_12": 37 + .1 * days,
        "la_mean_h6_12": 2. * days, "cbt_ultradian_amplitude_h0_12": .1 * days,
        "circadian_la_amplitude": 3. * days, "circadian_la_next_day_delta": np.repeat(3., 12),
    })


def test_exact_formulas_and_reference_excludes_target():
    values = daily()
    first = features.relative_features(values).iloc[0]
    assert first.cbt_mean_h6_12_reference_median == pytest.approx(37.8)
    assert first[features.PREFIX + features.FEATURE_NAMES[0]] == pytest.approx(-.6)
    assert first[features.PREFIX + features.FEATURE_NAMES[1]] == pytest.approx(4 / 16 - 1)
    assert first[features.PREFIX + features.FEATURE_NAMES[2]] == pytest.approx(.2 / .8 - 1)
    assert first[features.PREFIX + features.FEATURE_NAMES[3]] == pytest.approx(3 / 24)
    values.loc[0, "cbt_mean_h6_12"] = 100
    altered = features.relative_features(values).iloc[0]
    assert altered.cbt_mean_h6_12_reference_median == first.cbt_mean_h6_12_reference_median
    assert altered[features.PREFIX + features.FEATURE_NAMES[0]] == pytest.approx(100 - 37.8)


def test_relative_features_remove_offsets_and_scale_without_reordering_rows():
    values = daily()
    expected = features.relative_features(values)
    values["cbt_mean_h6_12"] += 5
    values[["la_mean_h6_12", "circadian_la_amplitude", "circadian_la_next_day_delta"]] *= 7
    values["cbt_ultradian_amplitude_h0_12"] *= 3
    actual = features.relative_features(values.sample(frac=1, random_state=4))
    cols = [features.PREFIX + name for name in features.FEATURE_NAMES]
    np.testing.assert_allclose(actual[cols], expected[cols], atol=1e-13, equal_nan=True)
    assert actual.day_index.tolist() == list(ANALYSIS_DAYS)


def test_missing_references_zero_denominators_and_final_day_preserve_rows():
    values = daily()
    values.loc[:1, "cbt_mean_h6_12"] = np.nan
    result = features.relative_features(values)
    assert result.loc[2, "cbt_mean_h6_12_reference_count"] == 9
    assert np.isfinite(result.loc[2, features.PREFIX + features.FEATURE_NAMES[0]])
    values.loc[2, "cbt_mean_h6_12"] = np.nan
    values["la_mean_h6_12"] = 0.
    result = features.relative_features(values)
    assert result.loc[3, "cbt_mean_h6_12_reference_count"] == 8
    assert np.isnan(result.loc[3, features.PREFIX + features.FEATURE_NAMES[0]])
    assert result[features.PREFIX + features.FEATURE_NAMES[1]].isna().all()
    assert np.isnan(result.iloc[-1][features.PREFIX + features.FEATURE_NAMES[3]])
    assert len(result) == 12 and not np.isinf(result.to_numpy()).any()
    with pytest.raises(ValueError, match="12 analysis-day"):
        features.relative_features(values.iloc[:-1])


def fake_helper():
    def band(values, periods, **kwargs):
        return np.asarray(values).reshape(14, 1440)
    return SimpleNamespace(recording_band_amplitude=band, CIRCADIAN_PERIODS_HOURS=[24], ULTRADIAN_PERIODS_HOURS=[2])


def test_summaries_use_exact_windows_and_preserve_final_buffer_exclusion():
    la = np.repeat(np.arange(1., 15), 1440)
    cbt = np.tile(np.arange(1440, dtype=float), 14)
    values = features.daily_summaries(la, cbt, fake_helper())
    assert values.day_index.tolist() == list(ANALYSIS_DAYS)
    assert values.iloc[0].cbt_mean_h6_12 == np.arange(360, 720).mean()
    assert values.iloc[0].la_mean_h6_12 == 2
    assert values.iloc[0].cbt_ultradian_amplitude_h0_12 == np.arange(720).mean()
    assert values.iloc[0].circadian_la_amplitude == 2
    assert values.iloc[0].circadian_la_next_day_delta == 1
    assert np.isnan(values.iloc[-1].circadian_la_next_day_delta)


def test_build_is_mouse_local_and_does_not_require_labels(tmp_path, monkeypatch):
    values = np.repeat(np.arange(1., 15), 1440)
    signals = {
        "la": pd.DataFrame({mouse: values * (i + 1) for i, mouse in enumerate(MICE)}),
        "cbt": pd.DataFrame({mouse: 36 + values / 10 + i for i, mouse in enumerate(MICE)}),
    }
    monkeypatch.setattr(features, "load_signals", lambda _: signals)
    monkeypatch.setattr(features, "wavelet_helper", lambda _: fake_helper())
    original, inspection = features.build_features(tmp_path)
    assert original.shape == (156, 6)
    assert original.iloc[:, -1].isna().sum() == 13
    assert inspection.shape[0] == 156
    signals["cbt"]["f3"] *= 2
    signals["la"]["f3"] = signals["la"]["f3"] ** 2
    altered, _ = features.build_features(tmp_path)
    pd.testing.assert_frame_equal(original[original.mouse_id.ne("f3")], altered[altered.mouse_id.ne("f3")])
    # No label files exist in this temporary checkout, and none are requested.
