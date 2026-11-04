"""Matthew's retrospective Morse amplitudes using the reconstruction convention.

These transforms use an entire recording, including future samples. They are
separate from the single-day Morlet features in estrus.features.
"""
from __future__ import annotations

import numpy as np
from scipy.fft import fft, fftfreq, ifft
from scipy.signal import detrend


PERIOD_GRID_HOURS = np.unique(np.r_[np.geomspace(1, 39, 96), [1, 3, 23, 24, 25, 39]])
CIRCADIAN_PERIODS_HOURS = PERIOD_GRID_HOURS[(PERIOD_GRID_HOURS >= 23) & (PERIOD_GRID_HOURS <= 25)]
ULTRADIAN_PERIODS_HOURS = PERIOD_GRID_HOURS[(PERIOD_GRID_HOURS >= 1) & (PERIOD_GRID_HOURS <= 3)]


def morse_cwt(values, periods_hours, *, sample_minutes=1, beta=5, gamma=3,
              boundary="periodic", detrend_linear=True):
    """Return period × time coefficients; a matching cosine has |W| ≈ amplitude.

    Frequency responses peak at 2. Periods refer to the response peak, not a
    package's default scale convention. This follows docs/features/matthew.md,
    without claiming equivalence to the paper's unavailable MATLAB transform.
    """
    values = np.asarray(values, dtype=float)
    periods = np.asarray(periods_hours, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("values must be a finite one-dimensional recording")
    if periods.ndim != 1 or not len(periods) or not np.isfinite(periods).all():
        raise ValueError("periods_hours must be a nonempty finite vector")
    if not all(np.isfinite(v) and v > 0 for v in (sample_minutes, beta, gamma)):
        raise ValueError("sample_minutes, beta, and gamma must be positive")
    if np.any(periods <= 2 * sample_minutes / 60):
        raise ValueError("Periods must exceed the Nyquist period")
    if boundary not in ("periodic", "reflect"):
        raise ValueError("boundary must be 'periodic' or 'reflect'")

    signal = detrend(values) if detrend_linear else values - values.mean()
    n = len(signal)
    offset = 0
    if boundary == "reflect":
        signal = np.concatenate((signal[::-1], signal, signal[::-1]))
        offset = n
    omega = 2 * np.pi * fftfreq(len(signal), d=sample_minutes / 60)
    positive = omega > 0
    peak_omega = (beta / gamma) ** (1 / gamma)
    scales = peak_omega / (2 * np.pi / periods)
    scaled_omega = scales[:, None] * omega[positive][None, :]
    log_response = (np.log(2) + beta * np.log(scaled_omega / peak_omega)
                    - scaled_omega**gamma + beta / gamma)
    response = np.zeros((len(periods), len(signal)))
    response[:, positive] = np.exp(log_response)
    coefficients = ifft(response * fft(signal)[None, :], axis=1)
    return coefficients[:, offset:offset + n]


def recording_band_amplitude(values, periods_hours, *, nonnegative=False,
                             boundary="periodic"):
    """Band max of |W| at each minute of complete 24-hour recording days.

    Missing values are rejected rather than imputed, dropped, or zero-filled.
    Both the circadian and ultradian features use linear recording detrending.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 1440 or values.size % 1440:
        raise ValueError("Recording must contain complete 1440-minute days")
    if not np.isfinite(values).all():
        raise ValueError("Wavelet recording must be finite; no gap imputation is defined")
    if nonnegative and (values < 0).any():
        raise ValueError("LA must be nonnegative")
    coefficients = morse_cwt(values, periods_hours, boundary=boundary)
    return np.abs(coefficients).max(axis=0).reshape(-1, 1440)
