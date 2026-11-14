import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

from estrus import build, features
from estrus.contracts import export_features
from estrus.data import canonical_keys


def test_feature_build_uses_export_without_running_extractors_or_baseline(tmp_path, monkeypatch):
    submitted = canonical_keys()
    submitted["vivian__example"] = range(len(submitted))
    export = export_features(submitted, tmp_path, "Vivian")
    original = export.read_bytes()
    # A default build must never execute an owner's script.
    (export.parents[1] / "features.py").write_text("raise RuntimeError('Do not execute this starter')")

    def reject_baseline(_):
        pytest.fail("Unused reference features should not be recomputed")

    monkeypatch.setattr(features, "baseline_features", reject_baseline)
    assert build.main(["features"], root=tmp_path) == 0
    assembled = pd.read_csv(tmp_path / "data/outputs/build/features.csv")
    pd.testing.assert_frame_equal(assembled, submitted)
    assert export.read_bytes() == original


def test_model_build_stops_on_invalid_export_before_training(tmp_path):
    path = tmp_path / "Vivian Feature Engineering/outputs/features.csv"
    path.parent.mkdir(parents=True)
    path.write_text("mouse_id,day_index,vivian__example\nf1,2,1\n")
    assert build.main(["model"], root=tmp_path) == 1
    assert not (tmp_path / "Model Building/results").exists()


@pytest.mark.parametrize("baseline_only", [False, True])
def test_feature_assembly_computes_reference_for_fallback_and_explicit_baseline(tmp_path, monkeypatch, baseline_only):
    reference = canonical_keys()
    reference["baseline__example"] = range(len(reference))
    if baseline_only:
        contributor = reference.rename(columns={"baseline__example": "vivian__example"})
        export_features(contributor, tmp_path, "Vivian")
    monkeypatch.setattr(features, "baseline_features", lambda _: reference)
    assembled, diagnostics = features.assemble_features(tmp_path, tmp_path / "scratch", baseline_only=baseline_only)
    pd.testing.assert_frame_equal(assembled, reference)
    assert not any(item["status"] == "accepted" for item in diagnostics)


def test_regeneration_rejects_notebook_and_starter_owners(tmp_path):
    for owner in ["Vivian", "Brandon"]:
        with pytest.raises(SystemExit) as failure:
            build.main(["features", "--regenerate", owner], root=tmp_path)
        assert failure.value.code == 2


def test_explicit_missing_feature_family_stops_model_experiment(tmp_path, capsys):
    from estrus.cli import main
    submitted = canonical_keys().assign(vivian__example=range(156))
    export_features(submitted, tmp_path, "Vivian")
    config = tmp_path / "experiment.json"
    config.write_text(json.dumps({"feature_owners": ["Vivian", "Mouse Baseline"]}))
    assert main(["--root", str(tmp_path), "run", "--config", str(config)]) == 2
    assert "Explicit feature_owners require valid exports" in capsys.readouterr().err
    assert not (tmp_path / "Model Building/results").exists()


def test_clean_removes_only_build_scratch_and_refuses_symlinks(tmp_path):
    retained = ["data/inputs/fem_temp.csv", "Vivian Feature Engineering/outputs/features.csv",
                "Model Building/results/historical/report.html", "data/outputs/labels.template.csv"]
    for name in retained:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("preserve")
    scratch = tmp_path / "data/outputs/build"
    scratch.mkdir()
    (scratch / "features.csv").write_text("generated")
    assert build.main(["clean"], root=tmp_path) == 0
    assert not scratch.exists()
    assert all((tmp_path / name).read_text() == "preserve" for name in retained)
    scratch.symlink_to(tmp_path / "Model Building/results", target_is_directory=True)
    assert build.main(["clean"], root=tmp_path) == 2
    assert (tmp_path / retained[2]).read_text() == "preserve"


def test_synthetic_build_needs_no_classroom_inputs_and_replays_saved_model(tmp_path):
    project = tmp_path / "source"
    fixture = project / "tests/fixtures/synthetic_profiles.json"
    fixture.parent.mkdir(parents=True)
    shutil.copyfile(Path(__file__).parent / "fixtures/synthetic_profiles.json", fixture)
    destination = tmp_path / "synthetic-report"
    assert build.main(["test", "--output", str(destination)], root=project) == 0
    assert not (project / "data/inputs").exists()
    assert not (project / "Matthew Feature Engineering").exists()
    manifest = json.loads((destination / "details/synthetic_fixture.json").read_text())
    assert manifest["saved_model_probabilities_verified"]
    assert manifest["feature_rows"] == 156
    assert manifest["prediction_rows"] == 12
    splits = json.loads((destination / "details/splits.json").read_text())
    assert not set(splits["training_mice"]) & set(splits["test_mice"])
    assert "Invented data; scores have no biological meaning" in (destination / "report.html").read_text()
    assert (destination / "model.joblib").exists()
