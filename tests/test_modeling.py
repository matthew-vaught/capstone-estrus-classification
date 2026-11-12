import json

import joblib
import numpy as np
import pandas as pd
import pytest

from estrus.modeling import (evaluate, grouped_splits, metric_values, predict,
                             selected_feature_names, split_mice, SelectPercentileAtLeastOne,
                             compare_models, select_threshold, threshold_settings, tune_threshold)


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
    root = tmp_path / "checkout"
    owner_folder = root / "Vivian Feature Engineering"
    owner_folder.mkdir(parents=True)
    note = "Input context supplied by the checkout used for this run."
    (owner_folder / "input_requirements.json").write_text(json.dumps([
        {"features": ["vivian__example"], "note": note},
    ]))
    predictions, metrics = evaluate(features, labels, tmp_path, config(), root=root)
    choices = pd.read_csv(tmp_path / "model_comparison.csv")
    winner = choices[choices.chosen].iloc[0]
    assert choices.chosen.sum() == 1
    assert winner.validation_ap == pytest.approx(choices.validation_ap.max())
    summary = json.loads((tmp_path / "final_model.json").read_text())
    assert summary["family"] == winner.family
    assert summary["feature_set"] == winner.feature_set
    assert summary["input_requirements"] == [note]
    assert predictions.family.nunique() == 1
    assert set(predictions.family) == {winner.family}
    assert len(predictions) == 16  # Two reserved mice, eight days each.
    splits = json.loads((tmp_path / "splits.json").read_text())
    assert not set(splits["training_mice"]) & set(splits["test_mice"])
    assert set(predictions.mouse_id) == set(splits["test_mice"])
    bundle = joblib.load(tmp_path / "model.joblib")
    assert bundle["input_requirements"] == [note]
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


@pytest.mark.parametrize("tuning", [False, True])
def test_test_labels_cannot_change_model_or_feature_selection(tmp_path, tuning):
    features, labels = synthetic()
    settings = {**config(), "threshold_tuning": {"enabled": tuning, "objective": "f2"}}
    train, test = split_mice(labels.is_estrus.to_numpy(), features.mouse_id.to_numpy(), settings)
    changed = labels.copy()
    changed.loc[test, "is_estrus"] = 1 - changed.loc[test, "is_estrus"]
    first, _ = evaluate(features, labels, tmp_path / "first", settings)
    second, _ = evaluate(features, changed, tmp_path / "second", settings)
    # Changing only reserved labels can change the test score, never fitting.
    np.testing.assert_allclose(first.p_estrus, second.p_estrus)
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "first/feature_summary.csv"), pd.read_csv(tmp_path / "second/feature_summary.csv"))
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "first/model_comparison.csv"), pd.read_csv(tmp_path / "second/model_comparison.csv"))
    first_summary = json.loads((tmp_path / "first/final_model.json").read_text())
    second_summary = json.loads((tmp_path / "second/final_model.json").read_text())
    assert first_summary["threshold"] == second_summary["threshold"]
    np.testing.assert_array_equal(first.prediction, second.prediction)
    if tuning:
        assert (tmp_path / "first/threshold_tuning.json").read_bytes() == (tmp_path / "second/threshold_tuning.json").read_bytes()
        assert (tmp_path / "first/threshold_curve.csv").read_bytes() == (tmp_path / "second/threshold_curve.csv").read_bytes()
        evidence = first_summary["threshold_tuning"]
        development = set(features.iloc[train].mouse_id)
        test_mice = set(features.iloc[test].mouse_id)
        for fold in evidence["folds"]:
            fitting, validation = set(fold["fitting_mice"]), set(fold["validation_mice"])
            assert not fitting & validation
            assert fitting | validation == development
            assert not (fitting | validation) & test_mice
            for inner in fold["inner_validation"]:
                a, b = set(inner["fitting_mice"]), set(inner["validation_mice"])
                assert not a & b
                assert a | b == fitting
                assert not (a | b) & validation
        oof = pd.read_csv(tmp_path / "first/threshold_validation_predictions.csv")
        assert set(oof.mouse_id) == development
        assert not oof.duplicated(["mouse_id", "day_index"]).any()
        assert len(oof) == len(train) and oof.p_estrus.notna().all()
        bundle = joblib.load(tmp_path / "first/model.joblib")
        assert bundle["threshold"] == first_summary["threshold"]
        assembled = first[["mouse_id", "day_index"]].merge(features, on=["mouse_id", "day_index"])
        replay = predict(tmp_path / "first/model.joblib", assembled)
        np.testing.assert_allclose(replay.p_estrus, first.p_estrus)
        np.testing.assert_array_equal(replay.prediction, first.prediction)
        comparison = pd.read_csv(tmp_path / "first/threshold_comparison.csv")
        assert comparison.average_precision.nunique() == 1
        np.testing.assert_allclose(comparison.threshold, [.5, bundle["threshold"]])


