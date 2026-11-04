# Matthew Feature Engineering

Matthew contributes four features through [outputs/features.csv](../../Matthew%20Feature%20Engineering/outputs/features.csv). Model building automatically combines this validated export with any other valid teammate exports; it may select a subset. Generate the CSV before training:

```bash
python "Matthew Feature Engineering/features.py"
estrus validate --owner Matthew
estrus run --save-details
```

## The four features

All names below have the `matthew__` prefix in the model input.

| Feature | Definition / units | Rationale |
| --- | --- | --- |
| `circadian_la_amplitude_next_day_delta` | A[d+1] − A[d] for recording days 2–12; NaN for day 13. Units: counts/minute; A is the daily mean of the sample-level maximum Morse amplitude over 23–25 hours | Change in circadian activity amplitude within the same mouse |
| `cbt_ultradian_amplitude_h0_12` | Mean of sample-level maximum Morse amplitude over periods of 1–3 hours, during elapsed hours [0,12); °C | Test the observed reduction in first-half CBT ultradian amplitude on estrus-proxy days |
| `cbt_fraction_above_37_2_h6_12` | Observed CBT readings strictly > 37.2 °C divided by observed CBT readings in elapsed hours [6,12); fraction | Elevated temperature occupancy |
| `la_fraction_above_15_h6_12` | Observed LA readings strictly > 15 counts/minute divided by observed LA readings in elapsed hours [6,12); fraction | Elevated activity occupancy |

The threshold fractions match [exploratory analysis.ipynb](../../Matthew%20Feature%20Engineering/exploratory%20analysis.ipynb): raw minutes 360–719, no interpolation, no smoothing, strict `>`, and at least 288 of 360 readings observed per signal. Otherwise a fraction is NaN. These thresholds were selected using development mice and are frozen here; extraction never loads labels or retunes them. Subsequent validation on those development mice is exploratory because feature design already used their labels. The notebook's nested assessment found that simple window means slightly outperformed these fractions on their own; inclusion here follows the requested feature experiment.

## Recording context and wavelets

**This contribution changes the input scope to retrospective classification of complete recordings.** Both wavelet features use each mouse's full 14-day recording. The LA delta explicitly uses the next day, and centered wavelets plus whole-recording detrending also use later samples. These inputs cannot be computed from an isolated day or used for online/end-of-day prediction. All days and wavelet context from a mouse must stay in the same evaluation partition; the shared model already splits by mouse.

The implementation uses analytic generalized Morse CWT, beta=5, gamma=3, peak-2 frequency response, one-minute sampling, linear detrending per full recording, periodic FFT boundary, and **absolute coefficient amplitude**, not squared power. No additional activity normalization, smoothing, or outlier clipping is applied. Matthew's transform code is in [wavelets.py](../../Matthew%20Feature%20Engineering/wavelets.py), alongside the feature exporter. Tests are in [tests/test_matthew_features.py](../../Matthew%20Feature%20Engineering/tests/test_matthew_features.py); run them with `python -m pytest "Matthew Feature Engineering/tests"`.

The period grid is `unique(concatenate(geomspace(1, 39, 96), [1,3,23,24,25,39]))`. The circadian band keeps the same five samples in [23,25] as the handoff; the ultradian band keeps all samples in [1,3]. At each minute take the maximum amplitude across the selected band, **then** average over the specified time window. This is a reconstruction convention, not numerical equivalence to the paper's unavailable MATLAB implementation.

Exported keys remain `f1`–`f13`, recording days **2–13**, using the repository's 1-based day numbering. Transform all 14 days first, retaining day 14's raw readings as surrounding wavelet context. Use next-day LA comparisons only for target days **2–12**. **Day 13's LA delta is NaN for each mouse**, because its next-day amplitude would come from the endpoint-sensitive final buffer. This yields **143 observed deltas and 13 missing deltas across all 156 target rows**. Day 13 retains its other three features. The model fills the missing LA feature using a median fitted only on the fitting data: separately in each validation fold, then on the final training mice for the saved model. No test values or labels determine that median. This replacement is a typical training value, not a recovered measurement of day 13's LA change.

Day 14 is never a model row, and the comparison never wraps to day one. Its raw readings still contribute to the full-recording wavelet. Excluding the final comparison avoids explicitly relying on day 14's daily amplitude; it does not remove all wavelet boundary effects or make the transform suitable for online prediction.

Clock/light alignment is unconfirmed; hours 0–12 and 6–12 are relative to the recording-day segment. Do not label them dark hours until the row-zero timing is verified.

Wavelet extraction rejects any nonfinite value in either complete signal and negative LA. It fails before replacing an existing export; it never silently fills a recording gap or compresses time. The independently callable fraction extractor supports NaNs using the coverage rule above. The supplied recordings are complete. Model-fold median imputation handles any exported missing feature values.

## Inspection and reproducibility

`outputs/wavelet_inspection.csv` contains current and eligible next-day amplitudes, the model delta, the exact next-day index, and exclusion/buffer flags. Columns ending in `_untrimmed` preserve raw estimates, including the excluded final-buffer comparison, for diagnostics only. These inspection columns are **not** model features. `outputs/feature_metadata.json` records input/source hashes, units, periods, parameters, boundary/aggregation rules, threshold provenance, package versions, and the information cutoff. Only `outputs/features.csv` is consumed as model input. Regenerate all three together after changing extraction. Model runs retain optional contributor metadata in `--save-details` records and read [input_requirements.json](../../Matthew%20Feature%20Engineering/input_requirements.json) to carry matching retrospective requirements and threshold provenance into the saved model, report, and run README.

Keep mouse identity and day indices as join keys only. No cycle position, labels, or population averages enter feature extraction. See the shared [feature contract](../FEATURE_CONTRACT.md) and [methods](../METHODS.md) for evaluation limitations and the explicitly documented retrospective exception.

To reproduce the boundary/buffer diagnostic without changing the model inputs:

```bash
python "Matthew Feature Engineering/check_wavelet_sensitivity.py"
```

This writes `outputs/wavelet_sensitivity.csv`. On the supplied recordings, changing periodic to reflected boundaries changes the day 13 LA delta's sign for **6 of 13 mice**; the largest day-13 difference is about **12.61 counts/minute**. The table also compares LA deltas after removing the real buffers before transforming (a sensitivity experiment, not the production rule). This diagnostic examines untrimmed estimates; the production feature now excludes the day 13 comparison. Retain the prescribed periodic settings for reproducibility. No thresholds, labels, or classifier are tuned by this diagnostic.

The local historical run `matthew-four-features-buffer-masked` excluded the final LA comparisons. See the [results reproduction guide](../RESULTS.md) to generate a report in a fresh checkout. The older `matthew-four-features/` run used day 14 amplitudes for those comparisons and is historical. Generated model results are ignored by Git; subsequent feature changes require a new run in a new results directory.
