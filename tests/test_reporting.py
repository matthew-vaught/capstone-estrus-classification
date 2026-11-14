import json
import re

import numpy as np
import pandas as pd
import pytest

from estrus import reporting


def test_cycle_alignment_uses_recording_days_and_excludes_buffers():
    for day in range(2, 14):
        assert reporting.cycle_day(day) == (day - 2) % 4 + 1
    assert [reporting.cycle_day(day) for day in [2, 6, 10]] == [1, 1, 1]
    for day in [1, 14]:
        with pytest.raises(ValueError, match="2 through 13"):
            reporting.cycle_day(day)


def test_reference_averages_cycles_then_mice_with_equal_mouse_weights():
    def signal(value):
        return pd.DataFrame({"la": np.repeat(value, 1440), "cbt": np.repeat(value + 35, 1440)})
    signals = {
        ("f1", 2): signal(0.), ("f1", 6): signal(2.), ("f1", 10): signal(4.),
        ("f2", 2): signal(10.), ("f2", 6): signal(np.nan), ("f2", 10): signal(np.nan),
        ("f1", 3): signal(20.), ("f2", 3): signal(30.),
        ("f1", 1): signal(1000.), ("f2", 14): signal(1000.),
    }
    original = signals[("f1", 2)].copy(deep=True)
    reference = reporting.female_cycle_references(signals)
    # Mouse means are 2 and 10: equal-mouse mean = 6, rather than pooled 4.
    np.testing.assert_allclose(reference[1].la, 6.)
    np.testing.assert_allclose(reference[1].cbt, 41.)
    np.testing.assert_allclose(reference[2].la, 25.)
    assert set(reference) == {1, 2}
    pd.testing.assert_frame_equal(original, signals[("f1", 2)])


def test_day_panels_are_side_by_side_with_matched_black_reference():
    signal = pd.DataFrame({"la": np.arange(1440, dtype=float), "cbt": np.repeat(37., 1440)})
    reference = pd.DataFrame({"la": np.repeat(8., 1440), "cbt": np.repeat(38., 1440)})
    fig, title = reporting.plot_mouse_day(signal, reference, mouse="f11", day_index=6,
                                         predicted=0, actual=1, confidence=.8, n_mice=13)
    try:
        assert len(fig.axes) == 2
        left, right = fig.axes
        assert left.get_subplotspec().rowspan == right.get_subplotspec().rowspan
        assert left.get_subplotspec().colspan.start < right.get_subplotspec().colspan.start
        assert left.get_title() == "Locomotor activity (LA)"
        assert right.get_title() == "Core body temperature (CBT)"
        for ax, expected in [(left, 8.), (right, 38.)]:
            black = [line for line in ax.lines if line.get_color() == "black"]
            assert len(black) == 1
            np.testing.assert_allclose(black[0].get_ydata(), expected)
            assert "Female average (13 mice)" in black[0].get_label()
            assert ax.get_box_aspect() == .75
        assert "recording day 6 (cycle day 1)" in title
    finally:
        reporting.plt.close(fig)


@pytest.mark.parametrize("tuning", [False, True])
def test_report_distinguishes_selection_scores_and_final_test_and_lists_features(tmp_path, monkeypatch, tuning):
    predictions = pd.DataFrame({
        "mouse_id": ["f1", "f2"], "day_index": [2, 3],
        "is_estrus": [1, 0], "prediction": [0, 0], "p_estrus": [.2, .1],
        "predicted_class_probability": [.8, .9], "label_source": ["paper_alignment_proxy"] * 2,
    })
    metrics = pd.DataFrame({"metric": ["average_precision", "roc_auc"], "estimate": [.63, .99]})
    pd.DataFrame({
        "family": ["logistic", "random_forest", "rbf_svm"],
        "feature_set": ["All usable features"] * 3,
        "validation_ap": [.98, .8, .7], "chosen": [True, False, False],
    }).to_csv(tmp_path / "model_comparison.csv", index=False)
    cutoff = .175 if tuning else .5
    (tmp_path / "final_model.json").write_text(json.dumps({"family": "logistic", "n_features": 1, "n_available": 2, "training_mice": ["f3", "f4"], "threshold": cutoff,
                                                          "threshold_tuning": {"enabled": tuning, "objective": "f2"}}))
    if tuning:
        from estrus.modeling import metric_values, select_threshold
        pd.DataFrame([
            {"operating_point": name, "threshold": value,
             **metric_values(predictions.is_estrus, predictions.p_estrus, threshold=value)}
            for name, value in [("Default", .5), ("Development-selected", cutoff)]
        ]).to_csv(tmp_path / "threshold_comparison.csv", index=False)
        _, curve = select_threshold([1, 0], [.4, .1])
        curve.to_csv(tmp_path / "threshold_curve.csv", index=False)
        predictions["prediction"] = [1, 0]
        predictions["predicted_class_probability"] = [.2, .9]
    pd.DataFrame({"owner": ["Vivian", "Reference features"], "name": ["power", "constant"], "feature": ["vivian__power", "baseline__constant"], "used": [True, False], "individual_ap": [.8, .25], "importance_ap_drop": [.2, 0.]}).to_csv(tmp_path / "feature_summary.csv", index=False)
    signal = pd.DataFrame({"cbt": 37 + np.sin(np.arange(1440) / 100), "la": np.ones(1440)})
    monkeypatch.setattr(reporting, "iter_days", lambda _: iter([("f1", 2, signal), ("f2", 3, signal)]))

    def image_stub(fig, path):
        reporting.plt.close(fig)
        return '<img src="data:image/png;base64,example" alt="Mouse-day plot">'

    monkeypatch.setattr(reporting, "_image", image_stub)
    report = reporting.render_report(tmp_path, tmp_path, predictions, metrics, [], {})
    page = report.read_text()
    assert re.search(r'data-metric="average_precision".*?<strong>0\.630</strong>', page, re.S)
    assert page.count('data-metric=') == 1
    assert page.count('<details class="example"') == 2
    assert 'Automatic model choice' not in page
    assert 'Validation AP' in page
    assert 'Final model test score' in page
    assert 'Vivian: 1 features, 1 used in the final model' in page
    assert 'Matthew: no valid export yet' in page
    assert 'Reference features: 1 features, 0 used in the final model' in page
    assert 'AP on its own' in page and 'Contribution (AP drop)' in page
    assert 'not the percentage of days classified correctly' in page
    assert f'{int(tuning)} of 1 estrus days detected' in page
    assert '1 of 1 non-estrus days correctly classified' in page
    assert ('Predicted: Estrus (20%)' if tuning else 'Predicted: Non-estrus (80%)') in page
    assert 'Actual: Estrus' in page
    assert 'recording day 2 (cycle day 1)' in page
    assert 'recording day 3 (cycle day 2)' in page
    assert 'black lines show the female average for the same cycle day' in page
    if tuning:
        assert '0.175 (17.50%)' in page
        assert 'Using 0.5 ' not in page
        assert 'Missed estrus days' in page and 'False alarms' in page
        assert 'not independent performance estimates' in page
    for jargon in ['ROC AUC', 'Brier', 'log loss', 'bootstrap', 'calibration', 'permutation', '95%']:
        assert jargon not in page
