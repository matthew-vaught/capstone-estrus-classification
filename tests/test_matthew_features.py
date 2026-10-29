"""Numerical and integration checks for Matthew's recording-context features."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from estrus import wavelets
from estrus.contracts import input_requirements, read_features
from estrus.data import canonical_keys, find_root, load_signals


@pytest.fixture(scope="module")
def matthew():
    root = find_root(Path(__file__).parent)
    spec = importlib.util.spec_from_file_location("matthew_features", root / "Matthew Feature Engineering/features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("period", [2., 24.])
def test_morse_matching_cosine_recovers_amplitude_not_power(period):
    hours = np.arange(14 * 1440) / 60
    amplitude = 3.7
    values = 20 + amplitude * np.cos(2 * np.pi * hours / period)
    coefficients = wavelets.morse_cwt(values, [period], detrend_linear=False)
    np.testing.assert_allclose(np.abs(coefficients), amplitude, atol=1e-11)
    np.testing.assert_allclose(wavelets.morse_cwt(np.ones(1440), [period]), 0, atol=1e-12)


def test_band_grid_and_maximum_precede_time_mean(monkeypatch):
    np.testing.assert_allclose(wavelets.CIRCADIAN_PERIODS_HOURS,
                              [23, 23.623267980838676, 24, 24.552064994038158, 25])
    assert wavelets.ULTRADIAN_PERIODS_HOURS[0] == 1
    assert wavelets.ULTRADIAN_PERIODS_HOURS[-1] == 3
    coefficients = np.zeros((2, 1440), dtype=complex)
    coefficients[0, :720] = 2j
    coefficients[1, 720:] = 4j
    monkeypatch.setattr(wavelets, "morse_cwt", lambda *args, **kwargs: coefficients)
    result = wavelets.recording_band_amplitude(np.ones(1440), [1, 3])
    assert result.mean() == 3  # max(mean(abs(W))) would incorrectly give 2.


def test_recording_day_pairing_direction_buffer_and_first_half(matthew, monkeypatch):
    circadian = np.repeat(np.array([10., 12., 9.])[:, None], 1440, axis=1)
    ultradian = np.tile(np.r_[np.repeat(2., 720), np.repeat(100., 720)], (3, 1))

    def amplitudes(values, periods, **kwargs):
        return circadian if np.array_equal(periods, wavelets.CIRCADIAN_PERIODS_HOURS) else ultradian

    monkeypatch.setattr(matthew, "recording_band_amplitude", amplitudes)
    result = matthew.extract_recording_features(np.ones(3 * 1440), np.full(3 * 1440, 37.))
    np.testing.assert_allclose(result[matthew.FEATURE_NAMES[0]], [2, np.nan, np.nan])
    np.testing.assert_allclose(result.circadian_la_next_day_delta_untrimmed, [2, -3, np.nan])
    np.testing.assert_allclose(result[matthew.FEATURE_NAMES[1]], 2)
    np.testing.assert_array_equal(result.day_index, [1, 2, 3])
    assert np.isnan(result.loc[1, "circadian_la_amplitude_next_day"])
    assert result.loc[1, "circadian_la_amplitude_next_day_untrimmed"] == 9
    assert result.la_next_day_delta_excluded.tolist() == [False, True, True]
    assert np.isnan(result.loc[2, "circadian_la_amplitude_next_day"])


def test_fractions_use_strict_thresholds_window_and_observed_denominator(matthew):
    day = pd.DataFrame({"cbt": np.full(1440, 100.), "la": np.full(1440, 1000.)})
    day.iloc[360:720, :] = [37.2, 15.0]
    values = matthew.extract_features(day)
    assert values[matthew.FEATURE_NAMES[2]] == 0
    assert values[matthew.FEATURE_NAMES[3]] == 0
    day.iloc[360:504, :] = [38., 16.]
    day.iloc[648:720, :] = np.nan  # 288 observed; exactly 80% coverage.
    values = matthew.extract_features(day)
    assert values[matthew.FEATURE_NAMES[2]] == .5
    assert values[matthew.FEATURE_NAMES[3]] == .5
    day.iloc[647, 0] = np.nan
    values = matthew.extract_features(day)
    assert np.isnan(values[matthew.FEATURE_NAMES[2]])
    assert values[matthew.FEATURE_NAMES[3]] == .5


@pytest.mark.parametrize("problem", ["nan", "inf", "negative", "partial", "misaligned"])
def test_wavelet_recording_rejects_unestablished_gap_policies(matthew, problem):
    la, cbt = np.ones(3 * 1440), np.full(3 * 1440, 37.)
    if problem == "nan":
        cbt[100] = np.nan
    elif problem == "inf":
        la[100] = np.inf
    elif problem == "negative":
        la[100] = -1
    elif problem == "partial":
        la, cbt = la[:-1], cbt[:-1]
    else:
        cbt = cbt[:-1]
    with pytest.raises(ValueError):
        matthew.extract_recording_features(la, cbt)


def test_real_export_keeps_156_rows_and_excludes_only_final_la_deltas(matthew):
    root = find_root(Path(__file__).parent)
    frame, inspection = matthew.build_features(root)
    pd.testing.assert_frame_equal(frame[["mouse_id", "day_index"]], canonical_keys())
    assert list(frame.columns[2:]) == ["matthew__" + name for name in matthew.FEATURE_NAMES]
    assert frame.shape == (156, 6)
    final_day = frame.day_index.eq(13)
    delta = frame["matthew__" + matthew.FEATURE_NAMES[0]]
    assert delta.isna().equals(final_day)
    assert delta.notna().sum() == 143
    assert np.isfinite(delta[~final_day]).all()
    assert np.isfinite(frame.iloc[:, 3:].to_numpy()).all()
    assert inspection.la_next_day_delta_excluded.equals(final_day)
    assert inspection.next_day_is_buffer.sum() == 13
    assert inspection.loc[inspection.day_index.eq(13), "next_day_index"].eq(14).all()
    np.testing.assert_allclose(frame.iloc[:, 2], inspection.circadian_la_amplitude_next_day
                               - inspection.circadian_la_amplitude)
    exported = read_features(root / "Matthew Feature Engineering/outputs/features.csv", "Matthew")
    pd.testing.assert_frame_equal(frame, exported, check_exact=False, rtol=1e-12)
    # Compute against original full-recording coefficients, including final buffer.
    signals = load_signals(root)
    coefficients = wavelets.morse_cwt(signals["la"].f1.to_numpy(), wavelets.CIRCADIAN_PERIODS_HOURS)
    reference = np.abs(coefficients).max(axis=0).reshape(14, 1440).mean(axis=1)
    f1 = inspection[inspection.mouse_id.eq("f1")]
    np.testing.assert_allclose(f1.circadian_la_amplitude, reference[1:13])
    np.testing.assert_allclose(f1.circadian_la_amplitude_next_day.iloc[:-1], reference[2:13])
    np.testing.assert_allclose(f1.circadian_la_amplitude_next_day_untrimmed, reference[2:14])
    assert np.isnan(f1.iloc[-1][matthew.FEATURE_NAMES[0]])
    assert f1.iloc[-2][matthew.FEATURE_NAMES[0]] == pytest.approx(reference[12] - reference[11])


def test_matthew_context_notes_do_not_apply_to_other_contributors(matthew):
    columns = ["matthew__" + name for name in matthew.FEATURE_NAMES]
    assert len(input_requirements(columns)) == 3
    assert "complete recording" in input_requirements(columns)[0]
    assert input_requirements(["baseline__mean", "vivian__example"]) == []
