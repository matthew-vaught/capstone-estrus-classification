# Reproducing the project

## Environment

Run commands from the repository root unless otherwise indicated. The shared pipeline's pinned environment was verified on Linux with Python 3.12. The package declares Python >=3.11; other Python/OS combinations have not received equivalent verification.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
```

For PowerShell, activate with `.\.venv\Scripts\Activate.ps1`. Use the same environment as the kernel for project notebooks. The pinned file includes development and notebook tools. For flexible dependency resolution during development, use `python -m pip install -e '.[dev,notebooks]'` instead; that does not promise the same exact versions.

`numba` is needed only to regenerate Alisha's DTW export. Install the optional extraction dependencies with `python -m pip install -e '.[extraction]'`. This optional environment is resolved separately from the verified shared-pipeline lock and may choose different compatible numerical-library versions. Training from the supplied exports does not need it.

## Build stages

The root `run.py` delegates to the installed `estrus` package. It can locate the checkout from its own path, so the script also works when invoked from another working directory. Explicit relative `--config`, `--labels`, and `--output` paths are relative to that working directory.

| Command | Behavior and outputs |
| --- | --- |
| `python run.py data` | Verify all four input checksums and prepare minute/day tables and label templates in `data/outputs/build/prepared/` |
| `python run.py features` | Validate and combine supplied contributor CSVs into `data/outputs/build/features.csv`; use reference features if no valid export exists |
| `python run.py validate` | Check submitted exports without fitting a model |
| `python run.py model --save-details` | Validate exports, select and evaluate a model, and write a new result folder |
| `python run.py all --save-details` | Run data preparation, feature assembly, and modeling in order |
| `python run.py test` | Build and verify the shared pipeline using invented data in a temporary checkout |
| `python run.py clean` | Remove only `data/outputs/build/`, including synthetic reports stored there |

Targets may be combined, for example `python run.py data features`. `clean` preserves classroom inputs, contributors' files, historical model results, and outputs made separately with `estrus prepare`. Build intermediates are regenerated on each requested stage; this is not a general caching engine. Contributor-based runs avoid computing unused reference features.

The normal `all` target starts with retained raw inputs and submitted feature artifacts. It does **not** rerun contributor notebooks or extraction code. Independent feature families can be generated separately, then joined by mouse/day keys. DTW alignment and complete-recording wavelets are the main extraction costs; model search and reporting are separate stages.

The build script stops on invalid submissions. Missing submissions, including Brandon's current starter, are allowed. The lower-level `estrus run` command retains its original behavior of skipping invalid exports with feedback. `--baseline` explicitly bypasses contributor exports in either interface.

## Feature regeneration

Feature code and notebooks remain contributor-owned. Default builds read the small, committed CSV handoffs and leave their folders unchanged.

| Contributor | Regeneration interface | Current boundary |
| --- | --- | --- |
| Matthew | `python run.py features --regenerate Matthew` | Executes his existing script; also replaces his generated diagnostics/metadata |
| Alisha | `python run.py features --regenerate Alisha` | Executes her existing script; requires optional `numba` dependencies and may populate her cache |
| Vivian | Open `Vivian Feature Engineering/feature.ipynb` using the project kernel, with that folder as the working directory | Her notebook is the authoritative exporter; `features.py` remains a starter and must not be used to recreate the six-feature submission |
| Brandon | Follow the [starter guide](features/brandon.md) when developing a submission | No completed export currently exists |

`--regenerate` requires an explicit owner and is accepted only with `features` or `all`. Vivian and Brandon are intentionally not automated by this wrapper. No contributor implementation was refactored as part of the repository cleanup. The only contributor-code path adjustment points Matthew's provenance hashing to his relocated feature document.

Consequently, the real-data model can be reproduced from the submitted artifacts without manual extraction, but full raw-to-all-contributor-feature regeneration still includes Vivian's notebook step. The synthetic build checks the entire shared path using stand-in features; it does not verify the numerical implementation of each contributor's extractor.

## Model configuration and variants

The default [configuration](../Model%20Building/config.json) controls the random seed, number of reserved mice, validation folds, trees, parallel jobs, feature-selection percentages, regularization grid, and forest settings. Keep alternative experiment JSON files under `config/` and pass `--config` rather than editing model logic. Old minimal configuration files remain supported through defaults.

```bash
python run.py model --config "Model Building/config.json" --save-details
python run.py model --baseline --save-details
python run.py all --quick
python run.py model --labels /path/to/confirmed_labels.csv --save-details
```

For a new experiment, copy that configuration into `config/` under a descriptive name and pass its path. `--quick` overrides validation folds to two, trees to forty, and the regularization search to the quick grid. Use full mode for the presentation result. Baseline/team comparisons need matching labels, seed, configuration, and quick/full mode.

`python run.py model --config config/threshold-f2.json --save-details` runs the opt-in [decision-threshold experiment](THRESHOLD_TUNING.md) using the full model search and unchanged labels/features. It adds nested mouse-grouped development fits to choose a cutoff by F2, and compares it with 0.5. Omitting `threshold_tuning` preserves the historical fixed cutoff.

Proxy-label days, canonical mouse/day keys, and frozen scientific feature definitions are documented in [methods](METHODS.md) and the [contract](FEATURE_CONTRACT.md). Curated labels are supplied separately with `--labels`. This cleanup does not change the target, split, or feature definitions.

## Results and provenance

Default model outputs are new timestamped directories under `Model Building/results/`. An explicit `--output` must name a new or empty directory. Start with `report.html`; its images are embedded. Other default files are `predictions.csv`, `model.joblib`, and a short run README.

Use `--save-details` for a result intended for submission. The added `details/` includes source and input hashes, versions, configuration, splits, metrics, feature assessments, and full predictions. Historical contributor manifests describe their original generation and may reference paths from before the documentation move; they are preserved rather than rewritten as if regenerated. Model-run metadata separately hashes the currently supplied exports.

The `estrus` CLI remains available for preparation, validation, modeling, and inference. For example, `estrus prepare` writes to `data/outputs/`, while the build script isolates its prepared intermediates under `data/outputs/build/`. See [modeling](MODELING.md) for prediction examples.

## Verification without classroom data

```bash
python run.py test
python -m pytest
```

The synthetic target starts from the five invented hour anchors in [synthetic_profiles.json](../tests/fixtures/synthetic_profiles.json). It expands them to the fixed production shape in a temporary directory, prepares and reloads tables, extracts reference features, writes two stand-in contributor columns, validates the CSV handoff, trains, renders a report, and verifies saved-model probabilities against the exported predictions. It reads no classroom CSVs or real contributor exports. Synthetic scores have no biological interpretation.

The generated synthetic report is stored under `data/outputs/build/synthetic-.../`, or at `--output PATH`. Temporary raw recordings are removed when the command ends. The pytest suite includes this synthetic integration check as well as contracts, missing data, mouse separation, reporting, and model replay checks. A few separate integration tests intentionally use the retained classroom inputs.
