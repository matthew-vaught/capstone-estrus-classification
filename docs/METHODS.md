# Methods

## Data and labels

The female CSVs contain 20,160 one-minute readings for each of 13 mice, with temperature in °C and activity in counts/minute. Recording days 2–13 provide 156 mouse-days. Days 1 and 14 are buffers. Male files are unused by the shared classifier; Alisha's separate exploratory analysis uses them as a control.

Recording days 2, 6, and 10 are provisionally positive, based on the team's assumed alignment with the supplied Smarr et al. paper. This gives 39 estrus and 117 non-estrus days. The paper identified estrus using temperature profiles; these are not independent biological staging labels. Results currently measure recognition of that paper-aligned pattern. Confirm alignment with the professor, or use `--labels` with independently curated labels. Blank targets are excluded.

## Final configuration and model selection

The retained final recipe is [config/threshold-f2.json](../config/threshold-f2.json): the original 28 features plus F2 threshold tuning. It excludes Mouse Baseline and LA CBT Relationship features. The historical `Model Building/config.json`, selected when `--config` is omitted, retains cutoff 0.5.

The [threshold guide](THRESHOLD_TUNING.md#how-the-cutoff-is-selected) specifies the nested folds and tie rule used in step 2. Development threshold-selection scores are not independent evaluation scores. The historical fixed-cutoff configuration skips that step.

1. **Reserve 3 mice for testing.** The split depends only on mouse IDs and seed 190, before model or feature selection. All days from a mouse stay together. The remaining 10 mice are the training/development set.
2. **Select the cutoff on development mice only.** In the final recipe, generate probabilities with each scored mouse excluded from model selection, preprocessing, fitting, and calibration. Choose a cutoff by F2 and freeze it before test prediction. The three test mice remain excluded throughout.
3. **Compare three models and three feature sets on all development mice.** Test logistic regression, random forest, and an RBF support vector machine using all usable features, the top 35%, or the top 70%. Constant features are removed. Reduced sets rank features by an ANOVA F score, which measures differences between classes relative to within-class variability.
4. **Choose the combination with the highest validation average precision.** Three training-only validation splits keep mice together. Median imputation, scaling, and feature ranking are fitted separately on the fitting mice in each split. Logistic regression and SVM try C values 0.1, 1, and 10. Random forest tries maximum depth 3 and unlimited, with 100 trees and minimum leaf size 3. Quick mode uses two validation splits, 40 trees, and C=1.
5. **Fit one final classifier on the training mice.** Sigmoid probability calibration uses predictions from grouped training-validation splits (`CalibratedClassifierCV`, `ensemble=False`). The final classifier's feature selection is fitted once on all training mice. It has one exact feature list, shown in the report.
6. **Evaluate that model on the 3 reserved mice.** Apply the frozen development-selected cutoff in the final recipe, or 0.5 in the historical configuration. Test labels do not affect feature selection, model choice, calibration, feature rankings, cutoff choice, or the saved classifier. The report and saved model use exactly the same fitted classifier and probabilities. Test mice are not subsequently added to training.

The model-comparison table shows the best validation result for each model family and marks the winning combination. Expanding the feature-selection trials shows the best result for each model/feature-set combination. The headline AP is the chosen model's separate test result, so it can differ from its selection score. There is no combined row made from changing model choices across evaluation rounds.

`Model Building/config.json` controls `test_mice`, `cv_folds`, `trees`, `seed`, `jobs`, feature-selection percentages, regularization grids, forest settings, and permutation repeats. The values above describe its defaults; alternate files can be supplied with `--config`. Custom labels must leave both classes in the training, validation, and test partitions. Fewer labeled mice may require reducing the configured counts.

## Feature assessment is the focus

Every input feature appears in the report, grouped under Matthew, Vivian, Brandon, Alisha, or Reference features. Names come from the CSV namespace. Valid contributor exports are combined **without reference features**. With no valid exports, the workflow reports a fallback to the reference baseline. `--baseline` explicitly ignores all contributor exports and runs the reference features alone. Missing or invalid exports do not trigger the switch to contributor-only features.

For baseline-versus-team comparisons, use the same labels, seed, configuration, and quick/full setting. Mouse membership and validation partitions depend on those inputs, not the feature columns. Each run selects the best model/subset for its own available features. Feature engineering is not guaranteed to improve the test score; the comparison measures whether it does. Reduced feature sets retain at least one usable feature, so an export with only one or a few features still works.

Each feature has three useful indicators:

- **AP on its own:** mean training-validation AP from a small logistic regression using only that feature. This is a simple screening score, not a complete test of nonlinear usefulness. A constant score gets AP equal to the positive fraction, 0.25 with the current labels.
- **Contribution (AP drop):** refit the chosen pipeline on each training-validation split, shuffle one feature in that split's validation data three times, and measure how much AP falls. Average the drops. Larger positive values suggest more useful information; zero or negative values do not prove a feature is useless, especially when features share information.
- **Used in final model:** exact membership in the final classifier's fitted feature selection. The saved model's list matches the report and `final_model.json`. Importance is a descriptive validation result; it does not remove additional features after model choice.

Both feature assessments use training/development mice only. The single-feature screening model and contribution calculation are separate from the ANOVA ranking used by the selection candidates. Their rankings need not agree. Selection may also vary between validation splits, while the saved classifier has one final feature list.

These assessments help the team develop features. They are not causal effects, significance tests, or independent proof of usefulness. Adding correlated features can change importance without materially changing predictions.

## Feature input scope

Reference features and the default contributor rule use only the target day's complete 1,440 readings. Do not use mouse identity, recording-day number, cycle position, or labels as features. Adjacent-day inputs and full-recording transforms require an explicit retrospective definition. Current submissions from Matthew, Alisha, and Vivian all include complete-recording context, documented below and in their feature guides. Population transforms belong inside the shared model pipeline. Export validation catches naming and formatting mistakes, but code review is still needed to catch semantic leakage.

The reference features describe temperature/activity location, spread, plateau length, roughness, first/second-half differences, daily harmonic shape, 1–3-hour Morlet power, missingness, and temperature–activity correlation. Signals with fewer than 720 observed minutes produce missing signal features. Other gaps use within-day interpolation with a ten-minute limit, then that day's median. Original values are not clipped using population statistics.

Wavelet features use five-minute averages, `cmor1.5-1.0`, and 13 periods between 60 and 180 minutes. Three hours at each edge are excluded to reduce boundary effects. This is a day-local approximation inspired by the paper, not its full-recording Morse analysis. A single day's 24-hour harmonic describes shape rather than establishing a stable circadian rhythm. Clock time at CSV row zero is unknown; first/second half is not assumed to mean light/dark.

## Matthew's retrospective recording features

This contribution uses recording-level context beyond a single day. It exports exactly four features: next-day minus current-day circadian LA amplitude (23–25-hour band), first-half CBT ultradian amplitude (1–3-hour band, hours 0–12), and the fractions of hours 6–12 above 37.2 °C CBT and 15 counts/minute LA. Hours are elapsed recording-day hours, with clock/light alignment unconfirmed.

The wavelets use each mouse's complete 14-day recording: analytic generalized Morse, beta=5, gamma=3, peak response=2, linear detrending, periodic FFT boundary, band maximum of absolute coefficients at each minute followed by window averaging. These are amplitudes, not squared power. Day 13's LA delta is NaN for each mouse because its next-day amplitude would come from the endpoint-sensitive final buffer. The other three features remain present and all 156 canonical target rows are retained: 143 observed LA deltas, 13 missing. The model uses fitting-fold median imputation, fitted on final training mice for the saved model; it does not recover the unavailable change or use test values to fill it. Day 14's raw readings still support the wavelet, and residual boundary effects remain. No missing samples are silently filled for these transforms. Exact definitions, grids, units, and reproducibility artifacts are in [Matthew's README](features/matthew.md).

