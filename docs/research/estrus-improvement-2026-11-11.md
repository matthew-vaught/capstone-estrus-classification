# Research plan for improving estrus-day classification

Prepared November 11, 2026. This is a research assessment of the existing model, not a new training experiment. The user confirmed that labels follow an assumed four-day cycle and explicitly requested that all labels remain unchanged. Possible label error is an interpretation limit, not an established finding about F3 day 10.

## Assessment of the current result

AP 0.932 is a promising ranking result for this small retrospective dataset. It does not mean 93.2% accuracy or establish biological estrus detection. The [versioned presentation record](../results/presentation-2026-11-03.json) identifies logistic regression, C=1, and 10 selected features from 28 available features: all four Matthew features, Vivian's adjusted-temperature range, and five Alisha DTW shifts. Selection used ten development mice; testing used f3, f6, and f11.

The following calculations were independently recomputed from the retained local `Model Building/results/presentation-2026-11-03/predictions.csv`, without fitting a model:

| Quantity | Observed result |
| --- | --- |
| Development model-selection AP | 0.9917582417582418 |
| Pooled test AP | 0.9320987654320989 |
| Test sample | 36 days, 3 mice, 9 positive days |
| True positives / false negatives at 0.5 | 5 / 4 |
| True negatives / false positives at 0.5 | 27 / 0 |
| Accuracy | 88.9% |
| Estrus recall / sensitivity | 55.6% |
| Specificity | 100% |
| Positive predictive value / precision | 100% |
| Balanced accuracy | 77.8% |

Always predicting non-estrus would achieve 75% accuracy here. AP measures ordering across thresholds, whereas accuracy and sensitivity describe decisions at a particular threshold; see the [scikit-learn precision–recall explanation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html). Strong ranking and weak sensitivity at 0.5 can coexist.

The validation AP is the best score selected during development, not an independent estimate. Matthew's threshold design and Alisha's feature design also used development labels. The gap to test AP could reflect selection optimism, differences between mice, and sampling variability; these observations do not identify a single cause. [Nested cross-validation documentation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) explains why evaluating a chosen configuration on its selection folds is optimistic.

## What the four errors reveal

| Mouse | Recording day | Assigned positive label | Saved estrus probability |
| --- | --- | --- | --- |
| f3 | 2 | Estrus | 0.447047 |
| f3 | 10 | Estrus | 0.053157 |
| f11 | 6 | Estrus | 0.435347 |
| f11 | 10 | Estrus | 0.337535 |

Two misses are close to the current cutoff. F3 day 10 is a much stronger disagreement. These cases should not automatically receive the same explanation or remedy.

The model already uses `class_weight="balanced"` for logistic regression, random forest, and SVM in [modeling.py](../../src/estrus/modeling.py). Adding balanced weights is therefore not a new intervention. All four mistakes being false negatives shows conservative decisions at this operating point; it does not by itself prove that fitting ignored the positive class.

An important additional diagnostic is AP calculated separately within each mouse: **f3 = 1.000, f6 = 1.000, f11 = 0.9167**. Every assigned positive day in f3 ranks above every assigned negative day in f3, including day 10. Its score is nevertheless lower than several negative days in f11. This supports investigating between-mouse baseline differences and score comparability. It does not prove a calibration defect or establish that separate mouse-specific thresholds will generalize. In particular, do not tune thresholds using a new mouse's true labels.

### Threshold illustrations, not validated improvements

These rows apply alternative cutoffs to the same already-inspected test predictions. They are descriptive error analysis and must not be reported as newly validated operating points.

| Cutoff | Estrus detected | False alarms | Accuracy | Recall | Precision |
| --- | --- | --- | --- | --- | --- |
| 0.50 | 5/9 | 0/27 | 88.9% | 55.6% | 100% |
| 0.40 | 7/9 | 0/27 | 94.4% | 77.8% | 100% |
| 0.33 | 8/9 | 1/27 | 94.4% | 88.9% | 88.9% |
| 0.05 | 9/9 | 9/27 | 75.0% | 100% | 50.0% |

A lower cutoff can improve sensitivity without changing any feature or AP. It cannot deliver perfect classification for these fixed scores: for example, the negative f11 day 5 scores 0.357683, above the positive f11 day 10 at 0.337535. Catching every assigned positive with a common threshold necessarily admits some negatives.

