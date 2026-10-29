import json

import joblib
import numpy as np
import pandas as pd
import pytest

from estrus.modeling import (evaluate, grouped_splits, metric_values, predict,
                             selected_feature_names, split_mice, SelectPercentileAtLeastOne)


def synthetic():
    rng = np.random.default_rng(190)
    frame = pd.MultiIndex.from_product([[f"f{i}" for i in range(1, 7)], range(2, 10)], names=["mouse_id", "day_index"]).to_frame(index=False)
    labels = frame.copy()
    labels["is_estrus"] = labels.day_index.isin([2, 6]).astype(int)
    labels["label_source"] = "synthetic_test"
    for i in range(7):
        frame[f"baseline__x{i}"] = rng.normal(size=len(frame)) + labels.is_estrus * (1 if i < 2 else .2)
    frame["vivian__example"] = rng.normal(size=len(frame)) + 2 * labels.is_estrus
    frame["baseline__constant"] = 1.
    frame.loc[0, "baseline__x3"] = np.nan
    return frame, labels


def config():
    return {"seed": 190, "test_mice": 2, "cv_folds": 2, "trees": 5, "jobs": 1, "quick": True}


def test_training_validation_and_test_mice_are_disjoint():
    features, labels = synthetic()
    groups, y = features.mouse_id.to_numpy(), labels.is_estrus.to_numpy()
    train, test = split_mice(y, groups, config())
    assert not set(groups[train]) & set(groups[test])
    for fitting, validation in grouped_splits(y[train], groups[train], 2):
        assert not set(groups[train][fitting]) & set(groups[train][validation])
        assert not set(groups[train][validation]) & set(groups[test])
    with pytest.raises(ValueError, match="both classes"):
        grouped_splits(np.zeros(len(y)), groups, 3)


def test_one_winner_matches_validation_and_saved_model(tmp_path):
    features, labels = synthetic()
    predictions, metrics = evaluate(features, labels, tmp_path, config())
    choices = pd.read_csv(tmp_path / "model_comparison.csv")
    winner = choices[choices.chosen].iloc[0]
    assert choices.chosen.sum() == 1
    assert winner.validation_ap == pytest.approx(choices.validation_ap.max())
    summary = json.loads((tmp_path / "final_model.json").read_text())
    assert summary["family"] == winner.family
    assert summary["feature_set"] == winner.feature_set
    assert predictions.family.nunique() == 1
    assert set(predictions.family) == {winner.family}
    assert len(predictions) == 16  # Two reserved mice, eight days each.
    splits = json.loads((tmp_path / "splits.json").read_text())
    assert not set(splits["training_mice"]) & set(splits["test_mice"])
    assert set(predictions.mouse_id) == set(splits["test_mice"])
    bundle = joblib.load(tmp_path / "model.joblib")
    assert len(bundle["model"].calibrated_classifiers_) == 1
    final_pipeline = bundle["model"].calibrated_classifiers_[0].estimator
    assert set(selected_feature_names(final_pipeline, bundle["feature_columns"])) == set(summary["selected_features"])
    catalog = pd.read_csv(tmp_path / "feature_summary.csv")
    assert len(catalog) == len(features.columns) - 2
    assert set(catalog[catalog.used].feature) == set(summary["selected_features"])
    assert "Vivian" in set(catalog.owner)
    assert not catalog.loc[catalog.feature.eq("baseline__constant"), "used"].item()
    # Saved model reproduces every probability shown in the report.
    assembled = predictions[["mouse_id", "day_index"]].merge(features, on=["mouse_id", "day_index"])
    actual = predict(tmp_path / "model.joblib", assembled)
    np.testing.assert_allclose(actual.p_estrus, predictions.p_estrus)
    assert metrics.estimate.notna().all()
    with pytest.raises(ValueError, match="schema"):
        predict(tmp_path / "model.joblib", features.drop(columns="baseline__x0"))


def test_test_labels_cannot_change_model_or_feature_selection(tmp_path):
    features, labels = synthetic()
    train, test = split_mice(labels.is_estrus.to_numpy(), features.mouse_id.to_numpy(), config())
    changed = labels.copy()
    changed.loc[test, "is_estrus"] = 1 - changed.loc[test, "is_estrus"]
    first, _ = evaluate(features, labels, tmp_path / "first", config())
    second, _ = evaluate(features, changed, tmp_path / "second", config())
    # Changing only reserved labels can change the test score, never fitting.
    np.testing.assert_allclose(first.p_estrus, second.p_estrus)
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "first/feature_summary.csv"), pd.read_csv(tmp_path / "second/feature_summary.csv"))
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "first/model_comparison.csv"), pd.read_csv(tmp_path / "second/model_comparison.csv"))


def test_probability_metrics_reward_correct_predictions():
    _, labels = synthetic()
    metrics = metric_values(labels.is_estrus, .1 + .8 * labels.is_estrus, np.repeat(.25, len(labels)))
    assert metrics["average_precision"] == 1
    assert metrics["brier_improvement_over_prevalence"] > 0


@pytest.mark.parametrize("percentile", [35, 70])
def test_feature_selection_keeps_one_feature_for_small_exports(percentile):
    selector = SelectPercentileAtLeastOne(percentile=percentile)
    X = np.arange(16, dtype=float).reshape(-1, 1)
    y = np.tile([0, 0, 0, 1], 4)
    assert selector.fit_transform(X, y).shape == (16, 1)
