# Handoff: compare a mouse's circadian LA amplitude with its next day

## Instructions for the receiving Codex agent

Implement a daily feature that compares **the same mouse's circadian locomotor
activity (LA) wavelet amplitude on day d and day d+1**. Follow the target
repository's conventions for reusable code, dependencies, tests, and data.
This file is self-contained; access to the capstone repository is optional.

The default comparison is a signed difference:

```text
circadian_la_amplitude_next_day_delta = A[d+1] - A[d]
```

Positive means the next day has stronger circadian LA amplitude; negative means
it has weaker amplitude. Keep both daily amplitudes beside the difference for
inspection. This default interprets “compare” as a change in daily mean
amplitude, rather than similarity between two entire within-day curves.

Before integrating this into a model, establish the prediction time, available
data, day boundary, sampling interval, and whether inference is retrospective
or prospective. Those choices affect correctness; see the timing section below.

## Origin and exact meaning of amplitude

This describes the **current capstone reconstruction**, using:

- `src/mouse_wavelets.py`: `morse_cwt` and `band_max`.
- `notebooks/exploratory/estrus_la_circadian_power.ipynb`: full-recording LA
  transform, circadian band amplitude, and daily aggregation.
- `notebooks/exploratory/figure_2_wavelet_rhythms.ipynb`: period grid and
  reconstruction settings.
- `tests/test_mouse_wavelets.py`: synthetic normalization checks.

It does not establish numerical equivalence to the paper's unavailable modified
MATLAB implementation. The transferable specification is the implementation
described here.

Use **absolute coefficient magnitude `abs(W)`**, not squared magnitude
`abs(W)**2`. Historical notebook variables and CSV fields named `power`, including
`circadian_power`, currently contain amplitude. Check their quantity metadata;
do not infer the spectral quantity from those names alone.

The transform uses a peak-2 frequency response: a real cosine of amplitude B at
a matching sampled period has wavelet magnitude approximately B. Under this
convention, amplitude retains the input signal's units. For the supplied
one-minute LA data, those are activity counts/min. A changed sampling/binning
scheme requires checking the input units again.

## Calculation to preserve

For each mouse and uninterrupted recording separately:

1. Sort by time and validate regular sampling, unique sample times, finite LA,
   and the expected units. Keep mouse and recording identity throughout.
2. Transform the **whole continuous recording**, including available buffer
   days, using the settings below. Do not transform each day separately.
3. Take the magnitude of each complex coefficient.
4. At each sample, take the **maximum over sampled periods in 23–25 hours**.
5. Remove buffer days after the transform.
6. Average the remaining sample-level band amplitudes within each defined
   24-hour day to obtain A[d].
7. Join day d to exactly day d+1 within the same mouse and recording. Subtract
   the current amplitude from the next-day amplitude.

In notation:

```text
W[p, t] = MorseCWT(LA)[p, t]
a[t]    = max over sampled p in [23, 25] hours of abs(W[p, t])
A[d]    = mean of a[t] over samples belonging to day d
delta[d] = A[d+1] - A[d]
```

The order matters: take the band maximum **before** the daily mean. Do not
replace this with a maximum of daily mean spectra, mean across periods, or an
exact-24-hour coefficient alone. Those define different features. Transforming
daily mean raw LA would also discard the within-day signal we need.

| Setting | Capstone value |
|---|---|
| Transform | Analytic generalized Morse continuous wavelet transform |
| Parameters | beta = 5, gamma = 3 |
| Sampling | One sample per minute |
| Frequency response normalization | Peak magnitude 2 |
| Detrending | Linear detrend of each complete recording before transforming |
| Boundary | Periodic: endpoints are joined by the FFT implementation |
| Circadian band | Inclusive 23–25 hours |
| Spectral quantity | Absolute amplitude `abs(W)` |
| Within-band reduction | Maximum at each sample |
| Within-day reduction | Arithmetic mean |
| Activity normalization / extra smoothing | None |
| Original buffer rule | Transform 14 days, discard first and last day |

Build the periods exactly this way to match the existing reconstruction:

