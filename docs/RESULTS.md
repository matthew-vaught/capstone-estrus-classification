# Results and final-model decision

## Final setup

The final choice, adopted November 15, 2026, is **mouse-relative features with a fixed-model, leave-one-mouse-out F2 cutoff**, using [config/mouse-relative-fixed-cutoff.json](../config/mouse-relative-fixed-cutoff.json):

- **Features:** the original 28 plus a copy of each, rescaled against the same mouse's median and IQR.
- **Cutoff selection:** the model is chosen once on development mice and refit while scoring each development mouse in turn; F2 picks the cutoff.
- **Calibration:** none.

Mouse Baseline and LA CBT Relationship features remain excluded. The experiment that led here and the earlier final setup are retained below. The [research note](research/mouse-relative-2026-11-15.md) gives the rationale and caveats.

The final full build is `final-2026-11-15`, recorded in the [versioned final result](results/final-2026-11-15.json):

| Item | Recorded value |
| --- | --- |
| Available features | 56: Matthew 4, Alisha 18, Vivian 6, plus a mouse-relative copy of each |
| Selected model | Logistic regression, C=1; top 35%, 20 features (10 original, 10 mouse-relative) |
| Calibration | None |
| Development model-selection AP | 0.9955484330484333 (0.996 rounded) |
| Test AP | 0.9797979797979799 (0.980 rounded) |
| Development-selected cutoff | 0.5057318949923271 |
| Test cohort | 36 days from f3, f6, and f11; nine positive days |
| Accuracy | **35/36 = 97.2%** |
| Estrus recall | 8/9 = 88.9% |
| Specificity / precision | 27/27 = 100% / 8/8 = 100% |
| Remaining false negative | F3 day 10 |

**All 13 mice, full pipeline:** the full pipeline was also run 13 times, holding out each mouse in turn ([script](research/all_mice_pipeline_2026-11-15.py)). This setup scored 148/156 correct (94.9%; 37/39 estrus days caught, 6 false alarms). The previous setup scored 145/156 (92.9%). It was never worse on any individual mouse.

The cutoff was selected on development data and frozen before test prediction; it is not a hard-coded constant. At 0.5 the same model gives identical decisions. The gains over the previous setup are small, about one test day and three days of 156. The configuration was developed over several rounds on this dataset, so new animals remain the real test.

To reproduce the final setup from retained inputs/exports:

```bash
python run.py all --config config/mouse-relative-fixed-cutoff.json --save-details
```

Use `model` instead of `all` to skip data-preparation/feature-assembly build stages. Open the printed report and retain its run folder for sharing. The local run folder `Model Building/results/final-2026-11-15/` (including `report.html`) is ignored by Git; the linked JSON preserves its provenance and artifact hashes. These scores describe the previously inspected, proxy-labeled cohort and are not independent biological validation.

## Previous final setup: original features with F2 cutoff, November 13, 2026

From November 13 to 15, 2026, the final choice was the **original 28 features with development-only F2 decision-threshold tuning**, using [config/threshold-f2.json](../config/threshold-f2.json). Its full run is `threshold-f2-2026-11-11`, recorded in the [versioned threshold result](results/threshold-f2-2026-11-11.json):

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

Threshold tuning changed decisions while retaining the historical model's probabilities and AP. At cutoff 0.5, the same model detected 5/9 positives with no false alarms and 88.9% accuracy. [The threshold guide](THRESHOLD_TUNING.md) explains the nested mouse-grouped procedure, F2 objective, and saved-model behavior. A November 15 rerun reproduced this result exactly; reproduce it with `python run.py all --config config/threshold-f2.json --save-details`.

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

## Feature and cutoff experiments

