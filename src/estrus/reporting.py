"""A short results report centered on average precision and test-day examples."""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data import ANALYSIS_DAYS, iter_days
from .results import MODEL_NAMES
from .contracts import OWNERS


def _image(fig, path):
    fig.savefig(path, dpi=115, bbox_inches="tight")
    plt.close(fig)
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}" alt="{html.escape(path.stem)}" loading="lazy">'


def cycle_day(day_index):
    """Map the original recording day to the assumed aligned four-day cycle."""
    if day_index not in ANALYSIS_DAYS:
        raise ValueError("Cycle references use recording days 2 through 13.")
    return (day_index - ANALYSIS_DAYS[0]) % 4 + 1


def female_cycle_references(signals):
    """Average repeated cycles within each mouse, then give mice equal weight.

    Returns four 1440-row reference days, using all available female signals.
    These population curves are for display only, including the test animals.
    """
    mice = sorted({mouse for mouse, _ in signals})
    reference = {}
    for phase in range(1, 5):
        mouse_means = []
        for mouse in mice:
            repeats = [signals[(mouse, day)][["la", "cbt"]]
                       for day in ANALYSIS_DAYS if cycle_day(day) == phase and (mouse, day) in signals]
            if repeats:
                # Index level 1 is minute_of_day, not recording day or cycle.
                mouse_means.append(pd.concat(repeats, keys=range(len(repeats))).groupby(level=1).mean())
        if mouse_means:
            reference[phase] = pd.concat(mouse_means, keys=range(len(mouse_means))).groupby(level=1).mean()
    return reference


def plot_mouse_day(signal, reference, *, mouse, day_index, predicted, actual, confidence, n_mice):
    """Compact, side-by-side LA/CBT panels with a matched population overlay."""
    phase = cycle_day(day_index)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), layout="constrained")
    hours = np.arange(len(signal)) / 60
    for ax, name, color, label in zip(axes, ["la", "cbt"], ["#377eb8", "#d95f02"], ["Activity (counts/min)", "Temperature (°C)"]):
        ax.plot(hours, signal[name], lw=.5, alpha=.18, color=color)
        ax.plot(hours, signal[name].rolling(15, center=True, min_periods=1).mean(),
                lw=1.3, color=color, label=f"{mouse} (15-min mean)")
        ax.plot(hours, reference[name].rolling(15, center=True, min_periods=1).mean(),
                lw=1.7, color="black", label=f"Female average ({n_mice} mice)")
        ax.set(xlabel="Hours into this day", ylabel=label, xlim=(0, 24), xticks=range(0, 25, 6))
        ax.set_title("Locomotor activity (LA)" if name == "la" else "Core body temperature (CBT)")
        ax.set_box_aspect(.75)
        ax.legend(loc="best", fontsize=8, framealpha=.9)
    predicted_class = "Estrus" if predicted else "Non-estrus"
    actual_class = "Estrus" if actual else "Non-estrus"
    title = f"{mouse}, recording day {day_index} (cycle day {phase}) · Predicted: {predicted_class} ({confidence:.0%}) · Actual: {actual_class}"
    fig.suptitle(title, fontsize=10)
    return fig, title


def feature_sections(destination, final_model, diagnostics=()):
    """Render development-only feature assessments, grouped by contributor."""
    catalog = pd.read_csv(destination / "feature_summary.csv")
    catalog["Used in final model"] = catalog.used.map({True: "Yes", False: "No"})
    def display(frame, include_owner=False):
        columns = (["owner"] if include_owner else []) + ["name", "individual_ap", "importance_ap_drop", "Used in final model"]
        table = frame[columns].rename(columns={"owner": "Person", "name": "Feature", "individual_ap": "AP on its own", "importance_ap_drop": "Contribution (AP drop)"}).copy()
        for name in ["AP on its own", "Contribution (AP drop)"]:
            table[name] = table[name].map(lambda value: f"{value:.3f}")
        return table.to_html(index=False, border=0)
    top = catalog[catalog.importance_ap_drop > 0].head(8)
    strongest = display(top, include_owner=True) if len(top) else "<p>No feature showed a positive contribution in this validation run.</p>"
    groups = []
    statuses = {item["owner"]: item["status"] for item in diagnostics}
    for owner in [*OWNERS, "Reference features"]:
        block = catalog[catalog.owner.eq(owner)]
        if block.empty:
            if owner == "Reference features":
                message = "excluded from this contributor-only run"
            elif statuses.get(owner) == "ignored":
                message = "not used in this baseline run"
            else:
                message = "no valid export yet"
            groups.append(f'<details class="feature-owner"><summary>{owner}: {message}</summary></details>')
        else:
            groups.append(f'<details class="feature-owner"><summary>{owner}: {len(block)} features, {int(block.used.sum())} used in the final model</summary>{display(block)}</details>')
    return f'''<h2>Feature selection</h2>
<p><strong>{final_model['n_features']} of {final_model['n_available']} available features are used by the final model.</strong> The model comparison tests all usable features and the configured reduced subsets. Features are ranked for selection using training data only.</p>
<h3>Most useful features</h3>
<p><strong>AP on its own</strong> measures prediction using just that feature. <strong>Contribution</strong> is how much the chosen model's validation AP drops when that feature's values are shuffled. Larger drops suggest more useful information. These are training-validation results; features that share information can hide each other's usefulness.</p>
{strongest}
<h3>All engineered features, by person</h3>
<p>Expand a person to see every included feature. “Used” marks the exact feature list in the saved model. Constant or unavailable features are excluded. Team runs use contributor features only; reference features are reserved for baseline runs.</p>
{''.join(groups)}'''