```python
full_grid = np.unique(np.r_[np.geomspace(1, 39, 96), [1, 3, 23, 24, 25, 39]])
periods_hours = full_grid[(full_grid >= 23) & (full_grid <= 25)]
# [23.0, 23.623267980838676, 24.0, 24.552064994038158, 25.0]
```

Computing just these five rows gives the same circadian coefficients as selecting
them from the full grid: each period's response is computed independently. A
different grid can change the per-sample maximum, so record the grid explicitly.

## Days, missingness, and recording identity

In the original CSVs, rows are consecutive one-minute samples and columns are
mouse IDs. There are no timestamps. The first 1,440 rows are recording day 0;
the next 1,440 are recording day 1, and so on. Transform all 20,160 rows, then
keep recording days 1–12. These correspond to analysis days 1–12 in the current
notebook. This gives **11 adjacent-day comparisons per mouse**; the final
retained day has no retained next-day value. With 13 mice, there are 156 daily
rows and 143 nonmissing deltas.

In the other project, use its documented biological or recording day boundary.
Do not assume calendar midnight or infer light-cycle alignment from the capstone
CSV. Timestamped input needs an explicit day anchor; use consecutive 24-hour
experimental windows if that is the intended meaning of “day.” Local calendar
dates around daylight-saving changes may not contain 24 hours.

Do not join separate recording sessions merely because they share a mouse ID.
Use a recording/session key, or a globally unique mouse-recording key, too.
Keep actual day offsets; do not renumber retained days after dropping a day.
An exact day-key join avoids accidentally comparing day 3 with day 5 when day 4
is absent. Never wrap the last day back to the first day.

The current transform rejects NaNs. The reference code below requires complete,
finite days and never imputes. If the new data contain gaps, establish and
document a gap policy before transforming; do not silently delete samples,
compress time, or turn missing activity into zero. If using contiguous segments,
treat each as its own recording and reconsider buffers. Report excluded samples,
days, and recordings. The supplied capstone LA is treated as already corrected;
that assumption does not establish preprocessing for a different dataset.

Keep each chronological day. The other notebook's four-day cycle folding,
estrus grouping, population averages, and `cycle_contrasts` are not part of this
feature. In particular, its within-cycle Day 4/Day 1 contrast is not an
adjacent-day pairing.

## Prediction timing and leakage

The requested feature explicitly uses day d+1. A row indexed by day d therefore
contains future observations relative to the end of day d. Use it as a model
input only when those observations are available at the intended prediction
time. Otherwise it may be an outcome/target, or the feature definition must change.

There is a second timing issue: this full-recording wavelet is **noncausal**.
Coefficients around day d use neighboring samples, potentially beyond day d+1.
Full-recording detrending also uses the complete recording, and the periodic
boundary couples its endpoints. The amplitude is a temporally smoothed estimate
of a roughly 24-hour oscillation, not an isolated measurement of that day's LA.

- **Retrospective analysis of complete recordings:** the specification here is
  suitable when complete recordings are available at inference and this matches
  the modeling task. Document the information used.
- **Prediction during an ongoing recording:** do not reuse the full-recording
  values as though they were available online. A next-day observation cannot be
  an input available today. Even switching to A[d] − A[d−1] is insufficient if
  those amplitudes were computed using later data. A separate implementation
  must compute preprocessing and transforms using only data available at each
  cutoff, with a documented window, endpoint rule, and any reporting delay.
  Validate that changing samples after the cutoff cannot change its features.

Evaluation must match the use case. For new-mouse generalization, split by mouse
and keep its sessions together. For future-time prediction in known mice, use
chronological evaluation and prevent preprocessing or transform windows from
crossing the information cutoff. Random daily splits can share mouse identity,
overlapping day pairs, and wavelet context across train and test. Fit any model
scaling or learned imputation using training data only. One-day edge trimming
reduces boundary concerns; it does not prove edge effects or leakage are absent.

## Standalone reference implementation

This is the retrospective implementation. It requires NumPy, SciPy, and pandas.
Use the target repository's existing equivalents if present; if it uses uv,
declare missing dependencies through `uv add numpy scipy pandas` as needed.
Do not replace the Morse transform with another library's defaults without
checking its wavelet parameters, normalization, and period mapping.

