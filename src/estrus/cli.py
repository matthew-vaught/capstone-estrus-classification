from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import pandas as pd

from .contracts import OWNERS, collect_features, feature_path, read_features
from .data import PROXY_SOURCE, find_root, load_labels, prepare, sha256
from .features import baseline_features


def metadata(root, config, args, diagnostics):
    paths = list((root / "data/inputs").glob("*.csv"))
    paths += [feature_path(root, d["owner"]) for d in diagnostics if d["status"] != "ignored" and feature_path(root, d["owner"]).exists()]
    provenance = {}
    for item in diagnostics:
        requirements = root / f"{item['owner']} Feature Engineering" / "input_requirements.json"
        if item["status"] == "accepted" and requirements.exists():
            paths.append(requirements)
        manifest = feature_path(root, item["owner"]).with_name("feature_metadata.json")
        if item["status"] == "accepted" and manifest.exists():
            # Preserve an optional contributor's extraction settings with run details.
            provenance[item["owner"]] = json.loads(manifest.read_text())
            paths.append(manifest)
    if args.labels:
        paths.append(Path(args.labels).resolve())
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "config": config,
            "command": sys.argv, "git_commit": revision.stdout.strip() or "uncommitted repository",
            "git_dirty": bool(status.stdout.strip()), "label_mode": str(args.labels or PROXY_SOURCE),
            "contributor_feature_metadata": provenance,
            "input_sha256": {str(p.relative_to(root) if p.is_relative_to(root) else p): sha256(p) for p in paths},
            "source_sha256": {str(p.relative_to(root)): sha256(p) for p in sorted((root / "src/estrus").glob("*.py"))},
            "versions": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "PyWavelets", "joblib"]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collaborative female mouse-day estrus classification")
    parser.add_argument("--root", type=Path, help="Repository path (otherwise locate from working directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare", help="Export day index, minute data, and label templates (ignored by Git)")
    validate = commands.add_parser("validate", help="Validate exports without training")
    validate.add_argument("--owner", choices=OWNERS)
    run = commands.add_parser("run", help="Train, evaluate, save model and HTML report")
    run.add_argument("--labels", type=Path, help="Confirmed or curated labels CSV; blank labels excluded")
    run.add_argument("--config", type=Path)
    run.add_argument("--output", type=Path, help="New or empty directory; default timestamped results folder")
    run.add_argument("--quick", action="store_true", help="Faster comparison: 2 validation folds, 40 trees, fewer settings")
    run.add_argument("--save-details", action="store_true", help="Keep optional technical records in a details/ subfolder")
    run.add_argument("--baseline", action="store_true", help="Use reference features only, ignoring team exports for a baseline comparison")
    predict = commands.add_parser("predict", help="Predict assembled feature rows using a saved model")
    predict.add_argument("--model", required=True, type=Path)
    predict.add_argument("--features", required=True, type=Path)
    predict.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "predict":
            from .modeling import predict as predict_rows
            result = predict_rows(args.model, pd.read_csv(args.features))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result.to_csv(args.output, index=False)
            print(f"Saved {len(result)} predictions to {args.output}")
            return 0
        root = args.root.resolve() if args.root else find_root()
        if args.command == "prepare":
            print(f"Prepared {prepare(root)}")
            return 0
        if args.command == "validate":
            if args.owner:
                path = feature_path(root, args.owner)
                frame = read_features(path, args.owner)
                print(f"{args.owner}: valid ({len(frame)} rows, {len(frame.columns) - 2} features)")
                return 0
            _, diagnostics = collect_features(root, pd.DataFrame(columns=["mouse_id", "day_index"]), root / "data/outputs/validation")
            return int(any(d["status"] == "invalid" for d in diagnostics))
        from .modeling import evaluate
        from .reporting import render_report
        from .results import publish_results
        config_path = args.config or root / "Model Building/config.json"
        config = json.loads(config_path.read_text())
        if args.quick:
            config.update(cv_folds=2, trees=40, quick=True)
        labels = load_labels(args.labels)
        print(f"Label sources: {', '.join(sorted(labels.label_source.unique()))}", flush=True)
        if args.labels is None:
            print("PROVISIONAL labels: recording days 2, 6, 10; days 1 and 14 excluded as buffers.", flush=True)
        destination = args.output or root / "Model Building/results" / datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")
        if destination.exists() and any(destination.iterdir()):
            raise ValueError(f"Output directory {destination} is nonempty; choose a new run directory.")
        with TemporaryDirectory(prefix="estrus-run-") as temporary:
            workspace = Path(temporary)
            baseline = baseline_features(root)
            features, diagnostics = collect_features(root, baseline, workspace, baseline_only=args.baseline)
            meta = metadata(root, config, args, diagnostics)
            meta["feature_mode"] = "contributors" if any(d["status"] == "accepted" for d in diagnostics) else "baseline"
            (workspace / "run_metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
            predictions, metrics = evaluate(features, labels, workspace, config, root=root)
            render_report(root, workspace, predictions, metrics, diagnostics, meta)
            report = publish_results(workspace, destination, predictions, metrics, save_details=args.save_details)
        print(f"Results saved to {destination.resolve()}")
        print(f"Report: {report.resolve()}")
        print("predictions.csv: one readable row per test day. model.joblib: saved trained model.")
        return 0
    except (ValueError, FileNotFoundError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
