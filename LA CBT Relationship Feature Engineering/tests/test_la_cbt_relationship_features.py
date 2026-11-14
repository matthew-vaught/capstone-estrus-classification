import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from estrus.data import canonical_keys

spec = importlib.util.spec_from_file_location("la_cbt_features", Path(__file__).parents[1] / "features.py")
features = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features)


def day_from_bins(activity, temperature):
    return pd.DataFrame({"la": np.repeat(activity, 5), "cbt": np.repeat(temperature, 5)})


def variable_day():
    time = np.arange(288)
    activity = np.maximum(0, 8 + 12 * np.sin(time / 11) + 3 * np.cos(time / 3))
    temperature = 37 + .3 * np.sin(time / 30) + .02 * np.roll(activity, 2)
    return day_from_bins(activity, temperature)


def test_partial_correlation_controls_current_temperature():
    rng = np.random.default_rng(12)
    current = np.linspace(35, 39, 120)
    activity = 5 * current + rng.normal(size=120)
    change = 2 * activity - 20 * current
    assert features.partial_correlation(activity, change, current) == pytest.approx(1)
    assert features.partial_correlation(activity, -change, current) == pytest.approx(-1)
    assert np.isnan(features.partial_correlation(np.ones(120), change, current))
    assert np.isnan(features.partial_correlation(activity[:10], change[:10], current[:10]))


def test_quiet_cooling_is_ten_minute_change_and_offset_invariant():
    activity = np.zeros(288)
    temperature = 40 - .01 * np.arange(288)
    values, _ = features.extract_features(day_from_bins(activity, temperature))
    assert values['quiet_cooling_weighted_change_10min'] == pytest.approx(-.02)
    shifted, _ = features.extract_features(day_from_bins(activity, temperature + 10))
    for name in features.FEATURE_NAMES:
        np.testing.assert_allclose(values[name], shifted[name], atol=1e-12, equal_nan=True)


def test_low_activity_contrast_uses_window_and_downweights_high_activity():
    activity = np.zeros(288)
    temperature = np.repeat(37., 288)
    temperature[72:144] = 38
    temperature[90] = 42
    activity[89:91] = 100
    values, _ = features.extract_features(day_from_bins(activity, temperature))
    recent = np.r_[np.nan, (activity[:-1] + activity[1:]) / 2]
    weights = 1 / (1 + recent)
    expected = np.average(temperature[72:144], weights=weights[72:144]) - 37
    assert values['low_activity_cbt_excess_h6_12'] == pytest.approx(expected)
    assert values['low_activity_cbt_excess_h6_12'] < temperature[72:144].mean() - 37


def test_hysteresis_matches_direction_at_current_activity():
    activity = np.tile([0, 1, 2, 3, 4, 3, 2, 1], 40).astype(float)
    falling = np.r_[False, np.diff(activity) < 0]
    temperature = 37 + 2 * falling
    gap, buckets = features.hysteresis_gap(activity, temperature)
    assert gap == pytest.approx(2) and buckets > 0
    gap, buckets = features.hysteresis_gap(np.zeros(288), np.ones(288))
    assert np.isnan(gap) and buckets == 0


def test_missing_bins_keep_the_grid_and_degenerate_states_remain_missing():
    day = variable_day()
    day.loc[:1, 'la'] = np.nan
    activity, temperature = features.bin_day(day)
    assert len(activity) == 288 and np.isnan(activity[0])
    assert activity[1] == day.la.iloc[5:10].mean()
    day.loc[:600, ['la', 'cbt']] = np.nan
    values, diagnostic = features.extract_features(day)
    assert diagnostic['jointly_observed_bins'] < features.MIN_DAY_BINS
    assert all(np.isnan(v) for v in values.values())
    values, _ = features.extract_features(day_from_bins(np.zeros(288), np.repeat(37., 288)))
    assert values['low_activity_cbt_excess_h6_12'] == 0
    assert all(np.isnan(values[name]) for name in features.FEATURE_NAMES if name != 'low_activity_cbt_excess_h6_12')
    with pytest.raises(ValueError, match='1440'):
        features.extract_features(day.iloc[:-1])
    with pytest.raises(ValueError, match='negative LA'):
        features.extract_features(day.assign(la=-1))


def test_build_uses_only_its_target_day_and_ignores_labels(tmp_path, monkeypatch):
    keys = canonical_keys()
    days = {(r.mouse_id, r.day_index): variable_day() for r in keys.itertuples(index=False)}
    monkeypatch.setattr(features, 'iter_days', lambda _: ((mouse, day, data) for (mouse, day), data in days.items()))
    original, _ = features.build_features(tmp_path)
    day = days[('f3', 10)]
    before, _ = features.extract_features(day)
    after, _ = features.extract_features(day.assign(is_estrus=1))
    assert before == after
    days[('f3', 10)] = day.assign(cbt=day.cbt + np.linspace(0, 10, 1440), la=day.la ** 2)
    changed, _ = features.build_features(tmp_path)
    keep = ~(original.mouse_id.eq('f3') & original.day_index.eq(10))
    pd.testing.assert_frame_equal(original[keep], changed[keep])
    assert original.shape == (156, 6)
    assert not np.isinf(changed.iloc[:, 2:].to_numpy()).any()