The first function below is copied from the capstone's current implementation.
The daily and pairing functions adapt it to the requested feature. Put reusable
logic in the target project's normal source directory and test it there.

```python
"""Analytic generalized Morse CWT for the Figure 2 exploration.

Uses a peak-2 frequency response so a real sinusoid of amplitude A has
|W| approximately A at its matching period. This is an explicit convention,
not a claim of equivalence to the paper's unpublished modified MATLAB code.
"""

import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq, ifft
from scipy.signal import detrend


def morse_cwt(
    values: np.ndarray,
    periods_hours: np.ndarray,
    *,
    sample_minutes: float = 1,
    beta: float = 5,
    gamma: float = 3,
    boundary: str = "periodic",
    detrend_linear: bool = True,
) -> np.ndarray:
    """Return period × time complex coefficients for one finite recording.

    Period labels refer to the peak of the wavelet's frequency response.
    ``periodic`` joins endpoints; ``reflect`` mirrors a full recording at each
    end. The notebook discards real buffer days AFTER this transform.
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
    # log response avoids the overflow/underflow of omega**beta * exp(-omega**gamma).
    scaled_omega = scales[:, None] * omega[positive][None, :]
    log_response = (
        np.log(2) + beta * np.log(scaled_omega / peak_omega)
        - scaled_omega**gamma + beta / gamma
    )
    response = np.zeros((len(periods), len(signal)))
    response[:, positive] = np.exp(log_response)
    coefficients = ifft(response * fft(signal)[None, :], axis=1)
    return coefficients[:, offset:offset + n]


def daily_circadian_la_amplitude(values, *, sample_minutes=1, trim_days=1):
    """One continuous recording, starting at a known 24-hour day boundary."""
    values = np.asarray(values, dtype=float)
    if (values.ndim != 1 or values.size < 2
            or not np.isfinite(values).all() or (values < 0).any()):
        raise ValueError("Expected finite, nonnegative, one-dimensional LA")
    if not np.isfinite(sample_minutes) or sample_minutes <= 0:
        raise ValueError("sample_minutes must be positive and finite")
    samples_per_day_float = 1440 / sample_minutes
    samples_per_day = int(round(samples_per_day_float))
    if samples_per_day < 1 or not np.isclose(
        samples_per_day_float, samples_per_day, rtol=0, atol=1e-8
    ):
        raise ValueError("Sampling interval must divide a 24-hour day")
    if not isinstance(trim_days, (int, np.integer)) or trim_days < 0:
        raise ValueError("trim_days must be a nonnegative integer")
    if values.size % samples_per_day:
        raise ValueError("Recording must contain complete 24-hour days")
    n_days = values.size // samples_per_day
    if n_days <= 2 * trim_days:
        raise ValueError("No complete analysis days remain after trimming")

    full_grid = np.unique(np.r_[np.geomspace(1, 39, 96), [1, 3, 23, 24, 25, 39]])
    periods = full_grid[(full_grid >= 23) & (full_grid <= 25)]
    coefficients = morse_cwt(
        values, periods, sample_minutes=sample_minutes,
        beta=5, gamma=3, boundary="periodic", detrend_linear=True,
    )
    sample_amplitude = np.abs(coefficients).max(axis=0)
    stop_day = n_days - trim_days
    retained = sample_amplitude[
        trim_days * samples_per_day:stop_day * samples_per_day
    ]
    return pd.DataFrame({
        "recording_day": np.arange(trim_days, stop_day),
        "circadian_la_amplitude": retained.reshape(-1, samples_per_day).mean(axis=1),
    })


def add_next_day_comparison(daily):
    """Exact next-day pairing; absent next days remain NaN."""
    keys = ["mouse_id", "recording_id", "recording_day"]
    amplitude = "circadian_la_amplitude"
    required = [*keys, amplitude]
    if daily[required].isna().any().any():
        raise ValueError("Daily keys and amplitudes must be nonmissing")
    if not pd.api.types.is_integer_dtype(daily["recording_day"]):
        raise ValueError("recording_day must contain integer day offsets")
    if daily.duplicated(keys).any():
        raise ValueError("Expected one row per mouse, recording, and day")
    values = daily[amplitude].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Daily amplitudes must be finite and nonnegative")

    current = daily[required].sort_values(keys).reset_index(drop=True)
    following = current.rename(columns={amplitude: "circadian_la_amplitude_next_day"})
    # Relabel the next day's value with its predecessor's key for an exact join.
    following = following.assign(recording_day=following["recording_day"] - 1)
    result = current.merge(following, on=keys, how="left", validate="one_to_one")
    result["circadian_la_amplitude_next_day_delta"] = (
        result["circadian_la_amplitude_next_day"] - result[amplitude]
    )
    return result
```

