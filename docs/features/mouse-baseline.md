# Mouse Baseline feature experiment

**Status:** excluded from the final model, as confirmed November 13, 2026. This page preserves the experiment's definitions and reproduction instructions. Use [config/threshold-f2.json](../../config/threshold-f2.json) for the retained final setup; see [the comparison](../RESULTS.md#feature-experiments-excluded-from-the-final-model).

The new `Mouse Baseline Feature Engineering/` folder contains a separately named experiment. It leaves Matthew's, Vivian's, Alisha's, and Brandon's code/notebooks/exports unchanged. The [extractor](../../Mouse%20Baseline%20Feature%20Engineering/features.py) exports four `mouse_baseline__` features; it does not read labels, mouse-stage assignments, probabilities, or model results.

## Rationale from the existing work

Matthew's [exploratory notebook](../../Matthew%20Feature%20Engineering/exploratory%20analysis.ipynb) studied elevated CBT and LA during elapsed hours 6–12. Its nested comparisons found that simple window means performed well compared with tuned threshold fractions. The first two new features retain those exact windows and means but express them relative to each animal's typical value, rather than add another sensor threshold.

The third feature retains Matthew's first-half 1–3-hour CBT amplitude measurement and its suppression hypothesis. The fourth retains his next-day minus current-day 23–25-hour LA amplitude change. Relative scaling asks whether a given amplitude/change is large or small for this animal. Vivian's separate per-mouse-centered exploration and Alisha's within-mouse comparisons provide additional motivation for individual references; their reported scores do not establish the benefit of this particular normalization.

These four definitions were chosen before inspecting their new model results. They are mechanistically motivated hypotheses, not established improvements or independent biological biomarkers. Joint LA–CBT relationships remain a separate future experiment.

## Exact definitions

For target day `d`, let `B(x,d)` be the median of summary `x` over the same mouse's **other eleven analysis days (2–13)**. Exclude the target day's summary and both buffer-day summaries. Use all stages without consulting labels. Thus this is a typical-recording baseline, not a confirmed non-estrus baseline.

| Name after `mouse_baseline__` | Formula | Interpretation / units |
| --- | --- | --- |
| `cbt_mean_h6_12_minus_median` | `T[d] - B(T,d)` | Extra temperature in the established window, °C; `T` is the raw observed-minute CBT mean in hours [6,12) |
| `la_mean_h6_12_relative_median` | `L[d] / B(L,d) - 1` | Fractional difference in the same activity window; `L` is the raw LA window mean |
| `cbt_ultradian_amplitude_h0_12_relative_median` | `U[d] / B(U,d) - 1` | Fractional difference in first-half CBT ultradian amplitude; negative means suppression relative to this mouse's usual amplitude |
| `circadian_la_next_day_delta_relative_median` | `(A[d+1] - A[d]) / B(A,d)` | Next-day LA amplitude change as a fraction of typical circadian amplitude; no subtraction of 1 for an already differenced numerator |

For example, temperature 37.5 °C against a reference of 37.0 gives +0.5 °C; activity 30 against 20 gives +0.5 (50% above usual); ultradian amplitude 0.2 against 0.4 gives −0.5; a next-day amplitude fall of 4 against usual amplitude 20 gives −0.2. Kelvin/Celsius temperature ratios would depend on the temperature origin, so CBT uses a difference instead of a ratio.

Hours are elapsed recording-day hours; the CSV clock/light alignment remains unconfirmed. The window is minutes 360–719. Mean calculations require at least 288 observed minutes (80%) and do not interpolate, smooth, or clip. Full-recording wavelet features currently require finite recordings, as Matthew's existing helper does; this experiment does not introduce gap filling.

## Wavelet reuse and retrospective scope

The extractor recomputes wavelet summaries from the unchanged raw female recordings using Matthew's unchanged [Morse helper](../../Matthew%20Feature%20Engineering/wavelets.py), imported read-only. It does not consume or overwrite his feature export or diagnostic CSV. Transform conventions match his existing features: beta=5, gamma=3, peak response=2, periodic boundaries, linear detrending, maximum absolute amplitude over band periods per minute, then averaging over the relevant window.

`U` uses the same hours [0,12) and 1–3-hour periods. `A` averages the full day's 23–25-hour amplitude. All 14 recording days support the transform; only days 2–13 enter reference medians. The next-day LA comparison remains missing on day 13 to avoid using the final buffer's endpoint-sensitive amplitude. All 156 mouse-days remain exported.

These features require **retrospective complete-recording access**, including later days. Excluding the target's daily summary from the reference median does not remove its raw samples from full-recording wavelets. They do not support isolated-day or online prediction. Within-mouse unlabeled context is available by definition at inference; no recording context crosses mouse partitions. A different extraction design would be needed for prospective use.

## Missingness and leakage controls

Require at least nine finite summaries among the eleven possible reference days. Otherwise the affected reference/feature is NaN. Missing target summaries remain missing. Ratios with reference values at or below `1e-12` become NaN rather than infinity; this fixed numerical-zero guard is not tuned from data. The model handles exported missing values using its fitting-fold imputer. No population median or other mouse's measurements fill the reference.

The baseline is computed independently for each animal without labels. Validation/testing exclude whole mice, including their full-recording context. Population preprocessing, model selection, probability calibration, and F2 cutoff selection remain in the existing grouped modeling workflow. Earlier feature design, repeated dataset exploration, and previously inspected test mice still limit independent generalization claims. Same-animal unlabeled normalization is compatible with the declared retrospective task; it would be unavailable for a single-day prospective task.

## Generate, validate, and compare

From the repository root with the project environment installed:

```bash
python "Mouse Baseline Feature Engineering/features.py"
python run.py validate
estrus validate --owner "Mouse Baseline"
python run.py model --config config/mouse-baseline-f2.json --save-details
```

The [experiment configuration](../../config/mouse-baseline-f2.json) adds this family to the existing 28 contributor features, using the same seed, test mice, model grid, grouped folds, and F2 cutoff-selection protocol as [threshold tuning](../THRESHOLD_TUNING.md). It tries 32 available features; subset selection may omit some or all new columns. A cutoff is selected anew using development mice because probability estimates can change with a new feature set.

`feature_owners` explicitly lists the accepted family names. Missing or invalid explicitly requested exports stop a model experiment rather than silently removing an experimental family. The ordinary build and `config/threshold-f2.json` still consume the original families; the new folder's presence alone does not alter them. `--baseline` continues to select reference features alone. The build command `python run.py features --regenerate "Mouse Baseline" --config config/mouse-baseline-f2.json` explicitly regenerates only this new family's export.

The new folder's `outputs/features.csv` is the handoff. `outputs/feature_metadata.json` records definitions, source/input hashes, missingness, and feature-export hash. `outputs/baseline_inspection.csv` contains daily summaries, per-day reference medians/counts, and final relative values for inspection; it is not an input to modeling and is ignored by Git. Model building consumes CSV/JSON only and never executes the extractor implicitly. Requirements are carried into saved models and reports via the folder's `input_requirements.json`.

## Verification

Tests exercise exact leave-one-day-out medians/formulas, temperature-offset and signal-scale invariance, minimum reference coverage, undefined ratios, preservation of the day-13 exclusion, same-window aggregation, canonical export keys, per-mouse isolation, and opt-in feature selection. Extraction and model runs are separate checks. Software checks do not validate the biological proxy labels.
