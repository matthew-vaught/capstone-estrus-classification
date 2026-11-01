"""How well do DTW shift features separate estrus-proxy days? Statistics for the homework.

1. Per-feature tests: pooled AUC, per-mouse estrus minus non-estrus difference,
   exact sign-flip test over all 2^13 sign patterns, bootstrap CI over mice, and
   Holm correction across the family of Alisha's 18 DTW shift features.
2. Leave-one-mouse-out classifiers on all 13 mice: a single-feature threshold
   and logistic regression on standardised features. AUC, average precision,
   sensitivity, specificity, balanced accuracy, and a confusion matrix.
3. Permutation null: shift the estrus phase within each mouse (one of the 4
   cycle offsets, chosen at random), keeping the 1-in-4 structure.
4. Male control: the same features and tests with days 2, 6, 10 as fake "estrus".

Pre-specified primary analysis: the sign-flip test of dtw_shift_whole_temp.
It was chosen on the 10 development mice before this script was run, so
results that include those mice are partly exploratory.

Run from the repository root:
    python "Alisha Feature Engineering/analysis.py" [--cleaned] [--offset 0] [--permutations 1000]
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dtw import load_or_compute  # noqa: E402
from features import build_features  # noqa: E402

from estrus.data import ANALYSIS_DAYS, find_root  # noqa: E402

PRIMARY = "dtw_shift_whole_temp"
SEED = 190
# Chart colours (validated categorical slots 1-4 on a light surface).
SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
ESTRUS, OTHER = "#2a78d6", "#a3a29c"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def estrus_labels(days, offset):
    """Estrus = cycle day 1. Offset 0 gives recording days 2, 6, 10; 3 gives 5, 9, 13."""
    return (np.asarray(days) - 2 - offset) % 4 == 0


def load_tables(root, cleaned):
    tables = {}
    for sex, prefix in [("female", "f"), ("male", "m")]:
        frame = build_features(load_or_compute(root, sex, cleaned), [f"{prefix}{i}" for i in range(1, 14)])
        tables[sex] = frame[frame.day_index.isin(ANALYSIS_DAYS)].reset_index(drop=True)
    matthew = pd.read_csv(root / "Matthew Feature Engineering/outputs/features.csv")
    matthew.columns = [c.removeprefix("matthew__") for c in matthew.columns]
    tables["female"] = tables["female"].merge(matthew, on=["mouse_id", "day_index"])
    return tables


# ---------------------------------------------------------------- per-feature tests

def mouse_differences(values, y, groups):
    frame = pd.DataFrame({"x": values, "y": y, "g": groups})
    means = frame.groupby(["g", "y"]).x.mean().unstack()
    return (means[True] - means[False]).to_numpy()


def sign_flip_p(differences):
    """Exact two-sided p over all 2^n sign patterns of the per-mouse differences."""
    signs = np.array(list(itertools.product([1, -1], repeat=differences.size)))
    null = np.abs(signs @ differences) / differences.size
    return float(np.mean(null >= abs(differences.mean()) - 1e-12))


def bootstrap_ci(differences, rng, n=10000):
    means = differences[rng.integers(0, differences.size, (n, differences.size))].mean(axis=1)
    return np.quantile(means, [0.025, 0.975])


def holm(p_values):
    p = np.asarray(p_values)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (p.size - rank) * p[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def feature_tests(table, columns, y, rng, family):
    rows = []
    groups = table.mouse_id.to_numpy()
    for column in columns:
        values = table[column].to_numpy(dtype=float)
        d = mouse_differences(values, y, groups)
        low, high = bootstrap_ci(d, rng)
        observed = np.isfinite(values)
        rows.append({
            "feature": column, "family": family(column), "auc": roc_auc_score(y[observed], values[observed]),
            "mean_difference": d.mean(), "ci_low": low, "ci_high": high,
            "mice_higher_on_estrus": int((d > 0).sum()), "mice": d.size,
            "sign_flip_p": sign_flip_p(d),
        })
    result = pd.DataFrame(rows)
    in_family = result.family == "Alisha DTW"
    result["holm_p"] = np.nan
    result.loc[in_family, "holm_p"] = holm(result.loc[in_family, "sign_flip_p"])
    return result


# ---------------------------------------------------------------- classifiers

def leave_one_mouse_out(X, y, groups, model):
    """Pooled held-out scores and 0/1 predictions, one mouse held out at a time."""
    score, predicted = np.empty(len(y)), np.empty(len(y), dtype=bool)
    for mouse in np.unique(groups):
        held = groups == mouse
        train = X[~held]
        fill = np.nanmedian(train, axis=0)
        train = np.where(np.isnan(train), fill, train)
        test = np.where(np.isnan(X[held]), fill, X[held])
        if model == "threshold":
            # Direction and cut-off learned on training mice only.
            direction = 1 if train[y[~held], 0].mean() >= train[~y[~held], 0].mean() else -1
            s_train, s_test = direction * train[:, 0], direction * test[:, 0]
            cuts = np.unique(s_train)
            balanced = [(np.mean(s_train[y[~held]] >= c) + np.mean(s_train[~y[~held]] < c)) / 2 for c in cuts]
            score[held], predicted[held] = s_test, s_test >= cuts[int(np.argmax(balanced))]
        else:
            fitted = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, class_weight="balanced", max_iter=3000))
            fitted.fit(train, y[~held])
            score[held] = fitted.predict_proba(test)[:, 1]
            predicted[held] = score[held] >= 0.5
    return score, predicted


def metrics(y, score, predicted):
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[False, True]).ravel()
    sensitivity, specificity = tp / (tp + fn), tn / (tn + fp)
    return {"auc": roc_auc_score(y, score), "average_precision": average_precision_score(y, score),
            "sensitivity": sensitivity, "specificity": specificity,
            "balanced_accuracy": (sensitivity + specificity) / 2,
            "accuracy": (tp + tn) / len(y), "TP": tp, "FN": fn, "FP": fp, "TN": tn}


def phase_shuffled_labels(days, groups, rng):
    offsets = {mouse: rng.integers(0, 4) for mouse in np.unique(groups)}
    return np.array([estrus_labels(d, offsets[g]) for d, g in zip(days, groups)])


# ---------------------------------------------------------------- plots

def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.6)
    ax.set_axisbelow(True)


def strip_grid(table, columns, y, stats, title, path, ncols=6):
    """Every mouse-day as a dot; a thin line joins each mouse's two means."""
    rows = int(np.ceil(len(columns) / ncols))
    fig, axes = plt.subplots(rows, ncols, figsize=(2.6 * ncols, 2.7 * rows), facecolor=SURFACE, squeeze=False)
    rng = np.random.default_rng(0)
    groups = table.mouse_id.to_numpy()
    for ax, column in zip(axes.flat, columns):
        style(ax)
        values = table[column].to_numpy(dtype=float)
        means = pd.DataFrame({"x": values, "y": y, "g": groups}).groupby(["g", "y"]).x.mean().unstack()
        for _, row in means.iterrows():
            ax.plot([0, 1], [row[False], row[True]], color=MUTED, linewidth=0.8, alpha=0.6, zorder=2)
        for position, mask, colour in [(0, ~y, OTHER), (1, y, ESTRUS)]:
            jitter = position + rng.uniform(-0.18, 0.18, mask.sum())
            ax.scatter(jitter, values[mask], s=9, color=colour, alpha=0.55, linewidths=0, zorder=1)
        ax.set_xticks([0, 1], ["other", "estrus"])
        ax.set_xlim(-0.5, 1.5)
        s = stats.set_index("feature").loc[column]
        p = s.holm_p if np.isfinite(s.holm_p) else s.sign_flip_p
        label = "Holm p" if np.isfinite(s.holm_p) else "p"
        ax.set_title(f"{column}\nAUC {s.auc:.2f}, {label} {p:.3f}", fontsize=8, color=INK)
    for ax in list(axes.flat)[len(columns):]:
        ax.axis("off")
    fig.suptitle(title, fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def roc_plot(curves, path):
    fig, ax = plt.subplots(figsize=(5.6, 5.2), facecolor=SURFACE)
    style(ax)
    ax.grid(color="#e6e5e0", linewidth=0.6)
    ax.plot([0, 1], [0, 1], color=OTHER, linewidth=1, linestyle=":", label="chance (AUC 0.50)")
    for (label, y, score, colour, dashed) in curves:
        fpr, tpr, _ = roc_curve(y, score)
        ax.plot(fpr, tpr, color=colour, linewidth=2, linestyle="--" if dashed else "-",
                label=f"{label} (AUC {roc_auc_score(y, score):.2f})")
    ax.set_xlabel("False positive rate (1 − specificity)", color=MUTED, fontsize=9)
    ax.set_ylabel("True positive rate (sensitivity)", color=MUTED, fontsize=9)
    ax.set_title("Leave-one-mouse-out ROC, all 13 mice", fontsize=11, color=INK, loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def primary_plot(tables, labels, path):
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.6), facecolor=SURFACE, sharey=True)
    rng = np.random.default_rng(0)
    for ax, sex in zip(axes, ["female", "male"]):
        style(ax)
        table, y = tables[sex], labels[sex]
        values = table[PRIMARY].to_numpy()
        means = pd.DataFrame({"x": values, "y": y, "g": table.mouse_id}).groupby(["g", "y"]).x.mean().unstack()
        for _, row in means.iterrows():
            ax.plot([0, 1], [row[False], row[True]], color=MUTED, linewidth=0.8, alpha=0.6)
        for position, mask, colour in [(0, ~y, OTHER), (1, y, ESTRUS)]:
            ax.scatter(position + rng.uniform(-0.18, 0.18, mask.sum()), values[mask], s=11,
                       color=colour, alpha=0.6, linewidths=0)
        ax.axhline(0, color=MUTED, linewidth=0.6)
        names = ["other days", "estrus days"] if sex == "female" else ["other days", "days 2, 6, 10"]
        ax.set_xticks([0, 1], names)
        ax.set_xlim(-0.5, 1.5)
        ax.set_title(f"{sex.capitalize()}s, AUC {roc_auc_score(y, values):.2f}", fontsize=10, color=INK, loc="left")
    axes[0].set_ylabel("Temperature timing shift (minutes)\nnegative = runs later than other days", color=MUTED, fontsize=8.5)
    fig.suptitle("Primary feature: whole-day temperature DTW shift", fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cleaned", action="store_true", help="Use the paper's cleaning before DTW")
    parser.add_argument("--offset", type=int, default=0, choices=range(4), help="0: estrus days 2, 6, 10; 1: 3, 7, 11; ...")
    parser.add_argument("--permutations", type=int, default=1000)
    args = parser.parse_args()

    root = find_root()
    out = HERE / "outputs" / "analysis" / f"{'cleaned' if args.cleaned else 'raw'}_offset{args.offset}"
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    tables = load_tables(root, args.cleaned)
    labels = {sex: estrus_labels(t.day_index, args.offset) for sex, t in tables.items()}

    shift = [c for c in tables["male"].columns if c.startswith("dtw_shift_")]
    matthew = [c for c in tables["female"].columns if c not in tables["male"].columns]
    family = lambda c: "Alisha DTW" if c.startswith("dtw_") else "Matthew (comparison)"  # noqa: E731

    # 1. Per-feature tests.
    stats = []
    for sex in ["female", "male"]:
        columns = shift + (matthew if sex == "female" else [])
        result = feature_tests(tables[sex], columns, labels[sex], rng, family)
        stats.append(result.assign(sex=sex))
    stats = pd.concat(stats)[["sex", "feature", "family", "auc", "mean_difference", "ci_low", "ci_high",
                              "mice_higher_on_estrus", "mice", "sign_flip_p", "holm_p"]]
    stats.to_csv(out / "feature_tests.csv", index=False)

    # 2-4. Classifiers, permutation null, male control.
    sets = [
        (f"{PRIMARY} (threshold)", [PRIMARY], "threshold"),
        ("Alisha shift, 18 (logistic)", shift, "logistic"),
        ("Matthew, 4 (logistic)", matthew, "logistic"),
        ("Alisha shift + Matthew, 22 (logistic)", shift + matthew, "logistic"),
    ]
    rows, scores = [], {}
    for sex in ["female", "male"]:
        table, y = tables[sex], labels[sex]
        groups, days = table.mouse_id.to_numpy(), table.day_index.to_numpy()
        for name, columns, model in sets:
            if not set(columns) <= set(table.columns):
                continue
            X = table[columns].to_numpy(dtype=float)
            score, predicted = leave_one_mouse_out(X, y, groups, model)
            scores[(sex, name)] = score
            row = {"sex": sex, "feature_set": name, **metrics(y, score, predicted)}
            if sex == "female":
                null = np.array([roc_auc_score(shuffled, leave_one_mouse_out(X, shuffled, groups, model)[0])
                                 for shuffled in (phase_shuffled_labels(days, groups, rng)
                                                  for _ in range(args.permutations))])
                row["permutation_p"] = (1 + np.sum(null >= row["auc"])) / (1 + null.size)
                row["null_auc_95th"] = np.quantile(null, 0.95)
            rows.append(row)
            print(f"{sex:6s} {name:42s} AUC {row['auc']:.3f}", flush=True)
    classifiers = pd.DataFrame(rows)
    classifiers.to_csv(out / "classifier_results.csv", index=False)

    # Plots.
    for sex in ["female", "male"]:
        strip_grid(tables[sex], shift, labels[sex], stats[stats.sex == sex],
                   f"{sex.capitalize()}s: DTW shift features, every mouse-day (blue = estrus{'' if sex == 'female' else ' days 2, 6, 10'})",
                   out / f"strip_shift_{sex}.png")
    strip_grid(tables["female"], matthew, labels["female"], stats[stats.sex == "female"],
               "Females: Matthew's features for comparison", out / "strip_matthew_female.png", ncols=4)
    primary_plot(tables, labels, out / "primary_feature.png")
    curves = [(name, labels["female"], scores[("female", name)], colour, False)
              for (name, _, _), colour in zip(sets, SERIES)]
    curves.append(("Male control: Alisha shift", labels["male"], scores[("male", sets[1][0])], MUTED, True))
    roc_plot(curves, out / "roc.png")

    pd.set_option("display.width", 200)
    print("\nPrimary analysis (females):")
    print(stats[(stats.sex == "female") & (stats.feature == PRIMARY)].round(4).to_string(index=False))
    print("\nClassifiers (leave-one-mouse-out, all 13 mice):")
    print(classifiers.round(3).to_string(index=False))
    print(f"\nSaved tables and plots to {out}")


if __name__ == "__main__":
    main()
