# Brandon Feature Engineering

Brandon's current work includes [model_eval.ipynb](../../Brandon%20Feature%20Engineering/model_eval.ipynb) for feature evaluation. No `outputs/features.csv` is currently submitted, so his work does not add columns to the retained 28-feature model. The instructions below describe the existing starter exporter for a future feature contribution.

Brandon owns everything inside this folder. Put notebooks, figures, exploratory code, and notes here. Other teammates should not edit these files.

The only file consumed by model building is `outputs/features.csv`. Start by changing `extract_features` in [features.py](../../Brandon%20Feature%20Engineering/features.py), then run from the repository root:

```bash
python "Brandon Feature Engineering/features.py"
estrus validate --owner Brandon
```

The starter's two features are examples, not your finished contribution. Replace them with features justified by your analysis; the starters are identical across owners, so exporting all of them unchanged adds duplicates. Add a description, units, rationale, missing-value handling, and any edge effects for each feature to the table below.

| Feature (without `brandon__`) | Meaning / units | Analysis / rationale | Missing values |
| --- | --- | --- | --- |
| cbt_p90 | 90th percentile CBT, °C | Starter example | pandas ignores missing readings |
| la_active_fraction | Fraction of observed minutes with activity > 0 | Starter example | NaN if no observed readings |

Use `iter_days(root)` to get the same 156 female mouse-days as everyone else. This excludes recording days 1 and 14. Each day has 1,440 minute bins. `day_index` is a join key only: never use it, cycle position, mouse identity, or labels as features. Do not fit normalization, PCA, feature selection, or other population transforms on all mice. Shared model pipelines fit those transforms within training folds.

Commit `outputs/features.csv` with the code that generated it; it is a small, versioned handoff artifact. Keep its column names stable between experiments or describe changes in your PR. Model runs read it but never modify it or execute this script. To withdraw your submission, remove that CSV in your own branch.

See the shared [feature contract](../FEATURE_CONTRACT.md), [collaboration guide](../COLLABORATION.md), and [methods](../METHODS.md). Everyone may use the same inputs; only write inside your own folder.
