# Results and final-model decision

## Retained final setup

The final choice, confirmed November 13, 2026, is the **original 28 features with development-only F2 decision-threshold tuning**, using [config/threshold-f2.json](../config/threshold-f2.json). Mouse Baseline and LA CBT Relationship features are excluded. Their source, exports, and results are retained below as research history.

The retained full run is `threshold-f2-2026-11-11`, recorded in the [versioned threshold result](results/threshold-f2-2026-11-11.json):

| Item | Recorded value |
| --- | --- |
| Available features | 28: Matthew 4, Alisha 18, Vivian 6 |
| Selected model | Logistic regression, C=1; top 35%, ten features |
| Development model-selection AP | 0.9917582417582418 (0.992 rounded) |
| Test AP | 0.9320987654320989 (0.932 rounded) |
| Development-selected cutoff | 0.36718281570864303 |
| Test cohort | 36 days from f3, f6, and f11; nine positive days |
| Accuracy | 34/36 = 94.4% |
| Estrus recall | 7/9 = 77.8% |
| Specificity / precision | 27/27 = 100% / 7/7 = 100% |
| Remaining false negatives | F3 day 10 and F11 day 10 |

Threshold tuning changed decisions while retaining the historical model's probabilities and AP. At cutoff 0.5, the same model detected 5/9 positives with no false alarms and 88.9% accuracy. The recorded cutoff was selected on development data and frozen before test prediction; it is not a hard-coded constant for future training runs. [The threshold guide](THRESHOLD_TUNING.md) explains the nested mouse-grouped procedure, F2 objective, and saved-model behavior.

To reproduce the final setup from retained inputs/exports:

```bash
python run.py all --config config/threshold-f2.json --save-details
```

Use `model` instead of `all` to skip data-preparation/feature-assembly build stages. Open the printed report and retain its run folder for sharing. The existing local run is ignored by Git; the linked JSON preserves its provenance without assuming that report folder exists in a fresh checkout. These scores describe the previously inspected, proxy-labeled cohort and are not independent biological validation.

## Historical presentation result: cutoff 0.5

The full build `presentation-2026-11-03` reproduced the following result using the retained input recordings and unchanged submitted feature CSVs:

| Item | Recorded value |
| --- | --- |
| Available features | 28: Matthew 4, Alisha 18, Vivian 6 |
| Chosen classifier | Logistic regression |
| Selected feature set | Top 35%; 10 features |
| Development-validation average precision | 0.992, rounded |
| Reserved-test average precision | 0.932, rounded |
| Test cohort | 36 days from 3 mice |
| Counts at probability threshold 0.5 | 5/9 estrus-proxy days detected; 27/27 other days correctly classified |

The run used `--save-details` and retained full configuration, source/input hashes, splits, feature assessments, and predictions locally. A small [presentation record](results/presentation-2026-11-03.json) is versioned here, including exact scores, selected features, software versions, and hashes for the report and predictions. The held-out mice were f3, f6, and f11. The working tree contained this repository cleanup; the record explicitly identifies that state.

The reproduced test AP is 0.9320987654320989 and matches the earlier local three-contributor result when rounded to 0.932. This is a software reproduction on the same dataset and split, rather than independent biological validation.

## Reproducing the historical fixed-cutoff setup

After installing the project, run:

```bash
python run.py all --config "Model Building/config.json" --save-details
```

Open the printed `Model Building/results/run-.../report.html` path. The default configuration is seed 190, three held-out mice, three development-validation folds, and 100 forest trees. The present submissions are the 28-feature combination above. Regenerating features or changing configuration may change the result; a reproduced score should be identified with that run's retained provenance.

For a reference-only comparison:

```bash
python run.py model --baseline --save-details
```

Compare baseline and team runs using the same labels, seed, configuration, and quick/full setting. Each run independently selects its winning model and feature subset. `--quick` is useful for checking the workflow and is a different experiment from a full run.

