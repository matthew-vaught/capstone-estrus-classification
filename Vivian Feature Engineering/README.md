# Vivian Feature Engineering

Vivian owns everything inside this folder. Put notebooks, figures, exploratory code, and notes here. Other teammates should not edit these files.

The only file consumed by model building is `outputs/features.csv`. Start by changing `extract_features` in [features.py](features.py), then run from the repository root:

```bash
python "Vivian Feature Engineering/features.py"
estrus validate --owner Vivian
```

The starter's two features are examples, not your finished contribution. Replace them with features justified by your analysis; the starters are identical across owners, so exporting all of them unchanged adds duplicates. Add a description, units, rationale, missing-value handling, and any edge effects for each feature to the table below.

| Feature (without `vivian__`) | Meaning / units | Analysis / rationale | Missing values |
| --- | --- | --- | --- |
| cbt_p90 | 90th percentile CBT, °C | Starter example | pandas ignores missing readings |
| la_active_fraction | Fraction of observed minutes with activity > 0 | Starter example | NaN if no observed readings |

Use `iter_days(root)` to get the same 156 female mouse-days as everyone else. This excludes recording days 1 and 14. Each day has 1,440 minute bins. `day_index` is a join key only: never use it, cycle position, mouse identity, or labels as features. Do not fit normalization, PCA, feature selection, or other population transforms on all mice. Shared model pipelines fit those transforms within training folds.

Commit `outputs/features.csv` with the code that generated it; it is a small, versioned handoff artifact. Keep its column names stable between experiments or describe changes in your PR. Model runs read it but never modify it or execute this script. To withdraw your submission, remove that CSV in your own branch.

See the shared [feature contract](../docs/FEATURE_CONTRACT.md), [collaboration guide](../CONTRIBUTING.md), and [methods](../docs/METHODS.md). Everyone may use the same inputs; only write inside your own folder.