Example for the capstone-style wide CSV (one recording, one mouse per column):

```python
from pathlib import Path

recordings = pd.read_csv(Path("data/sex_diff_paper_data/fem_act.csv"))
daily_tables = []
for mouse_id in recordings.columns:
    mouse_daily = daily_circadian_la_amplitude(recordings[mouse_id].to_numpy())
    daily_tables.append(mouse_daily.assign(
        mouse_id=mouse_id, recording_id="female_la_recording_1"
    ))
daily = pd.concat(daily_tables, ignore_index=True)
features = add_next_day_comparison(daily)
```

For long-format input, group by mouse and recording and validate each group's
timestamp spacing and day anchor before passing its sorted LA values. The
reference function cannot detect missing timestamps from a bare value array.
The 14-day length is specific to the example; the function accepts other complete
recording lengths. One-day trimming is the reproduction default, not a universally
validated buffer length for a new dataset.

## Output and interpretation

| Column | Meaning |
|---|---|
| `mouse_id` | Mouse identifier |
| `recording_id` | Uninterrupted recording/session identifier |
| `recording_day` | Integer offset from that recording's first day boundary |
| `circadian_la_amplitude` | A[d], daily mean circadian band amplitude |
| `circadian_la_amplitude_next_day` | A[d+1] in the same mouse/recording |
| `circadian_la_amplitude_next_day_delta` | A[d+1] − A[d] |

For amplitudes `[10, 12, 9]` on consecutive days, deltas are `[2, -3, NaN]`.
For days `[1, 3]`, both deltas are missing: neither has an observed day d+1.
Retain missing comparisons and count them; do not replace them with zero.

If a relative comparison is needed, an optional secondary feature is:

```text
percent_change[d] = 100 * (A[d+1] - A[d]) / A[d]
```

It is undefined when A[d] is zero and unstable near zero. Leave it missing for
an invalid denominator and document any minimum-amplitude threshold. Do not add
an unexplained epsilon or silently substitute a ratio for the signed difference.
For A[d] = 10 and A[d+1] = 12, the signed delta is 2 and percent change is 20%.

## Validation before model integration

- A matching 24-hour cosine with a known amplitude should recover that amplitude
  under `morse_cwt(..., detrend_linear=False)` on an integer-cycle periodic
  recording. Test normalization separately from the default linear detrending.
- Constant LA should produce approximately zero amplitude. For arbitrary input,
  the daily amplitudes must be finite and nonnegative.
- Compare a real capstone mouse's 12 daily values against the existing notebook
  using identical settings. Confirm amplitude rather than squared magnitude.
- `[10, 12, 9]` must yield `[2, -3, NaN]`. Verify unsorted rows, skipped days,
  duplicate day keys, multiple mice, and multiple sessions for one mouse.
- The output must preserve the daily row count. The original 14-day data must
  yield 12 retained daily values and 11 valid deltas per mouse.
- Invalid sampling, nonfinite values, negative LA, partial days, or too-short
  recordings must fail clearly. Do not silently drop or fill them.
- Inspect sensitivity to endpoint handling and buffer length on the target data.
  Adjacent amplitudes share temporal context; a daily delta is not a precise
  instantaneous change at the day boundary.

Save metadata alongside generated features: input identity/hash, sample interval
and units, day anchor, preprocessing, wavelet parameters and normalization,
period grid, detrending, boundary rule, buffer rule, aggregation order,
comparison direction, package versions, and information cutoff policy. Preserve
raw data; follow the target repository's artifact storage and DVC conventions.