def threshold_section(destination, final_model):
    """Show the fixed-vs-selected comparison and development selection curve."""
    tuning = final_model.get("threshold_tuning", {})
    if not tuning.get("enabled"):
        return ""
    comparison = pd.read_csv(destination / "threshold_comparison.csv")
    table = comparison[["operating_point", "threshold", "accuracy", "recall", "specificity",
                        "precision", "false_negative", "false_positive"]].copy()
    for column in ["accuracy", "recall", "specificity", "precision"]:
        table[column] = table[column].map(lambda value: f"{value:.1%}")
    table["threshold"] = table.threshold.map(lambda value: f"{value:.6f}")
    table = table.rename(columns={
        "operating_point": "Cutoff rule", "threshold": "Cutoff", "accuracy": "Accuracy",
        "recall": "Estrus recall", "specificity": "Specificity", "precision": "Precision",
        "false_negative": "Missed estrus days", "false_positive": "False alarms",
    })
    curve = pd.read_csv(destination / "threshold_curve.csv")
    fig, ax = plt.subplots(figsize=(8, 3.5), layout="constrained")
    for column, label in [(tuning["objective"], "F2" if tuning["objective"] == "f2" else "Balanced accuracy"),
                          ("recall", "Estrus recall"), ("specificity", "Specificity")]:
        ax.step(curve.threshold, curve[column], where="mid", label=label)
    ax.axvline(final_model["threshold"], color="black", ls="--", label="Selected cutoff")
    ax.axvline(.5, color="gray", ls=":", label="Default 0.5")
    ax.set(xlabel="Estrus probability cutoff", ylabel="Development selection score",
           xlim=(0, 1), ylim=(0, 1.03))
    ax.legend(fontsize=8)
    picture = _image(fig, destination / "figures" / "threshold_selection.png")
    objective = ("F2, which emphasizes estrus recall while still penalizing false alarms"
                 if tuning["objective"] == "f2" else "balanced accuracy, the mean of sensitivity and specificity")
    return f'''<h2>Decision threshold</h2>
<p>The cutoff was chosen to maximize {objective} using development mice only. Each scored development mouse was excluded from model selection, fitting, and probability adjustment for its prediction. The cutoff was fixed before calculating test predictions.</p>
<p>The table compares two cutoffs on the same final model and the same reserved test mice. Probabilities and average precision are identical; only class decisions change.</p>
{table.to_html(index=False, border=0)}
<details><summary>How the cutoff was selected on development mice</summary>
<p>These development scores were used to choose the cutoff and are not independent performance estimates. They can differ from the test results above.</p>{picture}</details>'''


def render_report(root: Path, destination: Path, predictions, metrics, diagnostics, metadata):
    """Write a standalone HTML report with embedded held-out-day figures."""
    figures = destination / "figures"
    figures.mkdir(exist_ok=True)
    main_score = float(metrics.set_index("metric").loc["average_precision", "estimate"])
    comparison = pd.read_csv(destination / "model_comparison.csv")
    comparison = comparison.sort_values(["validation_ap", "chosen"], ascending=[False, False])
    trials = comparison.drop_duplicates(["family", "feature_set"])[["family", "feature_set", "validation_ap"]].copy()
    best = comparison.drop_duplicates("family")[["family", "feature_set", "validation_ap", "chosen"]].copy()
    def comparison_table(frame):
        frame = frame.rename(columns={"family": "Model", "feature_set": "Feature set", "validation_ap": "Validation AP", "chosen": "Selected"})
        frame["Model"] = frame.Model.map(MODEL_NAMES)
        frame["Validation AP"] = frame["Validation AP"].map(lambda value: f"{value:.3f}")
        if "Selected" in frame:
            frame["Selected"] = frame.Selected.map({True: "Yes", False: ""})
        return frame.to_html(index=False, border=0)
    final_model = json.loads((destination / "final_model.json").read_text())
    cutoff = final_model.get("threshold", .5)
    threshold_html = threshold_section(destination, final_model)
    saved_model_name = MODEL_NAMES[final_model["family"]]
    feature_html = feature_sections(destination, final_model, diagnostics)
    feature_html += "".join(f"<p>{html.escape(note)}</p>" for note in final_model.get("input_requirements", []))

    positive = predictions.is_estrus.eq(1)
    detected = int((positive & predictions.prediction.eq(1)).sum())
    ruled_out = int((~positive & predictions.prediction.eq(0)).sum())
    accepted = ", ".join(d["owner"] for d in diagnostics if d["status"] == "accepted")
    feature_note = f"Feature inputs: contributor features only ({html.escape(accepted)}). Reference features excluded." if accepted else "Feature inputs: reference baseline only. Contributor features are not used in this run."
    errors = [d for d in diagnostics if d["status"] == "invalid"]
    feedback = ""
    if errors:
        messages = "".join(f'<li>{html.escape(d["message"])}</li>' for d in errors)
        feedback = f'<details><summary>Feature exports that need fixing</summary><ul>{messages}</ul></details>'
    if predictions.label_source.str.contains("paper_alignment_proxy", regex=False).any():
        label_note = "Labels are provisional: days 2, 6, and 10 are treated as estrus."
    else:
        label_note = "Actual classes come from your supplied label file."

    signals = {(mouse, day): signal for mouse, day, signal in iter_days(root)}
    references = female_cycle_references(signals)
    n_reference_mice = len({mouse for mouse, _ in signals})
    ordering = predictions.assign(error=predictions.prediction != predictions.is_estrus).sort_values(["error", "predicted_class_probability"], ascending=False)
    blocks = []
    for row in ordering.itertuples(index=False):
        signal = signals[(row.mouse_id, row.day_index)]
        phase = cycle_day(row.day_index)
        fig, title = plot_mouse_day(signal, references[phase], mouse=row.mouse_id, day_index=row.day_index,
                                   predicted=row.prediction, actual=row.is_estrus,
                                   confidence=row.predicted_class_probability, n_mice=n_reference_mice)
        picture = _image(fig, figures / f"{row.mouse_id}_day_{row.day_index:02d}.png")
        blocks.append(f'<details class="example" data-error="{int(row.error)}"><summary>{html.escape(title)}</summary><p>Probability of estrus: {row.p_estrus:.1%}.</p>{picture}</details>')

    page = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estrus-day results</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 20px;color:#1d2939;background:#fafbfc}}
