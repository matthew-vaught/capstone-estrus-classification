# Project documentation

This project evaluates temperature and activity features for retrospective classification of female mouse-days. The root [README](../README.md) provides installation and the shortest path to a report.

**Retained final model:** original 28 features with F2 decision-threshold tuning, using [config/threshold-f2.json](../config/threshold-f2.json). Both experimental feature families are excluded. The [results guide](RESULTS.md) gives the retained scores and the recorded reasons for excluding those experiments.

| Guide | What it explains |
| --- | --- |
| [Reproducing the project](REPRODUCING.md) | Environment, build stages, regeneration, configuration, and synthetic verification |
| [Results](RESULTS.md) | Retained final result, historical presentation milestone, excluded experiments, and evaluation limits |
| [Historical improvement research plan](research/estrus-improvement-2026-11-11.md) | Original error analysis, literature, and hypotheses before the completed experiments |
| [Decision-threshold tuning](THRESHOLD_TUNING.md) | Retained development-only cutoff selection, F2 objective, comparison with 0.5, and saved-model behavior |
| [Data](DATA.md) | Classroom recordings, checksums, provisional labels, and data-retention policy |
| [Methods](METHODS.md) | Features, grouped evaluation, metrics, and scientific limitations |
| [Modeling and reports](MODELING.md) | Available models, saved artifacts, and inference |
| [Feature contract](FEATURE_CONTRACT.md) | CSV schema, canonical keys, validation, and input requirements |
| [Collaboration](COLLABORATION.md) | Contributor ownership and development workflow |

## Feature documentation

Feature calculations remain in their contributor or experimental-family folders. Definitions and reproduction notes are centralized below.

| Contributor | Current submission | Documentation |
| --- | --- | --- |
| Matthew | 4 features: Morse amplitudes, next-day LA change, and threshold fractions | [Definitions and diagnostics](features/matthew.md) |
| Alisha | 18 within-mouse DTW time-shift features | [Definitions and exploratory analysis](features/alisha.md) |
| Vivian | 6 activity-adjusted CBT and correlation features | [Definitions and notebook regeneration](features/vivian.md) |
| Brandon | Feature evaluation notebook and starter exporter; no submitted feature CSV | [Starter and submission instructions](features/brandon.md) |
| Mouse Baseline (excluded) | 4 within-mouse contrasts; historical experiment only | [Rationale, formulas, and experiment](features/mouse-baseline.md) |
| LA CBT Relationship (excluded) | 4 day-local joint-signal descriptors; historical experiment only | [Paper motivation, definitions, and experiment](features/la-cbt-relationship.md) |

The final configuration currently consumes 28 numeric columns on all 156 canonical mouse-days. All three supplied original feature families include complete-recording context. Each excluded experiment separately offered 32 columns; neither family's CSV is automatically added to the final setup.

## References and repository design

The supplied [research paper](references/mouse_sex_diff.pdf) motivates the analysis. The [course software-engineering guidelines](references/repo_formatting_best_practices.pdf) emphasize reproducibility, configuration, reusable code, and synthetic testing.

The shared package isolates data handling, CSV validation, modeling, and reporting. Contributor folders preserve independent ownership and communicate through validated CSVs. A thin root build script makes those stages discoverable without relocating contributors' implementation. Detailed documentation lives here so a reviewer can start from a concise root README.

Raw input CSVs and submitted feature exports are deliberately retained for the course submission. This is an explicit exception to the course's general data-versioning recommendation; see the [data policy](DATA.md#version-control-policy). Notebook-based extraction remains contributor-owned, so rebuilding every real feature family from raw data is not yet one automated command. The [reproduction guide](REPRODUCING.md#feature-regeneration) identifies that boundary.
