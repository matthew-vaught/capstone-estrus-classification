# Modeling and reports

Use the root [README](../README.md) for installation and the [reproduction guide](REPRODUCING.md) for build targets. The active implementation is `src/estrus/`; `Model Building/run.py` remains a compatibility entry point. The unfinished TensorFlow notebook is preserved under [notebooks/archive](../notebooks/archive/README.md).

## Feature inputs and evaluation

The model combines valid submitted CSVs and excludes reference features whenever at least one valid contribution exists. Current submissions provide Matthew's four, Alisha's eighteen, and Vivian's six features. Missing contributions are allowed. `--baseline` explicitly selects reference features alone.

All three submitted families include full-recording or future context, so the current team model performs retrospective classification. The reference baseline uses only the target day's signal. Per-feature requirements are carried from contributors' JSON notes into the saved model and report.

The workflow reserves three mice, compares logistic regression, random forest, and RBF SVM on the other ten, selects the combination with highest validation average precision, calibrates it, and evaluates it on the reserved mice. All days from a mouse stay together. Exact settings, leakage controls, feature assessments, and limitations are explained in [methods](METHODS.md).

```bash
python run.py model --save-details
python run.py model --quick
python run.py model --baseline --save-details
```

## Output files

| File | Purpose |
| --- | --- |
| `report.html` | Start here: selected model, average precision, feature assessments, and test-day plots; images are embedded |
| `predictions.csv` | Readable classes, estrus probability, and confidence for each held-out mouse-day |
| `model.joblib` | The exact fitted classifier evaluated in the report |
| `README.md` | A short guide to that particular run |
| `details/` | Configuration, hashes, splits, full scores, and other records when `--save-details` is used |

Probabilities use a 0–1 scale. Confidence is the probability assigned to the predicted class, rather than a guarantee of correctness. Average precision is a ranking metric and is not classification accuracy. Feature assessments use development mice; the headline score uses reserved mice.

Report examples show activity and temperature side by side. The black reference averages cycles within each female, then all thirteen females, including test mice, for visual comparison only. It never enters model fitting or scoring. See [methods](METHODS.md#cycle-day-reference-overlays) for the provisional cycle alignment and display conventions.

## Prediction

After computing every required input feature, pass assembled rows to the saved model:

```bash
estrus predict --model 'Model Building/results/RUN/model.joblib' \
  --features /path/to/assembled_features.csv --output data/outputs/predictions.csv
```

The model requires its original feature schema. A model using retrospective contributor features needs the complete-recording extraction procedure described in each [feature document](README.md#feature-documentation). The [feature contract](FEATURE_CONTRACT.md#predict-a-new-day-with-the-reference-baseline) contains an isolated-day example for reference models.

The saved classifier excludes test mice from fitting. Only load trusted model files because joblib uses Python serialization. For a presentation milestone and reproduction commands, see [results](RESULTS.md).