Generated reports are local outputs ignored by Git. Documentation intentionally does not link to local-only HTML files that disappear in a fresh checkout. Submit the chosen HTML report with its run folder as a course attachment or release artifact; the HTML embeds its images. No artifact has been published automatically. The [modeling guide](MODELING.md#output-files) explains the other files.

## Feature experiments excluded from the final model

### Later experiment: Mouse Baseline, November 11, 2026

The four [Mouse Baseline features](features/mouse-baseline.md) follow Matthew's existing windows and wavelet summaries, adding same-animal references through a separate opt-in export. The first full 32-feature/F2 experiment did **not** improve the previously accepted threshold-only result:

| Existing 36-day test cohort | Original 28 features + F2 cutoff | Add four Mouse Baseline features + F2 cutoff |
| --- | --- | --- |
| Average precision | 0.932 | 0.829 |
| Estrus detected | 7/9 | 5/9 |
| False alarms | 0/27 | 0/27 |
| Accuracy | 94.4% | 88.9% |
| Development-selected cutoff | 0.367183 | 0.607759 |

The new model selected all four relative features and seven original features (11 total). Development model-selection AP was 0.9933, versus 0.9918 previously, but test ranking deteriorated. Adding correlated features also changed the selected subset and coefficients; this experiment does not isolate which change caused the decline. F3 day 10 and F11 days 2, 6, and 10 were missed. These cases were not used to revise the four definitions or select another cutoff.

The accepted threshold-only run remains intact and uses the original feature families. Mouse Baseline was excluded from the final model; `config/mouse-baseline-f2.json` is retained only for reproducing that experiment. A [versioned result/provenance record](results/mouse-baseline-f2-2026-11-11.json) preserves exact metrics, configuration, new feature assessments, extraction metadata, and source/input/artifact hashes. The local ignored report is under `Model Building/results/mouse-baseline-f2-2026-11-11/`. This is an exploratory comparison on previously inspected mice, not a fresh independent validation.

### Later experiment: LA–CBT relationships, November 11, 2026

The [four paper-inspired relationship descriptors](features/la-cbt-relationship.md) were added to the original 28 features, excluding Mouse Baseline and retaining the F2 threshold-selection protocol. The result was mixed:

| Existing 36-day test cohort | Original features, tuned cutoff | Joint descriptors, cutoff 0.5 | Joint descriptors, tuned cutoff |
| --- | --- | --- | --- |
| Average precision | 0.932 | 0.951 | 0.951 |
| Estrus detected | 7/9 | 8/9 | 9/9 |
| False alarms | 0/27 | 4/27 | 7/27 |
| Accuracy | 94.4% | 86.1% | 80.6% |
| Precision | 100% | 66.7% | 56.3% |
| Specificity | 100% | 85.2% | 74.1% |
| F2 | 0.814 | 0.833 | 0.865 |
| Cutoff | 0.367183 | 0.5 | 0.195403 |

The new configuration selected logistic regression C=0.1 and 11 features: eight original features plus warming partial correlation, quiet cooling, and low-activity temperature excess. Hysteresis was not selected. Development model-selection AP was 0.9907407407407408; test AP was 0.9513888888888891. The exact F2 cutoff, 0.19540268867889038, was chosen using excluded-mouse development predictions and was not changed after inspecting test results.

This improved ranking and estrus sensitivity on the existing test cohort, with a substantial false-alarm cost. It did not improve overall accuracy; LA CBT Relationship was excluded from the final model. The accepted original-feature/F2 model remains intact and has the better observed accuracy/specificity. The joint-feature configuration is retained only for historical reproduction; no test-optimized cutoff or feature deletion was performed. Feature subset, coefficients, and regularization also changed, so this is a comparison of the complete configured workflows rather than an isolated causal effect of a specific descriptor.

The [versioned result/provenance record](results/la-cbt-relationship-f2-2026-11-11.json) preserves exact scores, false-alarm keys, feature assessments, frozen design/coverage notes, configuration, extraction metadata, and hashes. The local ignored report is `Model Building/results/la-cbt-relationship-f2-2026-11-11/report.html`. The paper and these results share the underlying study context; neither repeated evaluation nor the paper's sex-separation result constitutes fresh biological estrus validation.

## Interpretation and limitations

The default labels identify recording days 2, 6, and 10 as estrus based on assumed paper alignment. Independent biological staging and clock-time alignment remain unconfirmed. Current results describe recognition of that proxy pattern.

All three feature families in the retained final model use complete recordings, including later measurements. Results support retrospective classification and do not establish online prediction performance. Only three mice contribute to the test estimate. Development exploration and prior inspection of this dataset further limit claims of independent generalization.

Contributor-specific exploratory classifiers may use other preprocessing, splits, and metrics. Their scores should remain attributed to those analyses and should not be presented as interchangeable with the shared model's held-out result. Feature definitions and provenance are indexed in the [feature documentation](README.md#feature-documentation); full evaluation details are in [methods](METHODS.md).
