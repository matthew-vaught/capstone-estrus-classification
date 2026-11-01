# Alisha Feature Engineering

Alisha contributes 18 within-mouse dynamic time warping (DTW) time-shift features through [outputs/features.csv](outputs/features.csv). They measure how much earlier or later a day's core body temperature (CBT) or locomotor activity (LA) pattern runs than the same mouse's other days. Generate and validate from the repository root:

```bash
python -m pip install numba   # only needed to regenerate; model building reads the CSV
python "Alisha Feature Engineering/features.py"
estrus validate --owner Alisha
```

The first run computes all DTW alignments (under a minute with numba) and caches them in `outputs/cache/`, which is ignored by Git. The cache is recomputed automatically if the input CSVs change.

## Features

All names have the `alisha__` prefix and exist for both signals: `_temp` (CBT) and `_act` (LA).

| Feature (without `alisha__`) | Meaning / units | Rationale | Missing values |
| --- | --- | --- | --- |
| `dtw_shift_whole_{temp,act}` | For each other day of the mouse, align the two whole-day curves with DTW and average (j − i) along the optimal path; then average over the 13 other days. Minutes; positive means this day's pattern runs earlier, negative later | A DTW distance says only *whether* a day differs; the alignment path says how it differs in timing | None: computed from complete recordings |
| `dtw_shift_seg1_{temp,act}` … `dtw_shift_seg8_{temp,act}` | The same within 3-hour segment s (s = 1 is hours [0,3), s = 8 is hours [21,24)), aligned only against the same segment on the other days | Locates when in the day timing differs | As above |

Shifts are antisymmetric (the shift of a vs b is minus the shift of b vs a). The path's mean offset also responds to how long high or low stretches last, not only to a pure time shift, so read it as "where the alignment moves", not as a measured phase.

**Main signal.** `dtw_shift_whole_temp` is lower (later) on days 2, 6, and 10 than on other days in all 13 female mice. The same calculation on males separates nothing (AUC ≈ 0.5), and in females only the 2, 6, 10 offset separates, so the effect is female-specific and 4-day periodic, not a recording-schedule artifact.

**Feature choice.** These features replaced an earlier set of DTW distance features after a comparison using only the 10 development mice (the shared test mice f3, f6, f11 were excluded). Those choices used development-mouse labels, so validation scores on those mice are exploratory. Shared-model test (3 reserved mice, seed 190): Matthew's 4 features gave average precision 0.748; adding these 18 gave 0.803.

## Method details

**DTW:** L1 cost, unconstrained, D[i,j] = |A_i − B_j| + min(D[i−1,j−1], D[i−1,j], D[i,j−1]), matching MATLAB's default `dtw` for scalar series. One-minute readings, no resampling. The path is traced back from the last cell, preferring the diagonal on ties. Each mouse is only compared with itself.

**Cleaning:** the export uses the raw recordings, like the other contributors. `analysis.py --cleaned` applies the Smarr and Kriegsfeld (2022) cleaning as a sensitivity check: CBT below 35 is set to 35, then values beyond 3 SD of the mouse's recording mean are clipped (activity: high side only).

## Input scope: retrospective, like Matthew's wavelets

Every feature compares a day with the mouse's other days, including later days and the buffer days 1 and 14. They therefore need the mouse's complete recording and cannot be computed for an isolated new day. Day 1 and day 14 contribute raw readings only and are never rows. No labels, cycle position, or day number enter the calculation, and no quantity is learned across mice. All of a mouse's days stay in one evaluation partition because the shared model splits by mouse.

## Statistics (homework analysis)

```bash
python "Alisha Feature Engineering/analysis.py"              # raw data, estrus = days 2, 6, 10
python "Alisha Feature Engineering/analysis.py" --cleaned    # paper's cleaning first
python "Alisha Feature Engineering/analysis.py" --offset 3   # estrus = days 5, 9, 13
```

Writes to `outputs/analysis/<raw|cleaned>_offset<k>/`:

- `feature_tests.csv`: per feature and sex: pooled AUC, per-mouse estrus minus non-estrus mean difference with a bootstrap 95% CI over mice, the number of mice in each direction, an exact two-sided sign-flip p over all 2^13 = 8192 sign patterns, and Holm-adjusted p. **Holm family:** the 18 shift features, which includes the 8 segments for each signal. Matthew's 4 features are reported for comparison, outside the family. With 13 mice, the smallest possible sign-flip p is 2/8192 ≈ 0.00024.
- `classifier_results.csv`: leave-one-mouse-out (all days of a mouse held out together, all 13 mice) single-feature threshold and logistic regression (standardised, C = 0.1, balanced class weights). AUC, average precision, sensitivity, specificity, balanced accuracy, accuracy, and confusion counts. For females, `permutation_p` compares the AUC with a null in which each mouse's estrus phase is shifted to a random one of the 4 cycle offsets (1,000 shuffles), keeping the 1-in-4 structure. Males are the control, with days 2, 6, 10 as fake "estrus".
- `roc.png`, `primary_feature.png`, and `strip_*.png`: every mouse-day as a dot, with a line joining each mouse's two means.

**Primary analysis (stated before running):** the sign-flip test of `dtw_shift_whole_temp` in females. It was chosen on the 10 development mice, so tests that include them are partly exploratory; the 3 test mice alone are too few for a sign-flip test (the smallest possible p is 0.25).

Plain accuracy is reported but not used for conclusions: always predicting "not estrus" scores 75%.

## Files

- [dtw.py](dtw.py): numba DTW alignment, loading, optional cleaning, and the cached 14 × 14 shift matrices per mouse, signal, and scope (whole day + 8 segments), for both sexes.
- [features.py](features.py): builds and exports the 156 female rows.
- [analysis.py](analysis.py): statistics, classifiers, permutation null, male control, and plots.
