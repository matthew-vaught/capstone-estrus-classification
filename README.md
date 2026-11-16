# Estrus-day classification from mouse temperature and activity

This capstone investigates whether core body temperature (CBT) and locomotor activity (LA) features can distinguish estrus-proxy days in female mice. The pipeline combines independently developed feature sets, compares classifiers with mouse-grouped validation, and produces a shareable HTML report.

The dataset contains 14 days of one-minute recordings from 13 females. Analysis uses recording days 2–13, giving 156 mouse-days. Current submissions provide 28 features: Matthew's four, Alisha's eighteen, and Vivian's six. Brandon's folder contains feature evaluation code. See the [feature overview](docs/README.md#feature-documentation).

**Final setup (adopted November 15, 2026):** the original 28 features plus a **mouse-relative copy** of each, giving 56 inputs. Each copy is the value rescaled against the same mouse's median and IQR. The decision cutoff is selected by F2 on development mice, one mouse at a time, using one fixed model without calibration; see the [config](config/mouse-relative-fixed-cutoff.json) and [rationale](docs/research/mouse-relative-2026-11-15.md).

It replaced the November 13 setup (original 28 features, grouped-fold F2 cutoff) after beating it in both evaluations:

- **All 13 mice, each held out in turn:** 148 vs 145 correct of 156 days.
- **Reserved test mice:** 35 vs 34 correct of 36 days.

Mouse Baseline and LA–CBT Relationship features remain excluded; their experiments are retained for reference.

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
python run.py all --config config/mouse-relative-fixed-cutoff.json --save-details
python run.py model --config config/mouse-relative-fixed-cutoff.json --quick  # Trial, not the final search
python run.py test  # Complete shared pipeline on invented data
python -m pytest   # Unit and integration tests
```

Use the explicit `--config config/mouse-relative-fixed-cutoff.json` for the final setup. Omitting it selects the historical `Model Building/config.json`, which still uses cutoff 0.5. The previous final setup is reproducible with `config/threshold-f2.json`. The four input CSVs and submitted feature exports are included for course submission reproducibility. The build reads those exports without executing or changing contributors' code. Optional extraction commands are in the [reproduction guide](docs/REPRODUCING.md).

Open the printed `Model Building/results/run-.../report.html` path in a browser. Each run also contains readable `predictions.csv`, the evaluated `model.joblib`, and a short run README. `--save-details` retains configuration, hashes, splits, and technical records. The main metric is **average precision**, evaluated on three reserved mice. The [results guide](docs/RESULTS.md) describes the current milestone and how to interpret it.

The final run `final-2026-11-15` achieved **AP 0.980 and accuracy 97.2% (35/36)**, detecting 8/9 estrus-proxy days with no false alarms. The only miss is F3 day 10. The previous final setup scored AP 0.932 and 94.4%. The cutoff was approximately 0.505732; it is learned from development data and saved with the model. Across all 13 mice, each held out in turn, the final setup scored 148/156 correct (94.9%). See [results and limitations](docs/RESULTS.md) for the small cohort, provisional labels, and exploratory evaluation context.

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
