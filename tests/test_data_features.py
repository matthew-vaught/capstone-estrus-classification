from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from estrus.data import (ANALYSIS_DAYS, MINUTES_PER_DAY, canonical_keys,
                         find_root, iter_days, load_labels, load_signals,
                         proxy_labels)
from estrus.features import extract_day


def test_actual_data_shape_and_day_alignment():
    root = find_root(Path(__file__).parent)
    signals = load_signals(root)
    days = list(iter_days(root))
    assert len(days) == 156
    mouse, day, signal = days[0]
    assert (mouse, day) == ("f1", 2)
    np.testing.assert_array_equal(signal.cbt, signals["cbt"].f1.iloc[1440:2880])
    np.testing.assert_array_equal(signal.la, signals["la"].f1.iloc[1440:2880])
    assert all(len(d) == MINUTES_PER_DAY and i in ANALYSIS_DAYS for _, i, d in days)
    labels = proxy_labels()
    assert labels.is_estrus.sum() == 39
    assert set(labels[labels.is_estrus == 1].day_index) == {2, 6, 10}


def test_feature_schema_stable_with_gaps_and_all_missing_sensor():
    minutes = np.arange(1440)
    day = pd.DataFrame({"cbt": 37 + np.sin(minutes / 100), "la": np.maximum(0, 10 + 10 * np.sin(minutes / 90))})
    original = day.copy(deep=True)
    complete = extract_day(day)
    pd.testing.assert_frame_equal(day, original)
    day.loc[:10, "cbt"] = np.nan
    day["la"] = np.nan
    missing = extract_day(day)
    assert missing.keys() == complete.keys()
    assert missing["la_missing_fraction"] == 1
    assert np.isnan(missing["la_mean"])
    assert np.isfinite(missing["cbt_mean"])


def test_curated_labels_unknowns_and_validation(tmp_path):
    labels = proxy_labels()
    labels.loc[0, "is_estrus"] = np.nan
    path = tmp_path / "labels.csv"
    labels.to_csv(path, index=False)
    assert load_labels(path).is_estrus.isna().sum() == 1
    labels.loc[1, "label_source"] = ""
    labels.to_csv(path, index=False)
    with pytest.raises(ValueError, match="source"):
        load_labels(path)


def test_new_day_inference_features_reject_wrong_duration():
    with pytest.raises(ValueError, match="1440"):
        extract_day(pd.DataFrame({"cbt": [37.], "la": [0.]}))
