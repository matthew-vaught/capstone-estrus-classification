"""Compare a few feature/model combinations, then test one chosen model."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectPercentile, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, fbeta_score, log_loss,
                             precision_score, recall_score)
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .data import KEYS
from .contracts import input_requirements

FAMILIES = {
    LogisticRegression: "logistic",
    RandomForestClassifier: "random_forest",
    SVC: "rbf_svm",
}


class SelectPercentileAtLeastOne(SelectPercentile):
    """Keep small contributor exports usable even when they contain one feature."""

    def _get_support_mask(self):
        mask = super()._get_support_mask()
        if len(mask) and not mask.any():
            mask[np.argmax(np.nan_to_num(self.scores_, nan=-np.inf))] = True
        return mask


def grouped_splits(y, groups, n_splits):
    """Return mouse-disjoint validation folds, each containing both classes."""
    if n_splits < 2 or len(np.unique(groups)) < n_splits:
        raise ValueError(f"Need at least {n_splits} training mice for validation.")
    splits = list(GroupKFold(n_splits=n_splits).split(np.zeros(len(y)), y, groups))
    for train, validation in splits:
        if len(np.unique(y[train])) != 2 or len(np.unique(y[validation])) != 2:
            raise ValueError("Every validation split needs both classes. Review labels or reduce cv_folds.")
        assert not set(groups[train]) & set(groups[validation])
    return splits


def split_mice(y, groups, config):
    """Fix test mice using IDs and the seed, before selecting any features/models."""
    n_test = config["test_mice"]
    if not isinstance(n_test, int) or n_test < 1 or len(np.unique(groups)) - n_test < config["cv_folds"]:
        raise ValueError("test_mice must leave enough training mice for cv_folds.")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=n_test, random_state=config["seed"]).split(np.zeros(len(y)), y, groups))
    if len(np.unique(y[train])) != 2 or len(np.unique(y[test])) != 2:
        raise ValueError("Training and test mice must each contain both classes. Review the labels and split settings.")
    assert not set(groups[train]) & set(groups[test])
    return train, test


def feature_set_name(selector):
    return "All usable features" if selector == "passthrough" else f"Top {selector.percentile}% of features"


def family_of(pipeline):
    return FAMILIES[type(pipeline.named_steps["model"])]


def selected_feature_names(pipeline, columns):
    """Map fitted variance/selection masks back to the original input names."""
    names = np.asarray(columns)[pipeline.named_steps["variance"].get_support()]
    selector = pipeline.named_steps["select"]
    if selector != "passthrough":
        names = names[selector.get_support()]
    return list(names)


def compare_models(X, y, cv, config):
    """One comparison table; the highest mean validation AP wins."""
    seed = config["seed"]
    pipeline = Pipeline([
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("variance", VarianceThreshold()),
        ("scale", StandardScaler()),
        ("select", "passthrough"),
        ("model", LogisticRegression()),
    ])
    selectors = ["passthrough", *[
        SelectPercentileAtLeastOne(f_classif, percentile=p)
        for p in config.get("feature_percentiles", [35, 70])
    ]]
    regularization = config.get("quick_regularization", [1.]) if config.get("quick") else config.get("regularization", [.1, 1., 10.])
    grid = [
        {"model": [LogisticRegression(class_weight="balanced", max_iter=3000, random_state=seed)], "model__C": regularization, "select": selectors},
        {"model": [RandomForestClassifier(n_estimators=config["trees"], class_weight="balanced", min_samples_leaf=config.get("forest_min_samples_leaf", 3), random_state=seed, n_jobs=1)], "model__max_depth": config.get("forest_max_depth", [3, None]), "select": selectors},
        {"model": [SVC(class_weight="balanced", random_state=seed)], "model__C": regularization, "select": selectors},
    ]
    search = GridSearchCV(pipeline, grid, scoring="average_precision", cv=cv, n_jobs=config["jobs"], error_score="raise", refit=True)
    search.fit(X, y)
    candidates = []
    for index, (params, score) in enumerate(zip(search.cv_results_["params"], search.cv_results_["mean_test_score"])):
        candidates.append({
            "family": FAMILIES[type(params["model"])], "feature_set": feature_set_name(params["select"]),
            "validation_ap": float(score), "chosen": index == search.best_index_,
            "settings": str({k: v for k, v in params.items() if k.startswith("model__")}),
        })
    return search.best_estimator_, pd.DataFrame(candidates)


def feature_assessment(X, y, cv, chosen_pipeline, final_pipeline, config):
    """Assess features on development mice only, preserving the test set."""
    selected = set(selected_feature_names(final_pipeline, X.columns))
    permutation_drops = []
    for fold, (train, validation) in enumerate(cv):
        fitted = clone(chosen_pipeline).fit(X.iloc[train], y[train])
        values = permutation_importance(fitted, X.iloc[validation], y[validation], scoring="average_precision", n_repeats=config.get("permutation_repeats", 3), random_state=config["seed"] + fold, n_jobs=config["jobs"])
        permutation_drops.append(values.importances_mean)
    mean_drop = np.mean(permutation_drops, axis=0)
    single_feature_model = Pipeline([
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=config["seed"])),
    ])
    rows = []
    for index, feature in enumerate(X.columns):
        owner, name = feature.split("__", 1)
        solo_score = float(cross_val_score(single_feature_model, X[[feature]], y, cv=cv, scoring="average_precision", n_jobs=config["jobs"]).mean())
        rows.append({
            "feature": feature, "name": name,
            "owner": "Reference features" if owner == "baseline" else owner.title(),
            "individual_ap": solo_score, "importance_ap_drop": float(mean_drop[index]),
            "used": feature in selected,
            "status": "Used" if feature in selected else ("Constant / unavailable" if X[feature].nunique(dropna=True) <= 1 else "Not selected"),
        })
    return pd.DataFrame(rows).sort_values(["importance_ap_drop", "individual_ap"], ascending=False).reset_index(drop=True)


def metric_values(y, probability, baseline=None, *, threshold=.5):
    """Compute probability metrics and decisions at the supplied cutoff."""
    y, probability = np.asarray(y), np.asarray(probability)
    prediction = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    result = {
        "average_precision": float(average_precision_score(y, probability)),
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.,
        "f2": float(fbeta_score(y, prediction, beta=2, zero_division=0)),
        "true_positive": int(tp), "false_negative": int(fn),
        "true_negative": int(tn), "false_positive": int(fp),
        "brier": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, np.c_[1 - probability, probability], labels=[0, 1])),
    }
    if baseline is not None:
        result["brier_improvement_over_prevalence"] = float(brier_score_loss(y, baseline) - result["brier"])
    return result


def threshold_settings(config):
    """Old configurations retain the fixed cutoff unless explicitly enabled."""
    settings = config.get("threshold_tuning", {})
    if not isinstance(settings, dict):
        raise ValueError("threshold_tuning must be an object with enabled and objective settings.")
    enabled, objective = settings.get("enabled", False), settings.get("objective", "f2")
    if not isinstance(enabled, bool):
        raise ValueError("threshold_tuning.enabled must be true or false.")
    if objective not in {"f2", "balanced_accuracy"}:
        raise ValueError("threshold_tuning.objective must be f2 or balanced_accuracy.")
    return {"enabled": enabled, "objective": objective}


def select_threshold(y, probability, *, objective="f2"):
    """Enumerate decision boundaries; ties prefer closest to .5, then higher.

    Midpoints between distinct scores represent each interior decision pattern.
    Include 0, .5, and 1 explicitly. Selection scores are not evaluation scores.
    """
    y, probability = np.asarray(y), np.asarray(probability, dtype=float)
    if (y.ndim != 1 or probability.shape != y.shape or set(np.unique(y)) != {0, 1}
            or not np.isfinite(probability).all()
            or ((probability < 0) | (probability > 1)).any()):
        raise ValueError("Threshold selection needs both binary classes and finite probabilities in [0, 1].")
    if objective not in {"f2", "balanced_accuracy"}:
        raise ValueError("Threshold objective must be f2 or balanced_accuracy.")
    scores = np.unique(probability)
    candidates = np.unique(np.r_[0., .5, 1., scores[:-1] + np.diff(scores) / 2])
    curve = pd.DataFrame([
        {"threshold": float(t), **metric_values(y, probability, threshold=t)}
        for t in candidates
    ])
    best = curve[np.isclose(curve[objective], curve[objective].max(), rtol=0, atol=1e-12)]
    winner = best.assign(distance=(best.threshold - .5).abs()).sort_values(
        ["distance", "threshold"], ascending=[True, False]).iloc[0]
    threshold = float(winner.threshold)
    curve["selected"] = curve.threshold.eq(threshold)
    return threshold, curve


def tune_threshold(X, y, groups, keys, cv, config, destination):
    """Get development predictions excluding each scored mouse from all fitting.

    Model search, imputation, scaling, feature selection, and sigmoid calibration
    are repeated inside each fitting fold. No reserved test inputs are accepted.
    """
    settings = threshold_settings(config)
    probability = np.full(len(y), np.nan)
    fold_ids = np.full(len(y), -1, dtype=int)
    audits = []
    for fold, (fitting, validation) in enumerate(cv):
        fitting_groups = groups[fitting]
        if len(np.unique(fitting_groups)) < 2:
            raise ValueError("Threshold tuning needs at least two fitting mice in every development fold; increase the development cohort or cv_folds.")
        inner_cv = grouped_splits(y[fitting], fitting_groups,
                                  min(config["cv_folds"], len(np.unique(fitting_groups))))
        print(f"Threshold tuning: development fold {fold + 1}/{len(cv)}; repeat model search and calibration on fitting mice only...", flush=True)
        chosen, candidates = compare_models(X.iloc[fitting], y[fitting], inner_cv, config)
        calibrated = CalibratedClassifierCV(clone(chosen), method="sigmoid", cv=inner_cv,
                                            ensemble=False, n_jobs=config["jobs"])
        calibrated.fit(X.iloc[fitting], y[fitting])
        probability[validation] = calibrated.predict_proba(X.iloc[validation])[:, 1]
        fold_ids[validation] = fold
        winner = candidates.loc[candidates.chosen].iloc[0]
        audits.append({
            "fold": fold, "fitting_mice": sorted(set(fitting_groups)),
            "validation_mice": sorted(set(groups[validation])),
            "inner_validation": [
                {"fitting_mice": sorted(set(fitting_groups[a])),
                 "validation_mice": sorted(set(fitting_groups[b]))} for a, b in inner_cv],
            "family": winner.family, "feature_set": winner.feature_set,
            "settings": winner.settings,
        })
    if not np.isfinite(probability).all():
        raise ValueError("Threshold validation folds must provide a prediction for every development row.")
    threshold, curve = select_threshold(y, probability, objective=settings["objective"])
    predictions = keys.reset_index(drop=True).copy()
    predictions["is_estrus"], predictions["p_estrus"], predictions["fold"] = y, probability, fold_ids
    predictions.to_csv(destination / "threshold_validation_predictions.csv", index=False)
    curve.to_csv(destination / "threshold_curve.csv", index=False)
    evidence = {
        **settings, "threshold": threshold, "default_threshold": .5,
        "method": "mouse_grouped_nested_model_selection_and_calibration",
        "tie_break": "closest_to_0.5_then_higher",
        "score_scope": "Development scores used to choose the cutoff; not independent performance estimates.",
        "development_mice": sorted(set(groups)), "folds": audits,
        "default_selection_metrics": metric_values(y, probability),
        "selected_selection_metrics": metric_values(y, probability, threshold=threshold),
    }
    (destination / "threshold_tuning.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return threshold, evidence


def evaluate(features, labels, destination: Path, config, *, root: Path | None = None):
    """Select on development mice and publish predictions for reserved mice.

    Inputs are joined on mouse/day keys. Fitted preprocessing, model selection,
    calibration, and feature assessments exclude the test mice. Returns held-out
    predictions and metrics; writes the fitted model and technical records.
    """
    threshold_config = threshold_settings(config)
    frame = features.merge(labels.dropna(subset=["is_estrus"]), on=KEYS, how="inner", validate="one_to_one")
    frame["is_estrus"] = frame.is_estrus.astype(int)
    columns = [column for column in features if column not in KEYS]
    requirements = input_requirements(columns, root)
    X, y, groups = frame[columns], frame.is_estrus.to_numpy(), frame.mouse_id.to_numpy()
    train, test = split_mice(y, groups, config)
    X_train, y_train = X.iloc[train], y[train]
    cv = grouped_splits(y_train, groups[train], config["cv_folds"])
    destination.mkdir(parents=True, exist_ok=True)
    splits = {"training_mice": sorted(set(groups[train])), "test_mice": sorted(set(groups[test])),
              "validation": [{"train_mice": sorted(set(groups[train][a])), "validation_mice": sorted(set(groups[train][b]))} for a, b in cv]}
    (destination / "splits.json").write_text(json.dumps(splits, indent=2) + "\n")
    threshold, threshold_evidence = .5, {**threshold_config, "threshold": .5, "method": "fixed"}
    if threshold_config["enabled"]:
        threshold, threshold_evidence = tune_threshold(
            X_train, y_train, groups[train], frame.iloc[train][KEYS], cv, config, destination)
        print(f"Development-selected cutoff: {threshold:.6f} ({threshold_config['objective']}). Frozen before test prediction.", flush=True)
    print(f"Compare feature sets and models on {len(splits['training_mice'])} training mice; reserve {len(splits['test_mice'])} test mice: {', '.join(splits['test_mice'])}", flush=True)
    chosen, candidates = compare_models(X_train, y_train, cv, config)
    candidates.to_csv(destination / "model_comparison.csv", index=False)
    family = family_of(chosen)
    print(f"Chosen: {family}, {feature_set_name(chosen.named_steps['select'])}. Fitting one model with probability calibration...", flush=True)
    # One final classifier, with a probability mapping learned from grouped
    # validation predictions. Its selector is fitted within each training split.
    model = CalibratedClassifierCV(clone(chosen), method="sigmoid", cv=cv, ensemble=False, n_jobs=config["jobs"])
    model.fit(X_train, y_train)
    final_pipeline = model.calibrated_classifiers_[0].estimator
    selected = selected_feature_names(final_pipeline, columns)
    print(f"Assessing {len(columns)} features using training mice only...", flush=True)
    catalog = feature_assessment(X_train, y_train, cv, chosen, final_pipeline, config)
    catalog.to_csv(destination / "feature_summary.csv", index=False)
    # Test probabilities are calculated only after model/feature choice is fixed.
    probability = model.predict_proba(X.iloc[test])[:, 1]
    predictions = frame.iloc[test][KEYS + ["is_estrus", "label_source"]].copy()
    predictions["family"] = family
    predictions["p_estrus"] = probability
    predictions["prediction"] = (probability >= threshold).astype(int)
    predictions["predicted_class_probability"] = np.where(predictions.prediction.eq(1), probability, 1 - probability)
    predictions.to_csv(destination / "predictions.csv", index=False)
    metrics = pd.DataFrame([{"metric": name, "estimate": value} for name, value in metric_values(y[test], probability, np.repeat(y_train.mean(), len(test)), threshold=threshold).items()])
    metrics.to_csv(destination / "metrics.csv", index=False)
    if threshold_config["enabled"]:
        pd.DataFrame([
            {"operating_point": name, "threshold": cutoff,
             **metric_values(y[test], probability, threshold=cutoff)}
            for name, cutoff in [("Default", .5), ("Development-selected", threshold)]
        ]).to_csv(destination / "threshold_comparison.csv", index=False)
    winner = candidates.loc[candidates.chosen].iloc[0]
    summary = {"family": family, "feature_set": winner.feature_set, "validation_ap": float(winner.validation_ap),
               "test_ap": float(metrics.set_index("metric").loc["average_precision", "estimate"]),
               "selected_features": selected, "n_features": len(selected), "n_available": len(columns),
               "training_mice": splits["training_mice"], "test_mice": splits["test_mice"],
               "threshold": threshold, "threshold_tuning": threshold_evidence, "settings": winner.settings}
    summary["feature_source"] = "baseline" if all(name.startswith("baseline__") for name in columns) else "contributors" if not any(name.startswith("baseline__") for name in columns) else "mixed"
    summary["input_requirements"] = requirements
    (destination / "final_model.json").write_text(json.dumps(summary, indent=2) + "\n")
    joblib.dump({"model": model, "feature_columns": columns, "selected_features": selected,
                 "threshold": threshold, "threshold_tuning": threshold_evidence,
                 "family": family, "label_sources": sorted(frame.label_source.unique()),
                 "training_mice": splits["training_mice"], "test_mice": splits["test_mice"], "config": config,
                 "input_requirements": summary["input_requirements"]}, destination / "model.joblib")
    features.to_csv(destination / "feature_matrix.csv", index=False)
    frame[KEYS + ["is_estrus", "label_source"]].to_csv(destination / "labels_used.csv", index=False)
    return predictions, metrics


def predict(bundle_path: Path, features: pd.DataFrame) -> pd.DataFrame:
    """Predict assembled mouse-day features using the saved, selected pipeline."""
    bundle = joblib.load(bundle_path)
    columns = bundle["feature_columns"]
    missing = set(columns) - set(features)
    if missing:
        raise ValueError(f"Model requires its original feature schema. Missing: {sorted(missing)}. Rebuild the features, or retrain without that contributor.")
    matrix = features[columns].apply(pd.to_numeric, errors="raise")
    if np.isinf(matrix.to_numpy(dtype=float)).any():
        raise ValueError("Inference features contain infinity.")
    result = features[[c for c in KEYS if c in features]].copy()
    result["p_estrus"] = bundle["model"].predict_proba(matrix)[:, 1]
    result["prediction"] = (result.p_estrus >= bundle["threshold"]).astype(int)
    result["predicted_class_probability"] = np.where(result.prediction.eq(1), result.p_estrus, 1 - result.p_estrus)
    return result