h1,h2{{line-height:1.2}}.score{{padding:20px;background:white;border:1px solid #d3dce5;border-radius:8px}}.score strong{{display:block;font-size:40px}}
table{{border-collapse:collapse;max-width:100%;display:block;overflow:auto}}td,th{{padding:7px 12px;border-bottom:1px solid #d3dce5;text-align:left}}img{{max-width:100%;height:auto}}
details{{background:white;border:1px solid #d3dce5;border-radius:6px;padding:12px;margin:10px 0}}summary{{cursor:pointer}}button{{padding:8px 14px;margin:4px;cursor:pointer}}
.note{{color:#52606d;font-size:14px}}
</style><main>
<h1>Estrus-day results</h1>
<p><strong>Final model: {html.escape(saved_model_name)} with {final_model['n_features']} features.</strong></p>
<p>Compared models and features on {len(final_model['training_mice'])} training mice, then tested this one chosen model on {len(predictions)} days from {predictions.mouse_id.nunique()} reserved mice.</p>
<div class="score" data-metric="average_precision"><b>Final model test score: average precision</b><strong>{main_score:.3f}</strong>
<p>Measures how well the model places estrus days near the top when days are ranked by predicted estrus probability. Higher is better; 1 is perfect. Giving every day the same score would get {positive.mean():.3f} on these labels.</p>
<p>This is the metric used to choose models. It is a ranking score, not the percentage of days classified correctly.</p></div>
<p>Using {cutoff:.6g} ({cutoff:.2%}) estrus probability as the cutoff: <strong>{detected} of {int(positive.sum())} estrus days detected</strong>; <strong>{ruled_out} of {int((~positive).sum())} non-estrus days correctly classified</strong>.</p>
<p class="note">{html.escape(label_note)}</p>
{threshold_html}
<h2>Model comparison</h2>
<p>The highest validation AP wins. All models use the same training mice and validation splits. The test score above comes from separate mice and can differ from these selection scores.</p>
{comparison_table(best)}
<details><summary>Compare feature-selection trials</summary>{comparison_table(trials)}</details>
<p class="note">{feature_note}</p>{feedback}
{feature_html}
<h2>Inspect individual days</h2>
<p>Expand a row for activity (left) and temperature (right). Colored lines show the individual mouse; black lines show the female average for the same cycle day. Both main traces use 15-minute display averages; faint colored lines show minute readings.</p>
<p class="note">The black reference first averages each mouse's three cycles, then averages all {n_reference_mice} female mice, including the displayed test mice. It is a visual comparison only. Cycle day 1 corresponds to recording days 2, 6, and 10; days 1 and 14 are buffers. The reference uses the supplied measurements without the paper's extra outlier clipping.</p>
<p class="note">Each row shows the prediction, confidence, and actual class. Confidence is the probability assigned to the predicted class, not a guarantee. Mistakes appear first.</p>
<button onclick="document.querySelectorAll('.example').forEach(e=>e.hidden=false)">All days</button>
<button onclick="document.querySelectorAll('.example').forEach(e=>e.hidden=e.dataset.error!=='1')">Mistakes only</button>
<button onclick="document.querySelectorAll('.example').forEach(e=>e.open=false)">Collapse all</button>
{''.join(blocks)}</main></html>'''
    (destination / "report.html").write_text(page, encoding="utf-8")
    return destination / "report.html"
