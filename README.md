# Estrus-day classification from mouse temperature and activity

This capstone investigates whether core body temperature (CBT) and locomotor activity (LA) features can distinguish estrus-proxy days in female mice. The pipeline combines independently developed feature sets, compares classifiers with mouse-grouped validation, and produces a shareable HTML report.

The dataset contains 14 days of one-minute recordings from 13 females. Analysis uses recording days 2–13, giving 156 mouse-days. Current submissions provide 28 features: Matthew's four, Alisha's eighteen, and Vivian's six. Brandon's folder contains feature evaluation code. See the [feature overview](docs/README.md#feature-documentation).

**Interpretation:** labels for recording days 2, 6, and 10 are provisional paper-alignment proxies, rather than independently confirmed biological stages. Current contributor features require complete recordings, including future context, and support retrospective classification. The [methods](docs/METHODS.md) explain these limitations.

## Install

Run from the repository root. The pinned environment was verified with Python 3.12 on Linux; the package declares Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`. Notebook and optional feature-extraction setup are documented in the [reproduction guide](docs/REPRODUCING.md).

## Reproduce and review

```bash
python run.py all --save-details  # Prepare data, assemble supplied exports, train and report
python run.py all --quick         # Faster trial with a smaller model search
python run.py test                # Complete shared pipeline on invented data
python -m pytest                 # Unit and integration tests
```

The four input CSVs and submitted feature exports are included for course submission reproducibility. The default build reads those exports without executing or changing contributors' code. Optional extraction commands and the notebook-based regeneration boundary are documented in the [reproduction guide](docs/REPRODUCING.md).

Open the printed `Model Building/results/run-.../report.html` path in a browser. Each run also contains readable `predictions.csv`, the evaluated `model.joblib`, and a short run README. `--save-details` retains configuration, hashes, splits, and technical records. The main metric is **average precision**, evaluated on three reserved mice. The [results guide](docs/RESULTS.md) describes the current milestone and how to interpret it.

## Repository map

| Location | Purpose |
| --- | --- |
| `src/estrus/` | Shared loading, contracts, reference features, modeling, and reporting |
| `* Feature Engineering/` | Each contributor's code, notebooks, and submitted export |
| `Model Building/` | Evaluation configuration, compatibility entry point, and local results |
| `data/inputs/` | Unmodified classroom recordings, retained in Git |
| `docs/` | Methods, feature definitions, reproduction instructions, and references |
| `tests/` | Shared checks and a small synthetic-data recipe |
| `notebooks/archive/` | Historical modeling prototype |

## AI use

Human contributors supplied the research context, feature submissions, and project decisions. OpenAI Codex assisted with repository review, documentation, shared build and model-configuration changes, and test creation and execution under human direction. The team remains responsible for reviewing the code and scientific conclusions. See [AI_USE.md](AI_USE.md) for the available prompts, contributions, testing, and gaps in the earlier project history.

## Documentation and attribution

Start with the [documentation index](docs/README.md). Development and folder ownership are covered in the [collaboration guide](docs/COLLABORATION.md).

Feature contributors: Matthew, Vivian, Brandon, and Alisha. Research reference: Smarr et al. (2017), *Sex differences in variability across timescales in BALB/c mice*, Biology of Sex Differences 8:7, DOI [10.1186/s13293-016-0125-3](https://doi.org/10.1186/s13293-016-0125-3). A supplied copy is in [docs/references](docs/references/mouse_sex_diff.pdf).
