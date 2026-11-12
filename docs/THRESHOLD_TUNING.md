# Decision-threshold experiment

This experiment changes how predicted probabilities become Estrus/Non-estrus decisions. It uses the existing contributor features, labels, mouse split, model search, and final probability calibration. Mouse-relative and joint LA–CBT feature experiments remain separate future work.

## Run it

From the installed project environment:

```bash
python run.py model --config config/threshold-f2.json --save-details
```

Open the printed `report.html`. It shows the selected cutoff, a comparison against 0.5 on the same final model, and the development selection curve. A new output directory preserves historical runs. The default `Model Building/config.json` still uses 0.5, so `python run.py model --save-details` retains the historical decision rule. Old saved models retain their own cutoffs.

The [experiment configuration](../config/threshold-f2.json) copies the maintained full-search settings and adds:

```json
"threshold_tuning": {
  "enabled": true,
  "objective": "f2"
}
```

Supported objectives are `f2` and `balanced_accuracy`. F2 is the predeclared first experiment because missed estrus days are the immediate concern. Its formula is `5 TP / (5 TP + 4 FN + FP)`: it emphasizes recall while penalizing false alarms. It does not force every day positive to guarantee recall. Balanced accuracy gives equal weight to sensitivity and specificity. Neither objective guarantees 100% accuracy or an improvement on new mice.

## How the cutoff is selected

1. Reserve f3, f6, and f11 using the existing ID/seed split. Do not pass their features or labels to cutoff selection.
2. Split the ten development mice into the existing three mouse-disjoint folds. For each fold, exclude its validation mice from every fitting operation.
3. On that fold's fitting mice, repeat the existing model/feature-subset/hyperparameter search using inner mouse-grouped folds. Fit median imputation, scaling, and supervised feature selection inside those pipelines.
4. Calibrate the selected configuration using sigmoid calibration and mouse-grouped folds entirely within the fitting mice. Predict probabilities for the excluded development mice. Each development day receives one probability from a fitting process that excluded its mouse.
5. Pool those development probabilities and compare candidate cutoffs. Candidates are the midpoints between distinct probabilities, plus 0, 0.5, and 1. The rule is `p_estrus >= cutoff`. Maximize the configured objective. Scores within absolute tolerance 1e-12 tie; prefer the candidate closest to 0.5, then the higher candidate. This is a deterministic convention, not a preference chosen after inspecting test results.
6. Freeze the selected cutoff. Run the original full-development model selection and final calibration, then calculate reserved-test probabilities once. Apply both 0.5 and the frozen cutoff to those identical probabilities.

The final model and its probability outputs match the ordinary run when inputs and original configuration settings match. Extra development fits determine only the cutoff. Fold-specific model choices can differ; the selection probabilities assess the existing model-selection procedure rather than reuse a configuration selected using the scored mice's labels.

Nested fitting costs more computation than changing a number in a saved model. It avoids using validation-mouse labels to choose the classifier or calibrator that generated those same mice's threshold-selection probabilities. Scikit-learn describes the distinction between [probability estimation and decision-threshold tuning](https://scikit-learn.org/stable/modules/classification_threshold.html), and [grouped probability calibration](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html) supports the explicit fold indices used here.

The fitting portion of every threshold-validation fold must contain at least two mice, with both classes present in each inner fitting/validation partition. Inner fold count is the smaller of configured `cv_folds` and the number of fitting mice. An insufficient cohort or invalid class distribution produces an error rather than silently reverting to random row splits. `--quick` changes the search and fold count and is a separate experiment.

## What to inspect

The main report compares default and selected cutoffs using accuracy, estrus recall, specificity, precision, missed estrus days, and false alarms. AP remains the model-selection/ranking metric and is identical between these two operating points. Probability magnitudes, Brier score, and log loss also remain unchanged.

With `--save-details`, the run retains:

| File under `details/` | Purpose |
| --- | --- |
| `threshold_tuning.json` | Objective, exact cutoff, tie rule, development selection metrics, and inner/outer mouse memberships with fold-specific model choices |
| `threshold_validation_predictions.csv` | One excluded-mouse development probability per day, with original target and fold ID |
| `threshold_curve.csv` | Candidate cutoffs, development metrics/confusion counts, and the selected candidate |
| `threshold_comparison.csv` | Reserved-test metrics at 0.5 and at the frozen development cutoff |
| `final_model.json` | Final configuration and its exact cutoff/selection evidence |

The model bundle stores the same cutoff and evidence even without detailed output. `estrus predict` uses it automatically. `predicted_class_probability` and the readable `confidence` column refer to the chosen class: `p_estrus` for Estrus, `1-p_estrus` for Non-estrus. With a cutoff below 0.5, an Estrus decision can correctly have class probability below 50%; that reflects the recall-oriented decision rule.

## Interpretation limits

Development metrics and the curve are selection evidence, not independent validation of the chosen cutoff. Although every probability excludes its mouse from fitting, choosing the cutoff uses all development targets. An additional outer evaluation would be needed for an independent cross-validation estimate of the full threshold-selection procedure. Earlier hand-designed features already used this dataset, which cannot be undone by nested computation.

The existing test mice were inspected before this experiment was conceived. Results on them are an exploratory comparison against the historical milestone, not a newly untouched biological validation. Freeze the objective and protocol before running; report the observed outcome even if sensitivity or accuracy gets worse. Keep all original labels and days, including F3 day 10. New independently staged animals remain the strongest future assessment.

## Verification

Tests cover known-score cutoff selection and its recall/false-alarm tradeoff, deterministic ties and equality handling, configuration/input validation, unchanged probability metrics, mouse separation through the nested fitting layers, invariance of threshold/model choice to reserved-test label changes, saved-model replay, class probability below 0.5, and report display of the selected cutoff/comparison. An additional regression test flips the labels of an excluded development fold and requires its own generated probabilities and model-choice audit to remain exactly unchanged, checking exclusion from search and calibration as well as fitting. Tests use synthetic data; they verify software behavior rather than biological label accuracy.

## First full experiment: November 11, 2026

The development-selected cutoff was **0.36718281570864303**, maximizing F2 on 120 excluded-mouse development probabilities. At that cutoff, the development selection data had 30/30 positives detected and 4/90 false alarms, compared with 28/30 detected and 3/90 false alarms at 0.5. These are selection scores.

| Historical test cohort: 36 days from 3 mice | Default 0.5 | Selected 0.367183 |
| --- | --- | --- |
| Estrus detected | 5/9 | 7/9 |
| False alarms | 0/27 | 0/27 |
| Accuracy | 88.9% | 94.4% |
| Recall | 55.6% | 77.8% |
| Precision / specificity | 100% / 100% | 100% / 100% |
| F2 | 0.610 | 0.814 |
| Average precision | 0.932 | 0.932 |

The final model remained logistic regression, C=1, with the same ten selected features. Every test probability matched the saved presentation run within `rtol=1e-12, atol=1e-12`; original test labels were identical. F3 day 2 and F11 day 6 changed to Estrus decisions. F3 day 10 and F11 day 10 remain false negatives. No cutoff was adjusted after seeing this test comparison.

The local run is `Model Building/results/threshold-f2-2026-11-11/`, ignored by Git. A small [versioned result/provenance record](results/threshold-f2-2026-11-11.json) preserves the exact cutoff, comparison, configuration, fold evidence, software versions, source/input hashes, and artifact hashes. The report, model, and detailed local outputs were generated successfully. Saved-model replay, reconstruction of the cutoff from its development CSV, nested mouse memberships, and preservation of 250 original input/contributor/historical-result files were checked.
