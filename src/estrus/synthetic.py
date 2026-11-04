"""Run the shared pipeline on invented recordings without classroom data."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from .cli import main as estrus_main
from .contracts import export_features
from .data import MINUTES_PER_DAY, MICE, prepare, sha256
from .features import baseline_features


def write_recordings(root: Path, fixture: dict) -> None:
    """Expand five hand-checkable hour anchors to the production input schema.

    The real loader intentionally enforces 13 mice and 14 one-minute days.
    Generated CSVs satisfy that shape in a temporary directory; only the small
    invented profile definition is versioned. No real measurements are used.
    """
    inputs = root / "data/inputs"
    inputs.mkdir(parents=True)
    hours = np.arange(MINUTES_PER_DAY) / 60
    for signal, filename in [("cbt", "fem_temp.csv"), ("la", "fem_act.csv")]:
        mice = {}
        for index, mouse in enumerate(MICE):
            days = []
            for day in range(1, 15):
                profile = fixture["estrus" if day in (2, 6, 10) else "non_estrus"][signal]
                values = np.interp(hours, fixture["hours"], profile)
                variation = (index + 1) * .003 + .02 * np.sin(hours * np.pi + day + index)
                days.append(values + variation)
            mice[mouse] = np.concatenate(days)
        pd.DataFrame(mice).to_csv(inputs / filename, index=False)


def smoke_test(project: Path, destination: Path) -> Path:
    """Build, validate, fit, report, and reload predictions using synthetic data.

    Two reference summaries are exported under a synthetic contributor schema
    to exercise CSV handoff. These are stand-ins, not an owner's real features.
    """
    from .modeling import predict

    destination = destination.resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Synthetic output must be a new or empty directory.")
    fixture_path = project / "tests/fixtures/synthetic_profiles.json"
    fixture = json.loads(fixture_path.read_text())
    with TemporaryDirectory(prefix="estrus-synthetic-") as temporary:
        checkout = Path(temporary)
        write_recordings(checkout, fixture)
        prepared = prepare(checkout)
        # Reload prepared files, so serialization and the real label validator
        # participate in the smoke test too.
        labels = pd.read_csv(prepared / "labels.paper_proxy.csv")
        labels["label_source"] = "synthetic_fixture_NO_BIOLOGICAL_MEANING"
        labels_path = checkout / "synthetic_labels.csv"
        labels.to_csv(labels_path, index=False)
        reference = baseline_features(checkout)
        features = reference[["mouse_id", "day_index", "baseline__cbt_mean", "baseline__la_mean"]].rename(columns={
            "baseline__cbt_mean": "matthew__synthetic_cbt_mean",
            "baseline__la_mean": "matthew__synthetic_la_mean",
        })
        export_features(features, checkout, "Matthew")
        config = checkout / "config.json"
        config.write_text(json.dumps(fixture["config"]))
        for command in [
            ["--root", str(checkout), "validate"],
            ["--root", str(checkout), "run", "--labels", str(labels_path),
             "--config", str(config), "--output", str(destination), "--save-details"],
        ]:
            if estrus_main(command):
                raise ValueError("Synthetic pipeline failed; see the preceding error.")
        saved = pd.read_csv(destination / "predictions.csv")
        assembled = saved[["mouse_id", "day_index"]].merge(features, validate="one_to_one")
        replay = predict(destination / "model.joblib", assembled)
        np.testing.assert_allclose(replay.p_estrus, saved.estrus_probability)
        manifest = {
            "purpose": "Software smoke test only; scores have no biological meaning.",
            "fixture_sha256": sha256(fixture_path),
            "input_sha256": {p.name: sha256(p) for p in sorted((checkout / "data/inputs").glob("*.csv"))},
            "feature_rows": len(features), "prediction_rows": len(saved),
            "saved_model_probabilities_verified": True,
        }
        (destination / "details/synthetic_fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Make synthetic status prominent in both shareable entry points.
        readme = destination / "README.md"
        readme.write_text("# Synthetic software check\n\nInvented data; scores have no biological meaning.\n\n" + readme.read_text())
        report = destination / "report.html"
        report.write_text(report.read_text().replace("<h1>Estrus-day results</h1>", "<h1>Synthetic software check</h1><p><strong>Invented data; scores have no biological meaning.</strong></p>"))
    print(f"Synthetic build and saved-model replay passed. Report: {destination / 'report.html'}")
    return destination / "report.html"
