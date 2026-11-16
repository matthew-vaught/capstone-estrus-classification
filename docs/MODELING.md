# Modeling and reports

Use the root [README](../README.md) for installation and the [reproduction guide](REPRODUCING.md) for build targets. The active implementation is `src/estrus/`; `Model Building/run.py` remains a compatibility entry point. The unfinished TensorFlow notebook is preserved under [notebooks/archive](../notebooks/archive/README.md).

## Feature inputs and evaluation

The model combines valid submitted CSVs and excludes reference features whenever at least one valid contribution exists. Current submissions provide Matthew's four, Alisha's eighteen, and Vivian's six features. Missing contributions are allowed. `--baseline` explicitly selects reference features alone.

All three submitted families include full-recording or future context, so the current team model performs retrospective classification. The reference baseline uses only the target day's signal. Per-feature requirements are carried from contributors' JSON notes into the saved model and report.

The workflow reserves three mice, compares logistic regression, random forest, and RBF SVM on the other ten, selects the combination with highest validation average precision, and evaluates it on the reserved mice. Calibration is configurable; the final configuration uses none. All days from a mouse stay together. Exact settings, leakage controls, feature assessments, and limitations are explained in [methods](METHODS.md).

The final setup adds a mouse-relative copy of every feature and a decision cutoff selected by F2 on one-mouse-at-a-time development probabilities from one fixed model. Mouse Baseline and LA CBT Relationship features are excluded. Use the explicit final configuration:

```bash
python run.py model --config config/mouse-relative-fixed-cutoff.json --save-details
python run.py model --config config/mouse-relative-fixed-cutoff.json --quick
python run.py model --config config/mouse-relative-fixed-cutoff.json --baseline --save-details
```

The last command is a reference-only comparison, not the final contributor model; `--quick` is a reduced trial, not the recorded final search. For the historical fixed-0.5 run:

```bash
python run.py model --config "Model Building/config.json" --save-details
```

The final configuration refits the chosen model with each development mouse left out to obtain mouse-disjoint development predictions, selects a cutoff by F2, and freezes it before test prediction. The previous final configuration, `config/threshold-f2.json`, repeated model selection and calibration within three grouped folds. The report compares it with 0.5 on the same model. Omitting `--config` still selects the historical fixed-0.5 configuration. See [threshold tuning](THRESHOLD_TUNING.md) for the protocol, interpretation limits, and detailed outputs.

For historical experiment reproduction only, `config/mouse-baseline-f2.json` enables [Mouse Baseline features](features/mouse-baseline.md), and `config/la-cbt-relationship-f2.json` enables [LA–CBT relationship descriptors](features/la-cbt-relationship.md). Both were excluded from the final model; their code, exports, and results remain as research records. They use explicit `feature_owners` lists and do not change the final configuration's original 28 inputs.

The November 15 [mouse-relative experiment](research/mouse-relative-2026-11-15.md) added several opt-in settings. The final configuration uses `mouse_relative_features`, `folds: leave_one_mouse_out`, `model_search: fixed`, and `calibration: false`:

- **`"mouse_relative_features": true`** appends a within-mouse rescaled copy of every feature.
- **`"objective": "accuracy"`** chooses the cutoff by plain accuracy.
- **`"folds": "leave_one_mouse_out"`**, inside `threshold_tuning`, chooses the cutoff from one-mouse-at-a-time development predictions.
- **`"calibration": false`** skips sigmoid calibration, except for SVMs.
- **`"model_search": "fixed"`**, inside `threshold_tuning`, reuses the development model choice in every cutoff fold instead of searching again.
- **`"test_mouse_ids": [...]`**, at the top level, names the reserved mice explicitly instead of drawing them with the seed. The all-mice evaluation uses it.

Their configs are listed in the [config index](../config/README.md). [mouse-relative-fixed-cutoff.json](../config/mouse-relative-fixed-cutoff.json) improved accuracy in both evaluations (148 vs 145 of 156 days on all 13 mice; 35 vs 34 of 36 test days). It was adopted as the final model. A saved mouse-relative model needs `mouse_id` and should receive every available day for each mouse at prediction time, because the copies depend on that mouse's other days.

The final run `final-2026-11-15` used logistic regression, C=1, with 20 selected features (10 original, 10 mouse-relative) and cutoff 0.505732: AP 0.980, accuracy 97.2%. The previous final run scored AP 0.932 and accuracy 94.4%. Each fresh run selects its cutoff from development data; reuse `model.joblib` to obtain the exact recorded model and cutoff. See [results](RESULTS.md) for provenance and cohort-specific limits.

## Output files

| File | Purpose |
| --- | --- |
| `report.html` | Start here: selected model, average precision, feature assessments, and test-day plots; images are embedded |
| `predictions.csv` | Readable classes, estrus probability, and confidence for each held-out mouse-day |
| `model.joblib` | The exact fitted classifier evaluated in the report |
| `README.md` | A short guide to that particular run |
| `details/` | Configuration, hashes, splits, full scores, and other records when `--save-details` is used |

Probabilities use a 0–1 scale. Confidence is the probability assigned to the predicted class, rather than a guarantee of correctness. Average precision is a ranking metric and is not classification accuracy. Feature assessments use development mice; the headline score uses reserved mice.

The saved model includes the decision cutoff used in its report. A recall-oriented cutoff below 0.5 can produce an Estrus decision with confidence below 50%.

Report examples show activity and temperature side by side. The black reference averages cycles within each female, then all thirteen females, including test mice, for visual comparison only. It never enters model fitting or scoring. See [methods](METHODS.md#cycle-day-reference-overlays) for the provisional cycle alignment and display conventions.

## Prediction

After computing every required input feature, pass assembled rows to the saved model:

```bash
estrus predict --model 'Model Building/results/RUN/model.joblib' \
  --features /path/to/assembled_features.csv --output data/outputs/predictions.csv
```

The model requires its original feature schema. A model using retrospective contributor features needs the complete-recording extraction procedure described in each [feature document](README.md#feature-documentation). The [feature contract](FEATURE_CONTRACT.md#predict-a-new-day-with-the-reference-baseline) contains an isolated-day example for reference models.

The saved classifier excludes test mice from fitting. Only load trusted model files because joblib uses Python serialization. For a presentation milestone and reproduction commands, see [results](RESULTS.md).
