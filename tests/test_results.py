import json

import numpy as np
import pandas as pd
import pytest

from estrus.results import publish_results


@pytest.mark.parametrize("save_details", [False, True])
def test_result_folder_is_small_and_predictions_remain_held_out(tmp_path, save_details):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "report.html").write_text("<html>Report with embedded images</html>")
    (workspace / "model.joblib").write_bytes(b"saved-model")
    (workspace / "final_model.json").write_text(json.dumps({"family": "logistic", "n_features": 2, "feature_set": "All usable features", "training_mice": ["f3", "f4"], "test_mice": ["f1", "f2"]}))
    (workspace / "metrics.csv").write_text("technical data\n")
    predictions = pd.DataFrame({
        "mouse_id": ["f1", "f2"], "day_index": [2, 3], "is_estrus": [1, 0],
        "prediction": [1, 0], "p_estrus": [.8, .1],
        "predicted_class_probability": [.8, .9], "label_source": ["paper_alignment_proxy"] * 2,
    })
    predictions.to_csv(workspace / "predictions.csv", index=False)
    metrics = pd.DataFrame({"metric": ["roc_auc", "average_precision", "recall"], "estimate": [1., 1., 1.]})
    destination = tmp_path / "results"
    publish_results(workspace, destination, predictions, metrics, save_details=save_details)
    expected = {"README.md", "report.html", "predictions.csv", "model.joblib"}
    if save_details:
        expected.add("details")
        assert (destination / "details/metrics.csv").exists()
        assert "p_estrus" in pd.read_csv(destination / "details/predictions.csv")
        assert not (destination / "details/report.html").exists()
    assert {path.name for path in destination.iterdir()} == expected
    readable = pd.read_csv(destination / "predictions.csv")
    assert list(readable) == ["mouse_id", "day_index", "actual_class", "predicted_class", "estrus_probability", "confidence"]
    assert list(readable.actual_class) == ["Estrus", "Non-estrus"]
    np.testing.assert_allclose(readable.estrus_probability, predictions.p_estrus)
    np.testing.assert_allclose(readable.confidence, predictions.predicted_class_probability)
    assert (destination / "model.joblib").read_bytes() == b"saved-model"
    assert "provisional" in (destination / "README.md").read_text()
