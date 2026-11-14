# LA–CBT relationship features

**Status:** excluded from the final model, as confirmed November 13, 2026. This page preserves the experiment's definitions and reproduction instructions. Use [config/threshold-f2.json](../../config/threshold-f2.json) for the retained final setup; see [the comparison](../RESULTS.md#feature-experiments-excluded-from-the-final-model).

This experiment adds four paired-signal descriptors in `LA CBT Relationship Feature Engineering/`. The comparison is **original 28 features + accepted F2 cutoff-selection protocol + these four features**. The rejected Mouse Baseline family is excluded. All new definitions were frozen before inspecting their supervised feature/model scores.

## Research basis and scope

Burks, J. H. and Smarr, B. L. (2026), *Dynamical model of aperiodic locomotor activity effects on mouse core body temperature removes transient perturbations from longitudinal temperature signals*, Scientific Reports 16:2164, DOI [10.1038/s41598-025-31953-8](https://doi.org/10.1038/s41598-025-31953-8), is the primary source. The supplied PDF is retained unchanged at the local ignored path `data/Important Data Files/estrus_detection_paper.pdf`. A fresh checkout may not contain it; use the DOI. Its hash is recorded by extraction when available. The [user-supplied ChatGPT summary](../references/la-cbt-user-provided-summary.md) is preserved as context, not treated as authoritative evidence or implementation instructions.

The paper motivates temperature-state-dependent activity responses, cooling during low activity, and temperature structure beyond activity alone (Figs. 2, 4, 5). It reanalyzes the 2017 study data, so it does not independently validate this capstone's classifier. Its perfect separation concerns males versus females in fitted parameter space, not held-out estrus-day classification. No numerical estrus-classification improvement follows from its significance tests.

The summary rewrites cooling with a positive-strength/minus-sign convention, whereas the article's recurrence uses a signed coefficient. Statements about a coefficient being lower should not be transferred between those conventions without checking the sign. This experiment extracts neither coefficient and makes no cooling-constant interpretation.

The requested implementation deliberately avoids recursive temperature simulation, nonlinear parameter optimization, inferred resting-temperature parameters, stage-specific fitting, borrowed fitted coefficients, and reproducing the paper's model. The following are proposed descriptive proxies. Their usefulness is an empirical question. Residual-like contrasts are not isolated hormones, and associations do not establish causation.

## Fixed preprocessing and notation

Use only the target day's 1,440 aligned LA/CBT minutes. Average into 288 nonoverlapping five-minute bins, retaining the time grid. Each signal needs four observed minutes per bin; otherwise that bin is NaN. Require at least 231 jointly observed bins (80% of the day). Reject infinity and negative LA. Do not clip, interpolate, compress gaps, or wrap at boundaries.

Let `A[t]` be five-minute mean LA in counts/minute and `T[t]` mean CBT in °C. Define `D[t] = T[t+2] - T[t]` and `E[t] = (A[t]+A[t+1])/2`, for `t=0..285`. CBT bin centers are ten minutes apart. The ten-minute horizon is motivated by the paper's reported typical activity/temperature lag and fixed here; no lag grid is selected using class labels. Means/changes are descriptors at this resolution, not exact reconstruction of minute-level thermodynamics.

## Four features and rationale

All names below have prefix `la_cbt_relationship__`.

| Feature | Calculation | Hypothesis / distinction from existing work |
| --- | --- | --- |
| `activity_warming_partial_corr_10min` | Correlate `E` with `D` after separately removing each variable's linear association with current `T`; include an intercept through centering | Association of activity exposure with subsequent warming after accounting for starting temperature; unlike Vivian's same-day LA–CBT level correlation |
| `quiet_cooling_weighted_change_10min` | Select intervals where both `A[t]` and `A[t+1]` are at/below the day's activity 25th percentile. Weighted mean of `D`, using weights `max(T[t] - day_CBT_q10, 0)` | Signed CBT change during low activity, emphasizing observations farther above a low-temperature reference; a descriptive response, not a fitted decay constant or Tmin |
| `low_activity_cbt_excess_h6_12` | Let recent activity be `(A[t-1]+A[t])/2`, `t=1..287`, and weights `1/(1+recent_activity)`. Weighted CBT mean in elapsed hours [6,12) minus the weighted CBT mean outside that window | Does elevated temperature persist in the existing window when attention is weighted toward lower recent activity? This is not a model residual or complete removal of activity heating |
| `activity_hysteresis_cbt_gap` | Classify bins by rising/falling activity relative to the preceding bin. Match broadly by current-day activity quartile; calculate mean `T_falling - T_rising` within eligible buckets, then average gaps weighted by the smaller direction count | Temperature memory at comparable current activity: falling activity may retain heat from prior activity. This specific descriptor is a new hypothesis, not a reported classifier feature in the paper |

For the correlation, require 36 complete pairs and nonzero residual variation. The linear projection is a within-day descriptive partial correlation, not a fitted dynamical system. If current CBT is constant, centering alone applies; constant residual signals yield NaN. The output lies in [−1,1].

The other three outputs have °C units. Cooling is °C change over a ten-minute interval, not °C per minute; negative values mean observed cooling. Require six positive-weight complete observations for each weighted mean. Hysteresis requires at least three rising and three falling observations in an activity bucket; ties/flat activity are excluded. Duplicate activity quantiles are collapsed, and buckets use right-side insertion (`searchsorted`, equality enters the higher bucket). Broad matching may leave activity-distribution or circadian confounding; it is not a controlled physiological experiment. Undefined descriptors remain NaN for the fitting-fold imputer.

The first bin has no preceding within-day activity value and is excluded from the recent-activity contrast/hysteresis. The final two bins cannot start a ten-minute change. No value from the preceding/following day is used. Overlapping intervals are correlated observations, not independent experimental replicates.

## Coverage-informed design, before supervised scoring

A label-free check on the ten development mice found that strict quiet/warmer-state filtering supplied at least six cooling pairs on only 12/120 days; a strict quiet-only hours-6–12 contrast had six bins on only 64/120 days. Before supervised scoring, the design used continuous temperature weighting for quiet cooling and inverse-activity weighting for the window contrast to reduce avoidable missingness. No class differences, validation scores, or test-mouse statistics were used to choose these rules. These coverage checks do not establish that the chosen descriptors discriminate estrus.

## Extraction and experiment

```bash
python "LA CBT Relationship Feature Engineering/features.py"
estrus validate --owner "LA CBT Relationship"
python run.py model --config config/la-cbt-relationship-f2.json --save-details
```

The [extractor](../../LA%20CBT%20Relationship%20Feature%20Engineering/features.py) writes its own canonical 156-row export, extraction metadata, and ignored coverage-inspection CSV. Model fitting reads only the CSV/JSON handoff. Its [configuration](../../config/la-cbt-relationship-f2.json) includes Matthew, Vivian, Alisha, and LA CBT Relationship, for 32 available features. It excludes Mouse Baseline. The original features, labels, reserved mice, full model grid, and nested F2 cutoff-selection procedure remain fixed; the new final model may select a different subset and receives a development-selected cutoff of its own.

The existing default/threshold-only experiments retain the original 28 features. New files do not automatically change the final model. The previous baseline-relative export is retained as a historical rejected experiment without including it in this run.

## Leakage and interpretation

All new calculations use one complete day from one mouse, never labels, other days/mice, predictions, or fitted population quantities. Binning, activity/temperature quantiles, matching, and partial correlations use that day's own paired measurements and are reproducible for an unseen complete day. Ten-minute forward changes require end-of-day retrospective access; they do not establish online prediction. The combined classifier still has the original contributors' complete-recording requirements.

Population preprocessing, supervised feature selection, model/hyperparameter choice, calibration, and threshold selection remain inside the mouse-grouped modeling workflow. No light-phase window is inferred from the paper: hours 6–12 refer to recording-day elapsed time until row-zero clock alignment is confirmed. The paper uses the same underlying source study and the project test mice were previously inspected, so any resulting gain is exploratory. Do not redesign features against the displayed test errors and describe another run as independent validation.

Tests check exact weighting/change units, partial correlation under known confounding, matched rising/falling comparisons, degenerate states/missingness, time-grid preservation, and independence from labels and other mouse-days. An observed association or model improvement would not independently establish biological staging or a causal thermal mechanism.
