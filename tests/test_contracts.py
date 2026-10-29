import numpy as np
import pandas as pd
import pytest

from estrus.contracts import (collect_features, export_features, feature_path,
                              read_features, validate_features)
from estrus.data import canonical_keys


def valid(owner="Vivian"):
    frame = canonical_keys()
    frame[f"{owner.lower()}__power"] = np.arange(len(frame), dtype=float)
    return frame


def test_shuffled_rows_are_joined_by_key_not_position(tmp_path):
    frame = valid().sample(frac=1, random_state=3)
    path = export_features(frame, tmp_path, "Vivian")
    actual = read_features(path, "Vivian")
    pd.testing.assert_frame_equal(actual, valid())


@pytest.mark.parametrize("corruption,match", [
    (lambda x: pd.concat([x, x.iloc[:1]]), "Duplicate"),
    (lambda x: x.iloc[1:], "156"),
    (lambda x: x.assign(day_index=1), "Duplicate"),
    (lambda x: x.rename(columns={"vivian__power": "matthew__power"}), "match"),
    (lambda x: x.assign(is_estrus=1), "match"),
    (lambda x: x.assign(vivian__cycle_day=2), "forbidden"),
    (lambda x: x.assign(vivian__power=np.inf), "infinity"),
    (lambda x: x.assign(vivian__power=np.nan), "empty"),
    (lambda x: x.assign(vivian__power="oops"), "numeric"),
])
def test_contract_rejects_malformed_exports(corruption, match):
    with pytest.raises(ValueError, match=match):
        validate_features(corruption(valid()), "Vivian")


def test_missing_values_allowed_and_failed_export_keeps_previous_file(tmp_path):
    frame = valid()
    frame.loc[0, "vivian__power"] = np.nan
    path = export_features(frame, tmp_path, "Vivian")
    previous = path.read_bytes()
    with pytest.raises(ValueError):
        export_features(frame.iloc[:2], tmp_path, "Vivian")
    assert path.read_bytes() == previous


def test_mixed_submissions_skip_invalid_and_missing_owners(tmp_path):
    baseline = canonical_keys().assign(baseline__mean=1.)
    export_features(valid(), tmp_path, "Vivian")
    invalid = feature_path(tmp_path, "Brandon")
    invalid.parent.mkdir(parents=True)
    invalid.write_text("mouse_id,day_index,brandon__broken\nf1,2,nope\n")
    combined, statuses = collect_features(tmp_path, baseline, tmp_path / "results")
    assert {s["owner"]: s["status"] for s in statuses} == {
        "Matthew": "missing", "Vivian": "accepted", "Brandon": "invalid", "Alisha": "missing"}
    assert len(combined) == 156
    assert "vivian__power" in combined and "brandon__broken" not in combined
    assert "baseline__mean" not in combined
    assert (tmp_path / "results/feature_validation.json").exists()


def test_no_valid_exports_falls_back_to_baseline(tmp_path):
    baseline = canonical_keys().assign(baseline__mean=37.)
    path = feature_path(tmp_path, "Brandon")
    path.parent.mkdir(parents=True)
    path.write_text("mouse_id,day_index,brandon__broken\nf1,2,oops\n")
    combined, statuses = collect_features(tmp_path, baseline, tmp_path / "results")
    pd.testing.assert_frame_equal(combined, baseline)
    assert not any(s["status"] == "accepted" for s in statuses)


def test_four_new_features_replace_reference_and_multiple_owners_combine(tmp_path):
    baseline = canonical_keys().assign(baseline__example=37.)
    matthew = canonical_keys()
    for i in range(4):
        matthew[f"matthew__example_{i}"] = np.arange(len(matthew), dtype=float) + i
    export_features(matthew, tmp_path, "Matthew")
    combined, _ = collect_features(tmp_path, baseline, tmp_path / "first")
    pd.testing.assert_frame_equal(combined, matthew)
    export_features(valid(), tmp_path, "Vivian")
    combined, _ = collect_features(tmp_path, baseline, tmp_path / "second")
    assert len(combined.columns) - 2 == 5
    assert not any(c.startswith("baseline__") for c in combined)


def test_explicit_baseline_ignores_even_valid_contributor_exports(tmp_path):
    baseline = canonical_keys().assign(baseline__mean=37.)
    export_features(valid(), tmp_path, "Vivian")
    combined, statuses = collect_features(tmp_path, baseline, tmp_path / "results", baseline_only=True)
    pd.testing.assert_frame_equal(combined, baseline)
    assert all(s["status"] == "ignored" for s in statuses)


def test_duplicate_csv_headers_rejected(tmp_path):
    path = tmp_path / "features.csv"
    path.write_text("mouse_id,day_index,vivian__x,vivian__x\nf1,2,1,2\n")
    with pytest.raises(ValueError, match="Duplicate CSV"):
        read_features(path, "Vivian")