These features support retrospective classification when the entire recording is available, not online or end-of-day inference. Full-recording detrending and the centered wavelet use samples beyond the explicit next-day comparison. Mouse-grouped evaluation keeps overlapping context from crossing training/test partitions. This does not establish prospective performance.

The two fixed thresholds came from supervised exploration on development mice and are not reselected within each model fold. Subsequent development-validation results therefore include feature-design selection and are exploratory. They were selected without the reserved test mice; avoid further design changes in response to the new test score. The notebook's nested single-feature check favored ordinary window means slightly over the tuned fractions; the exported fractions implement the requested experiment.

## Other recording-level contributions

[Alisha's eighteen DTW features](features/alisha.md) compare each target day with the same mouse's other thirteen recording days, including future days and both buffers. [Vivian's six features](features/vivian.md) use per-mouse complete-recording cleaning, activity regression, and adjusted-temperature wavelets. Both require retrospective recording access. Their shared exports contain no label columns and no quantities learned across mice. The shared model retains mouse-grouped partitions for all three contributor families.

Vivian's separate exploratory classifier uses per-mouse centering; her shared exported features are uncentered and use training-fold preprocessing in the shared pipeline. Alisha's exploratory analysis uses other evaluation and statistical procedures described in her feature document. Those scores should not be substituted for the shared held-out result.

## Experimental feature families excluded from the final model

The [Mouse Baseline experiment](features/mouse-baseline.md) added four label-free, same-animal contrasts from Matthew's existing hours-6–12 window means, first-half CBT ultradian amplitude, and next-day circadian LA amplitude change. Each reference is the median of the other eleven analysis-day summaries, requiring nine finite values. Temperature uses a difference in °C; activity/amplitude features use dimensionless relative scaling. Buffers are excluded from medians but support the unchanged full-recording wavelet; the day-13 next-day comparison remains missing. These are retrospective typical-recording references, not labeled non-estrus baselines.

The [LA CBT Relationship experiment](features/la-cbt-relationship.md) added four day-local paired-signal descriptors inspired by Burks and Smarr (2026). It improved observed AP/recall but increased false alarms. Both families were excluded from the retained final model; their explicit `feature_owners` configurations exist for historical research reproduction only. See [the recorded comparisons](RESULTS.md#feature-experiments-excluded-from-the-final-model). Original feature exports and labels remain unchanged.

## Scores and confidence

**Average precision (AP)** is used consistently for comparison, selection, feature screening, and final testing. It evaluates how well estrus days rank near the top of predicted probabilities. Higher is better and 1 is perfect. It is not accuracy. AP can penalize highly ranked false positives, but changing probability magnitudes without changing rank can leave AP unchanged.

At the run's saved decision threshold (development-selected for the final recipe; 0.5 for the historical default), the report also gives plain counts of correctly classified estrus and non-estrus days. Confidence is the probability assigned to the predicted class: `p_estrus` for Estrus and `1-p_estrus` for Non-estrus. At cutoff 0.5 this equals `max(p_estrus, 1-p_estrus)`; a tuned cutoff can select a class with probability below 0.5. Calibration attempts to make probabilities meaningful, but cannot guarantee this with so few mice and provisional labels. Additional metrics, including accuracy, sensitivity, specificity, F2, confusion counts, log loss, and Brier score, are retained with `--save-details`.

The spreadsheet uses `mouse_id`, `day_index`, `actual_class`, `predicted_class`, `estrus_probability`, and `confidence`. Probabilities are on a 0–1 scale. All plotted examples come from the reserved test mice.

## Cycle-day reference overlays

Each example shows LA on the left and CBT on the right in compact panels. The black overlay follows the two-step averaging described in the supplied paper's Data analysis section (page 2): first average the three repeated cycles within each female, then average across females, giving each mouse equal weight. It uses all 13 females, including the displayed test animals. Missing minute values are omitted at each averaging step. This is a descriptive population reference for the plots, not an input to features, model fitting, calibration, selection, or evaluation.

Cycle day is `(recording_day - 2) % 4 + 1`: recording days 2/6/10 match cycle day 1, 3/7/11 match day 2, 4/8/12 match day 3, and 5/9/13 match day 4. Buffers 1 and 14 are excluded. This uses the same provisional alignment as the labels, not a cycle day inferred from the model prediction. Legends identify the individual and female reference. Both main traces use centered 15-minute moving averages for display; faint individual traces retain the original minute readings.

The overlay uses the supplied CSV measurements without reproducing the paper's additional outlier clipping. It is therefore a paper-inspired reference, not an exact reproduction of Figure 1. Axes show elapsed hours because the CSV start clock time is unknown; no light/dark schedule is inferred. Changing these visualizations does not change the saved predictions or model.

## Limits and reproducibility

Three test mice give a small, variable estimate. The team has already explored this dataset and previous results, so this is exploratory evaluation, not a new independent biological validation. Repeatedly changing features in response to the displayed test score further limits its independence. Use training-validation feature assessments to guide development; validate future claims on additional animals.

The report, readable predictions, saved model, and short README are the four default output files. `--save-details` adds input/source hashes, exact software versions, configuration, the feature matrix, labels, mouse splits, model comparisons, feature assessments, full predictions, and day PNGs in `details/`. Intermediate files are built in a temporary workspace and removed afterward. The run README is written last.

The saved model stores its original input schema, exact selected feature list, train/test mice, label sources, and configuration. Seed 190 controls the split, model randomness, and feature-importance shuffles. Exact development dependency versions are in `requirements-lock.txt`. Original inputs and committed contributor exports remain authoritative.
