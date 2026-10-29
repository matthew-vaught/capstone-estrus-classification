"""Publish a small, readable set of results from the training workspace."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pandas as pd

MODEL_NAMES = {
    "logistic": "Logistic regression",
    "random_forest": "Random forest",
    "rbf_svm": "Support vector machine",
}


def readable_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """One interpretable row per held-out day, with probabilities on a 0–1 scale."""
    result = predictions[["mouse_id", "day_index"]].copy()
    result["actual_class"] = predictions.is_estrus.map({0: "Non-estrus", 1: "Estrus"})
    result["predicted_class"] = predictions.prediction.map({0: "Non-estrus", 1: "Estrus"})
    result["estrus_probability"] = predictions.p_estrus
    result["confidence"] = predictions.predicted_class_probability
    return result


def publish_results(workspace: Path, destination: Path, predictions, metrics, *, save_details=False):
    """Keep the report, spreadsheet, saved model, and brief instructions visible.

    The workspace is temporary. Detailed outputs are retained only on request.
    This function never changes model values or substitutes training predictions.
    """
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workspace / "report.html", destination / "report.html")
    shutil.copy2(workspace / "model.joblib", destination / "model.joblib")
    readable_predictions(predictions).to_csv(destination / "predictions.csv", index=False)
    if save_details:
        details = destination / "details"
        details.mkdir(exist_ok=True)
        for path in workspace.iterdir():
            if path.name in {"report.html", "model.joblib"}:
                continue
            if path.is_dir():
                shutil.copytree(path, details / path.name, dirs_exist_ok=True)
            else:
                shutil.copy2(path, details / path.name)
    final_model = json.loads((workspace / "final_model.json").read_text())
    scores = metrics.set_index("metric").estimate
    model_name = MODEL_NAMES.get(final_model["family"], final_model["family"])
    extra = "\n`details/` contains optional technical records from this run. You can ignore it when reviewing results.\n" if save_details else ""
    note = ""
    if predictions.label_source.str.contains("paper_alignment_proxy", regex=False).any():
        note = "\nLabels are provisional: recording days 2, 6, and 10 are treated as estrus. These results measure recognition of that paper-aligned pattern until independent labels are available.\n"
    source = final_model.get("feature_source")
    feature_note = "Contributor features only; reference features are excluded." if source == "contributors" else "Reference baseline features only." if source == "baseline" else "See the report for feature inputs."
    input_notes = "\n\n".join(final_model.get("input_requirements", []))
    text = f"""# Results

**Start with [report.html](report.html)** — open it in a browser for the chosen model, feature rankings grouped by person, and expandable test-day plots.

| File | When to use it |
| --- | --- |
| `report.html` | Review and share the results. Images are included in this one file. |
| `predictions.csv` | Open in Excel or another spreadsheet to inspect each mouse-day. |
| `model.joblib` | Reuse the trained model from Python or `estrus predict`; you do not need to open this file. |

This completed run evaluated {len(predictions)} mouse-days from {predictions.mouse_id.nunique()} mice. Test mice were kept out of training.

**Feature inputs:** {feature_note}

{input_notes}

**Main metric: average precision = {scores['average_precision']:.3f}.** It measures how well estrus days appear near the top when days are ranked by predicted estrus probability. Higher is better; 1 is perfect. This is the metric used to choose models, not a percentage of correct predictions.

The saved model uses **{model_name}** with **{final_model['n_features']} features** ({final_model['feature_set']}). It was chosen using validation on {len(final_model['training_mice'])} training mice. The score above comes from {len(final_model['test_mice'])} reserved test mice. The saved model is the same fitted model evaluated here; test mice are not used to fit it.
{note}
In the spreadsheet, `actual_class` and `predicted_class` say Estrus or Non-estrus. `estrus_probability` is P(estrus); `confidence` is the probability assigned to the predicted class. Both use 0–1, so 0.8 means 80%. Confidence is a model estimate, not a guarantee.
{extra}
Future runs use this same layout. Add `--save-details` only when you want the technical records for debugging or deeper analysis.
"""
    # Written last: a README indicates publishing completed successfully.
    (destination / "README.md").write_text(text, encoding="utf-8")
    return destination / "report.html"