The first experiment should select a cutoff using predictions for development mice that were excluded from fitting each corresponding model. Calibration, feature selection, and model tuning must also exclude those validation mice. For an honest evaluation of the entire selection procedure, put threshold choice inside an outer mouse-grouped evaluation. Scikit-learn documents [decision-threshold tuning and its overfitting risks](https://scikit-learn.org/stable/modules/classification_threshold.html); its default stratified folds must be replaced with mouse-disjoint folds for this dataset.

## Labels, biology, and the 100% objective

The user confirmed that the classroom labels assume a repeating four-day cycle. The original [Smarr et al. (2017) methods](https://link.springer.com/article/10.1186/s13293-016-0125-3) aligned female analysis windows using prolonged peak-temperature profiles; they do not establish independent cytological staging of these classroom CSV rows. Temperature features can consequently learn the phenotype used to define a proxy label. This is relevant to interpretation even when mouse partitions are correctly separated.

A [mouse staging protocol by Pantier et al. (2019)](https://bio-protocol.org/en/bpdetail?id=3354&type=0) describes progression across four to five days on average, with stage durations that vary. That makes the user's concern biologically plausible. It does not demonstrate that f3 day 10 is mislabeled, that any particular other day is estrus, or that perfect agreement with this dataset is impossible.

Keep original labels and all days in the primary analysis. Record F3 day 10 as an unresolved disagreement. If independent staging records ever become available, they could support a separately versioned validation exercise. Visual judgments from the same temperature/activity signals would be additional phenotype interpretation, not independent biological ground truth. Never relabel a difficult case merely to improve the score.

Perfect agreement on 36 inspected days is different from reliable generalization to new mice. Only nine positive test days inform sensitivity, and days within an animal are correlated. A 100% observed score would still have substantial uncertainty. Conversely, possible label noise is not a reason to stop improving the model; it is a reason to distinguish agreement with assigned labels from biological validity.

## Feature hypotheses, in priority order

These are proposed experiments, not demonstrated missing biomarkers. Start with a few predeclared features per family and compare each addition against the unchanged baseline on identical development partitions.

### 1. Mouse-relative temperature and activity

**Hypothesis:** fixed absolute thresholds and globally scaled features retain nuisance differences in individual temperature/activity levels.

Compare absolute features with label-free within-mouse contrasts: window temperature minus that mouse's median temperature, activity relative to its own typical profile, and plateau height/duration relative to the mouse's other days. A retrospective robust transform could use `(feature - mouse median) / mouse IQR`, with a defined fallback for zero IQR. Test absolute plus relative features as well as relative-only features; centering can remove useful information too.

This is motivated by the observed difference between within-mouse and pooled ranking. Vivian's separate exploratory classifier already uses per-mouse centering, but the shared export is uncentered; see [her feature documentation](../features/vivian.md). Its previous AUC is not a controlled estimate of the effect of centering because evaluation and other choices differ.

Using the new animal's unlabeled complete recording is consistent with the current retrospective task if specified in advance and reproduced during validation. It would require a different definition for prospective prediction. Do not use the animal's true positive days to build its baseline.

### 2. Sustained plateau duration and temperature decline

**Hypothesis:** existing features describe elevation and temporal alignment but incompletely measure how long the high-temperature state persists and when it ends. The source paper emphasizes a prolonged high-temperature/activity plateau and delayed CBT decline, motivating these proposed measurements rather than proving their predictive benefit. [Smarr et al., 2017](https://link.springer.com/article/10.1186/s13293-016-0125-3).

Candidates include the longest sustained elevated-temperature interval, its end time, sustained negative-slope onset after the peak, and area above a robust mouse-relative baseline. Distinguish one continuous plateau from several disconnected spikes: a fraction-above-threshold alone cannot do that. Define smoothing, gap tolerance, minimum duration, search interval, absent-decline handling, and boundary behavior before evaluation. Express hours relative to the recording until row-zero light/clock alignment is confirmed.

There are useful existing starting points. The [reference extractor](../../src/estrus/features.py) already computes plateau duration, window contrasts, and harmonic features, but the contributor-only model excludes reference features. A controlled shared experiment could add a small predeclared subset without modifying any contributor's export. This combination is not currently an implemented CLI experiment. Also, Vivian's `adj_decline_hour` is the first hour below that day's median, which can precede the peak; it is not a specific post-peak decline detector.

### 3. Within-mouse changes across adjacent days

**Hypothesis:** an unusual daily shape becomes clearer relative to the same animal's surrounding days.

Add previous-day change in plateau duration, temperature decline timing, or a robust temperature summary. For the retrospective task, compare the target with a label-free surrounding-day baseline as a separate variant. Matthew already supplies a next-day activity-amplitude difference; simply duplicating that information is unlikely to be the best use of extra columns. Record buffer/edge requirements explicitly. Never use recording-day modulo four, assigned cycle position, or true neighboring labels as inputs: that would reproduce the assumed answer by construction.

### 4. Joint shape and time-localized rhythm features

**Hypothesis:** the relationship among sustained heat, activity timing, and ultradian suppression is more informative than their separate daily averages.

Test a small number of interactions such as relative plateau duration × relative activity duration, temperature-decline time minus activity-offset time, and early-versus-late ultradian amplitude contrast. Existing Vivian correlation and activity-adjusted CBT features already address some temperature–activity coupling; a generic correlation is not a missing feature. Global LA regression may remove shared cycle-related information, so compare raw, adjusted, and joint representations rather than assuming residualization is always beneficial.

Alisha's DTW features already capture temporal shape shifts. Additional alignment features should answer a distinct question, such as constrained shift or warp amount, rather than repeat the same segment shifts. Compare a small constrained variant only after the higher-priority experiments.

## Models worth testing

Logistic regression currently beats the tested random forest and RBF SVM by development AP: approximately 0.992 versus 0.975 and 0.971 at their best tried settings. This is evidence for keeping logistic regression as the reference, not proof that all nonlinear models are worse.

1. **Regularized logistic regression with a few explicit interactions or splines.** This tests specific nonlinear relationships while retaining interpretability. Compare the selection step as well: the current ANOVA filter scores one feature at a time, so weak marginal predictors with useful joint effects may be discarded. The existing search already includes all features, but new interaction sets still need an appropriate comparison. [SelectPercentile documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectPercentile.html).
2. **Shallow gradient-boosted trees.** Use a small search with shallow trees, shrinkage, and conservative leaf sizes. This is a targeted comparison for nonlinearities, not an expectation of 100%. Scikit-learn describes [gradient boosting and its small-sample implementation choices](https://scikit-learn.org/stable/modules/ensemble.html#gradient-boosted-trees).
3. **A sequence model as a later research extension.** An HMM or duration-aware alternative could combine daily physiological evidence with a soft temporal prior, allowing cycle lengths to vary. Binary labels alone do not supervise all four biological stages, and 13 short recordings provide little information for learning transitions. EstrousNet provides precedent for using temporal context, but it classifies cytology images and its accuracy is not a benchmark for this task. [Wolcott et al., 2022](https://www.nature.com/articles/s41598-022-22392-w).

Deep neural networks are a low priority with 156 correlated day examples from 13 mice. Thousands of minute measurements do not create thousands of independently labeled animals. Generic oversampling or SMOTE is also a lower priority than cutoff selection and relative features; synthetic rows cannot replace independent mice. Any resampling would belong entirely inside fitting folds.

## Evaluation and experiment order

Agree on the objective before selecting a winner. Keep AP as a ranking measure and report accuracy, sensitivity, specificity, precision, F2, and confusion counts at the chosen cutoff. If missed estrus is the main concern, a possible objective is sensitivity subject to a predeclared specificity requirement, or F2, which emphasizes recall. A target such as 90–95% sensitivity is an aspiration, not a stable estimate from nine positives. Also retain Brier/log loss to assess confidently wrong probabilities; the existing detailed results already calculate them.

| Order | Experiment | Main question |
| --- | --- | --- |
| 1 | Development-only threshold selection with current features/model | How much of low sensitivity is an operating-point issue? |
| 2 | Add mouse-relative features | Do individual baselines explain score differences? |
| 3 | Add plateau duration and true decline features | Does explicit shape capture improve discrimination? |
| 4 | Add a few adjacent-day contrasts / interactions | Do temporal changes or joint relationships add information? |
| 5 | Compare regularized nonlinear variants and shallow boosting | Is model flexibility a remaining bottleneck? |
| 6 | Longer term: variable-duration sequence modeling and independently staged new animals | Can temporal structure help, and does the method generalize biologically? |

Use the same mouse-disjoint partitions for comparisons. Obtain outer held-out predictions with preprocessing, supervised feature choices, hyperparameters, calibration, and cutoff selection performed inside the fitting portion. Hand-designed features already influenced by this dataset remain exploratory even if later computations are nested. Show individual-mouse results and aggregate uncertainty over mice, not independent-day bootstrap intervals. With only three original test mice, any cluster uncertainty estimate is itself fragile.

Keep the current 0.932 result as a historical milestone. The original test mice have now informed diagnosis and hypotheses; future gains on them are exploratory. Neither changing the random seed until a favorable test score appears nor repeated tuning against these 36 days constitutes new validation. New independently staged animals are the strongest final assessment; obtaining them is proposed work, not something completed here.

## Work completed for this assessment

Reviewed the source, configuration, feature documentation, versioned milestone, and local saved predictions/model-comparison table; browsed primary papers and official software documentation; recomputed AP, confusion counts, sensitivity, specificity, precision, accuracy, F2, balanced accuracy, and per-mouse AP from saved predictions. No model training, feature regeneration, code tests, label edits, or contributor-file changes were performed. The threshold illustrations are retrospective arithmetic only. The local detailed run is ignored by Git and may be absent in a fresh checkout; reproduce the milestone using the [results guide](../RESULTS.md) before attempting to inspect those local artifacts.