The Mouse Baseline and LA–CBT Relationship experiments were excluded. The November 15 mouse-relative experiment produced the current [final setup](#final-setup). In this section, "final" means the final setup at the time of each experiment.

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

### Later experiment: mouse-relative features and accuracy cutoff, November 15, 2026

This experiment tested two changes aimed at accuracy:

- **Mouse-relative copies of all 28 features:** each value rescaled against the same mouse's median and IQR, keeping the originals.
- **Choosing the cutoff by plain accuracy** instead of F2.

Both were crossed in a full 2×2 on the standard split. The [research note](research/mouse-relative-2026-11-15.md) gives the rationale, a leave-one-mouse-out screen over all 13 mice, and the interpretation.

| Existing 36-day test cohort | Original 28 + F2 (then final) | Original 28 + accuracy | Mouse-relative + F2 | Mouse-relative + accuracy |
| --- | --- | --- | --- | --- |
| Average precision | 0.932 | 0.932 | 0.980 | 0.980 |
| Estrus detected | 7/9 | 5/9 | 9/9 | 3/9 |
| False alarms | 0/27 | 0/27 | 4/27 | 0/27 |
| Accuracy | **94.4%** | 88.9% | 88.9% | 83.3% |
| Development-selected cutoff | 0.367 | 0.688 | 0.072 | 0.841 |

Mouse-relative features clearly improved ranking: AP rose from 0.932 to 0.980, and all nine estrus days were caught under F2. The development-selected cutoffs did not transfer to the test mice, though, and no arm beat the then-final setup's accuracy. The plain-accuracy objective hurt both feature sets: with about 30 development estrus days, it moved the cutoff to gain one development day. In the earlier leave-one-mouse-out screen, mouse-relative features did raise accuracy at 0.5, from 148/156 to 151/156, so the evidence is mixed rather than negative.

A same-day follow-up targeted the cutoff transfer. Rescaling predicted scores within each mouse lowered accuracy and was not pursued further. Choosing the cutoff with leave-one-mouse-out development folds and no calibration did better:

- **All 13 mice, nested, with a fixed logistic model:** mouse-relative features reached 152/156 (97.4%), versus 148/156 (94.9%) for the original features.
- **Full pipeline on the 36 test days:** mouse-relative features with this protocol caught 8/9 estrus days with 1 false alarm. That is 94.4% accuracy, a **tie** with the then-final setup. The original features with the same protocol gave 91.7%.

The full pipeline did not match the fixed-model result because its per-fold model search mixed logistic regression, random forest, and SVM probability scales when choosing the cutoff.

**A follow-up fixed that, and it improved accuracy.** With `"model_search": "fixed"`, the pipeline chooses the model once and refits that same model in every cutoff fold. It was evaluated twice: on the standard split, and by running the full pipeline 13 times, once per held-out mouse.

| Evaluation | Previous final ([threshold-f2](../config/threshold-f2.json)) | Mouse-relative + fixed-model cutoff ([mouse-relative-fixed-cutoff](../config/mouse-relative-fixed-cutoff.json)) |
| --- | --- | --- |
| All 13 mice, 156 days | 145 correct (92.9%); 33/39 caught, 5 false alarms | **148 correct (94.9%)**; 37/39 caught, 6 false alarms |
| Standard split, 36 days | 34 correct (94.4%); 7/9 caught, 0 false alarms | **35 correct (97.2%)**; 8/9 caught, 0 false alarms |

- **The fix was never worse on any individual mouse.** It was better on f1, f12, and f13.
- **Both parts are needed.** The same cutoff method without mouse-relative features tied the previous final model on all 13 mice: 145/156 with 9 false alarms.
- **The gains are small,** about three days of 156. The configuration was developed over several rounds on this dataset.
- **The model's only standard-split error is f3 day 10.**

**Status:** adopted as the [final setup](#final-setup) on November 15, 2026. The other arms were excluded. All arms are reproducible with the configs under `config/`; see the [config index](../config/README.md). The [research note](research/mouse-relative-2026-11-15.md#step-4-one-fixed-model-while-choosing-the-cutoff) has the per-mouse errors, caveats, and evaluation scripts. The first column reran `config/threshold-f2.json` on the same machine and matched its recorded result exactly. Exact scores, selected features, errors, and hashes are in the [versioned record](results/mouse-relative-2026-11-15.json). Local ignored reports are under `Model Building/results/*-2026-11-15/`. This is another exploratory comparison on previously inspected test mice.

## Interpretation and limitations

The default labels identify recording days 2, 6, and 10 as estrus based on assumed paper alignment. Independent biological staging and clock-time alignment remain unconfirmed. Current results describe recognition of that proxy pattern.

All three feature families in the final model use complete recordings, including later measurements, and the mouse-relative copies also use each mouse's other days. Results support retrospective classification and do not establish online prediction performance. Only three mice contribute to the test estimate. Development exploration and prior inspection of this dataset further limit claims of independent generalization.

Contributor-specific exploratory classifiers may use other preprocessing, splits, and metrics. Their scores should remain attributed to those analyses and should not be presented as interchangeable with the shared model's held-out result. Feature definitions and provenance are indexed in the [feature documentation](README.md#feature-documentation); full evaluation details are in [methods](METHODS.md).
