"""Nested leave-one-mouse-out test of per-mouse score normalization, Nov 15, 2026.

For each outer mouse, everything is chosen from the other 12 mice only:
an inner leave-one-mouse-out loop gives out-of-fold scores for those 12, a
cutoff is chosen on them, then a model fitted on all 12 scores the outer mouse
and the frozen cutoff makes its decisions. The outer mouse's labels are never
used for fitting or for choosing the cutoff.

Arms (declared before running): features {original 28, + mouse-relative copies}
x decision score {calibrated-free probability, per-mouse z-scored logit}
x cutoff objective {f2, balanced_accuracy}. Model fixed to the configuration the
full pipeline selected in every recent run: logistic regression, C=1, top 35%.

Usage from the repository root:
    python docs/research/nested_lomo_score_norm_2026-11-15.py OUTPUT_DIR
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectPercentile, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, fbeta_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path("src").resolve()))
from estrus.modeling import add_mouse_relative  # noqa: E402

warnings.filterwarnings("ignore")
KEYS = ["mouse_id", "day_index"]
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

features = pd.read_csv("Matthew Feature Engineering/outputs/features.csv")
for owner in ["Alisha", "Vivian"]:
    features = features.merge(pd.read_csv(f"{owner} Feature Engineering/outputs/features.csv"), on=KEYS)
labels = pd.read_csv("data/outputs/labels.paper_proxy.csv")[KEYS + ["is_estrus"]]


def model():
    return Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()),
                     ("select", SelectPercentile(f_classif, percentile=35)),
                     ("model", LogisticRegression(C=1., class_weight="balanced", max_iter=5000))])


def mouse_z(probability, groups):
    """Within-mouse z-score of the logit: label-free, uses only that mouse's days."""
    logit = np.log(np.clip(probability, 1e-9, 1) / np.clip(1 - probability, 1e-9, 1))
    s = pd.Series(logit).groupby(groups)
    return ((pd.Series(logit) - s.transform("mean")) / s.transform("std")).to_numpy()


def score(probability, groups, kind):
    return probability if kind == "probability" else mouse_z(probability, groups)


OBJECTIVES = {"f2": lambda y, d: fbeta_score(y, d, beta=2, zero_division=0),
              "balanced_accuracy": balanced_accuracy_score}


def choose_cutoff(y, s, objective):
    """Midpoints between distinct development scores; ties resolved to the middle tied cutoff."""
    values = np.unique(s)
    candidates = values[:-1] + np.diff(values) / 2
    rows = [(c, OBJECTIVES[objective](y, s >= c)) for c in candidates]
    best = max(v for _, v in rows)
    tied = [c for c, v in rows if np.isclose(v, best, atol=1e-12)]
    return float(np.median(tied))


def oof(X, y, g):
    p = np.zeros(len(y))
    for m in np.unique(g):
        p[g == m] = model().fit(X[g != m], y[g != m]).predict_proba(X[g == m])[:, 1]
    return p


rows, decisions = [], []
for feature_name, frame in [("original 28", features), ("+ mouse-relative", add_mouse_relative(features))]:
    data = frame.merge(labels, on=KEYS).sort_values(KEYS).reset_index(drop=True)
    X = data.drop(columns=KEYS + ["is_estrus"]).to_numpy(float)
    y, g = data.is_estrus.to_numpy(), data.mouse_id.to_numpy()
    outer_p = np.zeros(len(y))
    inner = {}
    for m in np.unique(g):
        dev = g != m
        inner[m] = oof(X[dev], y[dev], g[dev])  # out-of-fold for the 12 development mice
        outer_p[~dev] = model().fit(X[dev], y[dev]).predict_proba(X[~dev])[:, 1]
    for kind in ["probability", "mouse_z"]:
        for objective in ["f2", "balanced_accuracy"]:
            predicted = np.zeros(len(y), dtype=int)
            cutoffs = []
            for m in np.unique(g):
                dev = g != m
                cutoff = choose_cutoff(y[dev], score(inner[m], g[dev], kind), objective)
                cutoffs.append(cutoff)
                predicted[~dev] = score(outer_p[~dev], g[~dev], kind) >= cutoff
            tp = int(((predicted == 1) & (y == 1)).sum()); fp = int(((predicted == 1) & (y == 0)).sum())
            final_score = score(outer_p, g, kind)
            rows.append({"features": feature_name, "decision_score": kind, "objective": objective,
                         "accuracy": float((predicted == y).mean()), "correct": int((predicted == y).sum()),
                         "estrus_detected": tp, "false_alarms": fp,
                         "AP_of_score": float(average_precision_score(y, final_score)),
                         "cutoff_min": float(min(cutoffs)), "cutoff_max": float(max(cutoffs))})
            decisions.append(data[KEYS + ["is_estrus"]].assign(
                features=feature_name, decision_score=kind, objective=objective,
                p_estrus=outer_p, score=final_score, prediction=predicted))
            r = rows[-1]
            print(f"{feature_name:17s} {kind:12s} {objective:17s} acc={r['accuracy']:.3f} ({r['correct']}/156) "
                  f"detected={tp}/39 false_alarms={fp} AP={r['AP_of_score']:.3f} cutoffs={r['cutoff_min']:.2f}-{r['cutoff_max']:.2f}", flush=True)

pd.DataFrame(rows).to_csv(OUT / "nested_lomo_summary.csv", index=False)
pd.concat(decisions).to_csv(OUT / "nested_lomo_decisions.csv", index=False)
