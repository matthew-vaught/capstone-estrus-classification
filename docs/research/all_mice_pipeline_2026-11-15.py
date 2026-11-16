"""Full-pipeline evaluation on all 13 mice, one held-out mouse at a time (Nov 15, 2026).

For each configuration and each mouse, runs the project's own ``evaluate()``
with ``test_mouse_ids=[mouse]``: model search, cutoff selection, calibration
(if any), and fitting all use only the other 12 mice. The held-out mouse's
predictions are pooled into 156 decisions per configuration.

Arms and primary metric (pooled accuracy over 156 days) were declared before
running: the retained final config, the per-fold-search leave-one-mouse-out
config that tied on the standard split, and the fixed-model fix with and
without mouse-relative features.

Usage from the repository root (one configuration per process):
    python docs/research/all_mice_pipeline_2026-11-15.py config/threshold-f2.json OUTPUT_DIR
Writes OUTPUT_DIR/<config name>_predictions.csv and _summary.json.
"""
import contextlib
import io
import json
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path("src").resolve()))
from estrus.contracts import resolve_owners  # noqa: E402
from estrus.data import load_labels  # noqa: E402
from estrus.features import assemble_features  # noqa: E402
from estrus.modeling import evaluate  # noqa: E402

warnings.filterwarnings("ignore")
config_path, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
config = json.loads(config_path.read_text())
root = Path(".").resolve()
labels = load_labels(None)
rows = []
with tempfile.TemporaryDirectory(prefix="estrus-all-mice-") as temporary:
    features, _ = assemble_features(root, Path(temporary), owners=resolve_owners(config.get("feature_owners")))
    for mouse in sorted(features.mouse_id.unique(), key=lambda m: int(m[1:])):
        run = {**config, "test_mouse_ids": [mouse]}
        with contextlib.redirect_stdout(io.StringIO()):
            predictions, _ = evaluate(features, labels, Path(temporary) / mouse, run, root=root)
        summary = json.loads((Path(temporary) / mouse / "final_model.json").read_text())
        predictions = predictions.assign(threshold=summary["threshold"], chosen=f"{summary['family']} {summary['settings']}")
        rows.append(predictions)
        wrong = predictions[predictions.prediction != predictions.is_estrus]
        print(f"{config_path.stem} {mouse}: cutoff={summary['threshold']:.3f} {summary['family']} "
              f"errors={list(zip(wrong.day_index, wrong.is_estrus, wrong.p_estrus.round(3)))}", flush=True)
result = pd.concat(rows)
y, p, d = result.is_estrus.to_numpy(), result.p_estrus.to_numpy(), result.prediction.to_numpy()
summary = {"config": str(config_path), "days": int(len(y)), "correct": int((d == y).sum()),
           "accuracy": float((d == y).mean()), "estrus_detected": int(((d == 1) & (y == 1)).sum()),
           "estrus_days": int(y.sum()), "false_alarms": int(((d == 1) & (y == 0)).sum()),
           "pooled_ap": float(average_precision_score(y, p)),
           "cutoff_range": [float(result.threshold.min()), float(result.threshold.max())]}
result.to_csv(out / f"{config_path.stem}_predictions.csv", index=False)
(out / f"{config_path.stem}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary), flush=True)
