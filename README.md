# Estrus-day classification capstone

A collaborative workspace for classifying a **female mouse-day** from core body temperature (CBT) and locomotor activity (LA). Each teammate works in their own folder and exports one CSV. Model building combines valid teammate exports and uses **only those contributor features**. Reference features are used only when no valid export exists or when you explicitly request a baseline run.

**Input scope:** reference features use one day. Matthew's wavelet contribution uses the complete 14-day recording and next-day context, so a model accepting those inputs performs retrospective classification. See [Matthew's feature definitions](Matthew%20Feature%20Engineering/README.md); it cannot be computed from an isolated new day.

**Current labels are provisional:** recording days **2, 6, and 10** are treated as estrus; recording days 1 and 14 are excluded as buffers. This follows the team's likely alignment with the supplied paper, but the CSVs contain no timestamps or independent stage labels. The paper itself identified estrus from CBT patterns. Results therefore measure separation of that paper-aligned phenotype until alignment and biological labels are independently confirmed.

## Get started

Python 3.11 or newer is required. Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,notebooks]'

estrus prepare
estrus run --quick
```

`--quick` uses fewer validation splits, trees, and model settings. Open the printed `Model Building/results/run-.../report.html` file in a browser. It shows **the chosen model and average precision**, feature rankings grouped by person, which features the final model uses, and expandable test-day plots. The HTML includes its images and can be shared as one file.

If you use `uv`, the equivalent install is `uv venv` followed by `uv pip install -e '.[dev,notebooks]'`. Exact versions used to verify this repository are recorded in `requirements-lock.txt`; use `uv pip install -r requirements-lock.txt` then `uv pip install --no-deps -e .` for that environment.

```bash
# Compare models and feature sets, then test the winning combination
estrus run

# Validate submissions; missing people are fine
estrus validate
estrus validate --owner Vivian

# Use independently curated labels instead of the provisional default
estrus run --labels /path/to/confirmed_labels.csv

# Optional technical records for deeper analysis
estrus run --save-details

# Reference-only comparison, even when teammates have exported features
estrus run --baseline --output "Model Building/results/reference-comparison"

python -m pytest
```

`python "Model Building/run.py" --quick` is also available after installation. Commands can locate the repo from any directory inside it; from elsewhere, use `estrus --root /path/to/repo run`. Supplied relative file paths are relative to your current working directory.

## Repository layout

```text
Matthew Feature Engineering/   Matthew's exploration, code, outputs/features.csv
Vivian Feature Engineering/    Vivian's exploration, code, outputs/features.csv
Brandon Feature Engineering/   Brandon's exploration, code, outputs/features.csv
Alisha Feature Engineering/    Alisha's exploration, code, outputs/features.csv
Model Building/
  config.json                 Shared evaluation settings, maintained by Matthew
  run.py                      Training entry point
  results/                    Local runs, ignored by Git
data/
  inputs/                     Original female + male CSVs, left untouched
  Important Data Files/       Supplied research paper
  outputs/                    Reproducible prepared data and templates, ignored
src/estrus/                   Shared data, validation, features, modeling, reporting
docs/                         Feature contract and scientific methods
tests/                        Contract, leakage, and pipeline checks
```

## Each person's workflow

1. Create a branch for your work, such as `vivian/wavelet-features`.
2. Work entirely inside your own `Name Feature Engineering/` folder. Explore in notebooks or scripts however you prefer.
3. Edit your `features.py` starter, or export from a notebook with the shared helper. Your handoff must have all 156 mouse-day keys and numeric columns prefixed with your name, such as `vivian__ur_power`.
4. Generate and validate your CSV:

   ```bash
   python "Vivian Feature Engineering/features.py"
   estrus validate --owner Vivian
   ```

5. Commit your code, feature notes, and `outputs/features.csv` in that folder, then open a PR. After it is merged, the next model run automatically includes your features. Nobody has to edit model-building code to register a contribution.

The starters contain two small example features and are not automatically executed. With **zero valid exports**, training uses the reference baseline. As soon as one valid export exists, training uses **only the combined contributor features**, excluding all reference features. For example, Matthew's four features alone give four available features; if Vivian adds three, there are seven. Feature selection may use a subset. Missing and invalid submissions are skipped with feedback. If none remain valid, the pipeline reports that it is falling back to the baseline. `estrus validate` returns nonzero for invalid submissions so CI can catch them.

To compare your features against the reference baseline, run normally for team features and use `--baseline` for reference features. Keep the same labels, configuration, seed, and quick/full setting. Both runs use the same mouse split. Each run has a separate output folder, and the report states its feature inputs. The existing `final-baseline/` result is preserved.

The exact handoff format and notebook export example are in [docs/FEATURE_CONTRACT.md](docs/FEATURE_CONTRACT.md). Folder ownership, branch rules, and shared-file changes are explained in [CONTRIBUTING.md](CONTRIBUTING.md).

## Modeling and interpretation

The workflow reserves **3 mice for testing** and uses the remaining **10 mice to compare** logistic regression, random forest, and an RBF SVM. Each model tries all usable features, the top 35%, and the top 70%. Reduced sets rank features using a training-only class-separation score. The combination with the highest validation average precision wins. All days from a mouse stay together, and preprocessing and feature ranking stay inside training splits.

The winner is fitted once on the training mice, with calibrated probabilities, and evaluated on the reserved mice. **Average precision is the primary metric** throughout: higher is better and 1 is perfect. Model-comparison scores come from training-validation splits; the headline score comes from the separate test mice. The report groups every feature by contributor, shows its predictive strength and contribution, and marks the exact features used in the saved model. See [docs/METHODS.md](docs/METHODS.md) for details and limitations.

Each results folder contains **four files**: `report.html` to review the results, `predictions.csv` to inspect days in a spreadsheet, `model.joblib` to reuse the trained model, and a short `README.md`. The predictions spreadsheet uses readable class names and columns `mouse_id`, `day_index`, `actual_class`, `predicted_class`, `estrus_probability`, and `confidence` (probabilities are on a 0–1 scale).

Use `estrus run --save-details` only if you want the technical records in an additional `details/` folder. The saved model is exactly the model evaluated in the report; the reserved test mice are not used to fit it. Only load model files you trust, since joblib uses Python serialization.

```bash
# Inference accepts one or more rows with the saved model's complete feature schema.
estrus predict --model 'Model Building/results/RUN/model.joblib' \
  --features /path/to/assembled_features.csv --output data/outputs/predictions.csv
```

To classify a new raw day with a baseline model, use `estrus.features.extract_day(day)` on a 1,440-row DataFrame with `cbt` and `la`, and prefix returned names with `baseline__`. For a contributor-only model, compute the contributor features using their documented code; reference columns are not required. Missing required columns are an error at inference; the trained schema cannot silently change. See the complete example in the feature contract.

## Data source

Smarr BL, Grant AD, Zucker I, Prendergast BJ, Kriegsfeld LJ (2017). *Sex differences in variability across timescales in BALB/c mice.* Biology of Sex Differences 8:7. DOI: [10.1186/s13293-016-0125-3](https://doi.org/10.1186/s13293-016-0125-3). The supplied copy is in `data/Important Data Files/mouse_sex_diff.pdf`. Its Methods (pp. 2–3) describe one-minute sampling, 12 analysis days buffered by two additional days, and CBT-based estrus alignment. The paper's Morse wavelet analysis is not exactly reproduced by the day-local Morlet reference features here.
