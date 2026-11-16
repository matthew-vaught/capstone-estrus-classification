"""Exploratory leave-one-mouse-out benchmark, November 15, 2026.

Compares feature transforms (raw, mouse-relative robust z, adjacent-day
contrast) and model families on all 13 mice: each mouse is predicted by a model
fitted on the other twelve. Fixed settings, no nested selection; 54 setups were
compared, so the best rows are optimistic. Results are summarized in
docs/research/mouse-relative-2026-11-15.md.

Usage, from the repository root with the project environment active:
    python docs/research/lomo_benchmark_2026-11-15.py . OUTPUT_DIR
Writes OUTPUT_DIR/lomo_results.csv (and caches reference features as ref.csv).
"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectPercentile, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, ExtraTreesClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, accuracy_score, balanced_accuracy_score

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "src"))
KEYS = ["mouse_id", "day_index"]

def load(path):
    return pd.read_csv(ROOT / path)

contrib = load("Matthew Feature Engineering/outputs/features.csv")
for p in ["Alisha Feature Engineering/outputs/features.csv", "Vivian Feature Engineering/outputs/features.csv"]:
    contrib = contrib.merge(load(p), on=KEYS)
labels = load("data/outputs/labels.paper_proxy.csv")[KEYS + ["is_estrus"]]

ref_path = Path(sys.argv[2]) / "ref.csv"
if ref_path.exists():
    ref = pd.read_csv(ref_path)
else:
    from estrus.features import baseline_features
    ref = baseline_features(ROOT)
    ref.to_csv(ref_path, index=False)
ref = ref[[c for c in ref if not c.endswith("missing_fraction")]]

def mouse_z(df, cols):
    g = df.groupby("mouse_id")[cols]
    med = g.transform("median"); iqr = g.transform(lambda s: s.quantile(.75) - s.quantile(.25))
    return ((df[cols] - med) / iqr.replace(0, np.nan)).fillna(0).add_suffix("__mz")

def neighbor(df, cols):
    df = df.sort_values(KEYS)
    out = {}
    for c in cols:
        g = df.groupby("mouse_id")[c]
        nb = pd.concat([g.shift(1), g.shift(-1)], axis=1).mean(axis=1)
        out[c + "__nb"] = df[c] - nb
    return pd.DataFrame(out, index=df.index)

def build(base, transform):
    df = base.merge(labels, on=KEYS).sort_values(KEYS).reset_index(drop=True)
    cols = [c for c in base if c not in KEYS]
    parts = []
    if "raw" in transform: parts.append(df[cols])
    if "mz" in transform: parts.append(mouse_z(df, cols))
    if "nb" in transform: parts.append(neighbor(df, cols))
    if "mznb" in transform: parts.append(neighbor(pd.concat([df[KEYS], mouse_z(df, cols)], axis=1), [c + "__mz" for c in cols]))
    X = pd.concat(parts, axis=1)
    return X, df.is_estrus.to_numpy(), df.mouse_id.to_numpy()

def lr(C=1., pct=None, penalty="l2"):
    steps = [("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]
    if pct: steps.append(("k", SelectPercentile(f_classif, percentile=pct)))
    steps.append(("m", LogisticRegression(C=C, penalty=penalty, solver="liblinear" if penalty == "l1" else "lbfgs", class_weight="balanced", max_iter=5000)))
    return Pipeline(steps)

MODELS = {
    "LR C1 top35 (current)": lambda: lr(1, 35),
    "LR C0.1 all": lambda: lr(.1),
    "LR L1 C0.3": lambda: lr(.3, penalty="l1"),
    "RF d3": lambda: Pipeline([("i", SimpleImputer(strategy="median")), ("m", RandomForestClassifier(300, max_depth=3, min_samples_leaf=3, class_weight="balanced", random_state=0))]),
    "ExtraTrees": lambda: Pipeline([("i", SimpleImputer(strategy="median")), ("m", ExtraTreesClassifier(500, min_samples_leaf=3, class_weight="balanced", random_state=0))]),
    "HistGB shallow": lambda: HistGradientBoostingClassifier(max_depth=2, learning_rate=.05, max_iter=200, min_samples_leaf=8, class_weight="balanced", random_state=0),
}

def lomo(model_fn, X, y, g):
    p = np.zeros(len(y))
    for m in np.unique(g):
        tr, te = g != m, g == m
        p[te] = model_fn().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return p

def per_mouse_z(p, g):
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    s = pd.Series(lp).groupby(g)
    return ((pd.Series(lp) - s.transform("mean")) / s.transform("std")).to_numpy()

def summarize(name, model, y, g, p):
    z = per_mouse_z(p, g)
    per_mouse_ap = np.mean([average_precision_score(y[g == m], p[g == m]) for m in np.unique(g)])
    return {"features": name, "model": model, "n_feat": None,
            "AP": average_precision_score(y, p), "AUC": roc_auc_score(y, p),
            "acc@0.5": accuracy_score(y, p >= .5), "bal_acc@0.5": balanced_accuracy_score(y, p >= .5),
            "AP mouse-z score": average_precision_score(y, z),
            "acc mouse-z>0.8": accuracy_score(y, z > .8),
            "mean within-mouse AP": per_mouse_ap}

rows = []
configs = [
    ("C28 raw", contrib, ["raw"]),
    ("C28 mouse-z", contrib, ["mz"]),
    ("C28 raw+mouse-z", contrib, ["raw", "mz"]),
    ("C28 raw+neighbor", contrib, ["raw", "nb"]),
    ("C28 mouse-z+neighbor", contrib, ["mz", "mznb"]),
    ("Ref raw", ref, ["raw"]),
    ("Ref mouse-z+neighbor", ref, ["mz", "mznb"]),
    ("C28+Ref raw", contrib.merge(ref, on=KEYS), ["raw"]),
    ("C28+Ref mouse-z+neighbor", contrib.merge(ref, on=KEYS), ["mz", "mznb"]),
]
for fname, base, tf in configs:
    X, y, g = build(base, tf)
    X = X.to_numpy(dtype=float)
    for mname, fn in MODELS.items():
        p = lomo(fn, X, y, g)
        r = summarize(fname, mname, y, g, p); r["n_feat"] = X.shape[1]
        rows.append(r)
        print(f"{fname:28s} {mname:22s} AP={r['AP']:.3f} AUC={r['AUC']:.3f} acc={r['acc@0.5']:.3f} zAP={r['AP mouse-z score']:.3f} zacc={r['acc mouse-z>0.8']:.3f}", flush=True)
out = pd.DataFrame(rows)
out.to_csv(Path(sys.argv[2]) / "lomo_results.csv", index=False)