def test_threshold_selection_improves_recall_and_keeps_probability_metrics():
    y = np.array([1, 1, 1, 0, 0, 0])
    probabilities = np.array([.6, .4, .3, .35, .2, .1])
    cutoff, curve = select_threshold(y, probabilities)
    assert cutoff == pytest.approx(.25)
    assert curve.selected.sum() == 1
    fixed = metric_values(y, probabilities)
    tuned = metric_values(y, probabilities, threshold=cutoff)
    assert fixed["recall"] == pytest.approx(1 / 3)
    assert tuned["recall"] == 1
    assert tuned["false_positive"] == 1
    assert tuned["f2"] > fixed["f2"]
    for name in ["average_precision", "brier", "log_loss"]:
        assert tuned[name] == fixed[name]
    # Equality is classified positive; ties are deterministic and favor 0.5.
    cutoff, _ = select_threshold([0, 1], [.1, .5])
    assert cutoff == .5


@pytest.mark.parametrize("target,probabilities", [([1, 1], [.2, .3]), ([0, 1], [.1, np.nan]),
                                                   ([0, 1], [.1, 1.1]), ([0, 1], [.1])])
def test_threshold_selection_rejects_invalid_inputs(target, probabilities):
    with pytest.raises(ValueError, match="Threshold selection"):
        select_threshold(target, probabilities)


def test_threshold_settings_are_opt_in_and_validated():
    assert not threshold_settings({})["enabled"]
    for bad in [True, {"enabled": "false"}, {"objective": "unknown"}]:
        with pytest.raises(ValueError, match="threshold_tuning"):
            threshold_settings({"threshold_tuning": bad})


def test_prediction_confidence_follows_chosen_class_below_half(tmp_path):
    from sklearn.dummy import DummyClassifier
    model = DummyClassifier(strategy="prior").fit([[0], [1], [2], [3]], [0, 0, 0, 1])
    path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "feature_columns": ["baseline__x"], "threshold": .2}, path)
    result = predict(path, pd.DataFrame({"mouse_id": ["f1"], "day_index": [2], "baseline__x": [0]}))
    assert result.prediction.item() == 1
    assert result.p_estrus.item() == .25
    assert result.predicted_class_probability.item() == .25


def test_excluded_development_labels_cannot_change_their_own_probabilities(tmp_path):
    """Exclude labels from search and calibration, not just the base fit."""
    features, labels = synthetic()
    X = features.drop(columns=["mouse_id", "day_index"])
    groups, y = features.mouse_id.to_numpy(), labels.is_estrus.to_numpy()
    cv = grouped_splits(y, groups, 2)
    changed = y.copy()
    validation = cv[0][1]
    changed[validation] = 1 - changed[validation]
    settings = {**config(), "threshold_tuning": {"enabled": True, "objective": "f2"}}
    keys = features[["mouse_id", "day_index"]]
    for name, target in [("original", y), ("changed", changed)]:
        folder = tmp_path / name
        folder.mkdir()
        tune_threshold(X, target, groups, keys, cv, settings, folder)
    original = pd.read_csv(tmp_path / "original/threshold_validation_predictions.csv")
    altered = pd.read_csv(tmp_path / "changed/threshold_validation_predictions.csv")
    np.testing.assert_allclose(original.loc[validation, "p_estrus"],
                               altered.loc[validation, "p_estrus"], rtol=0, atol=0)
    original_audit = json.loads((tmp_path / "original/threshold_tuning.json").read_text())
    altered_audit = json.loads((tmp_path / "changed/threshold_tuning.json").read_text())
    assert original_audit["folds"][0] == altered_audit["folds"][0]
    # The cutoff may change: excluded labels are legitimately used for selecting
    # the threshold after probabilities have been generated, never for fitting.


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


def test_experiment_config_controls_search_grid():
    features, labels = synthetic()
    X = features.drop(columns=["mouse_id", "day_index"])
    y = labels.is_estrus.to_numpy()
    cv = grouped_splits(y, features.mouse_id.to_numpy(), 2)
    settings = {**config(), "quick": False, "feature_percentiles": [50],
                "regularization": [.25], "forest_max_depth": [2],
                "forest_min_samples_leaf": 2}
    _, candidates = compare_models(X, y, cv, settings)
    assert len(candidates) == 6
    assert set(candidates.feature_set) == {"All usable features", "Top 50% of features"}
    assert candidates[candidates.family.eq("logistic")].settings.str.contains("0.25", regex=False).all()
    assert candidates[candidates.family.eq("random_forest")].settings.str.contains("2", regex=False).all()
