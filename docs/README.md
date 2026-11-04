# Project documentation

This project evaluates temperature and activity features for retrospective classification of female mouse-days. The root [README](../README.md) provides installation and the shortest path to a report.

| Guide | What it explains |
| --- | --- |
| [Reproducing the project](REPRODUCING.md) | Environment, build stages, regeneration, configuration, and synthetic verification |
| [Results](RESULTS.md) | Presentation milestone, report interpretation, and evaluation limits |
| [Data](DATA.md) | Classroom recordings, checksums, provisional labels, and data-retention policy |
| [Methods](METHODS.md) | Features, grouped evaluation, metrics, and scientific limitations |
| [Modeling and reports](MODELING.md) | Available models, saved artifacts, and inference |
| [Feature contract](FEATURE_CONTRACT.md) | CSV schema, canonical keys, validation, and input requirements |
| [Collaboration](COLLABORATION.md) | Contributor ownership and development workflow |

## Feature documentation

Feature calculations remain in their original contributor folders. The documents below were moved from those folders, retaining the feature explanations and updating links.

| Contributor | Current submission | Documentation |
| --- | --- | --- |
| Matthew | 4 features: Morse amplitudes, next-day LA change, and threshold fractions | [Definitions and diagnostics](features/matthew.md) |
| Alisha | 18 within-mouse DTW time-shift features | [Definitions and exploratory analysis](features/alisha.md) |
| Vivian | 6 activity-adjusted CBT and correlation features | [Definitions and notebook regeneration](features/vivian.md) |
| Brandon | Starter examples; no submitted CSV | [Starter and submission instructions](features/brandon.md) |

The current submitted feature set contains 28 numeric columns and all 156 canonical mouse-days. All three submitted feature families include complete-recording context. Counts describe the current submission and will change as contributors update their exports.

## References and repository design

The supplied [research paper](references/mouse_sex_diff.pdf) motivates the analysis. The [course software-engineering guidelines](references/repo_formatting_best_practices.pdf) emphasize reproducibility, configuration, reusable code, and synthetic testing.

The shared package isolates data handling, CSV validation, modeling, and reporting. Contributor folders preserve independent ownership and communicate through validated CSVs. A thin root build script makes those stages discoverable without relocating contributors' implementation. Detailed documentation lives here so a reviewer can start from a concise root README.

Raw input CSVs and submitted feature exports are deliberately retained for the course submission. This is an explicit exception to the course's general data-versioning recommendation; see the [data policy](DATA.md#version-control-policy). Notebook-based extraction remains contributor-owned, so rebuilding every real feature family from raw data is not yet one automated command. The [reproduction guide](REPRODUCING.md#feature-regeneration) identifies that boundary.
