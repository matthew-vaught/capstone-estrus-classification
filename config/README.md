# Final and historical configurations

The retained final setup is [threshold-f2.json](threshold-f2.json): original contributor features with development-only F2 cutoff selection. Run:

```bash
python run.py model --config config/threshold-f2.json --save-details
```

| Configuration | Status |
| --- | --- |
| [threshold-f2.json](threshold-f2.json) | **Final choice:** original 28 supplied features, F2 cutoff tuning; both experimental families excluded |
| [Model Building/config.json](../Model%20Building/config.json) | Historical fixed-0.5 setup; selected when `--config` is omitted |
| [mouse-baseline-f2.json](mouse-baseline-f2.json) | Excluded from final model; retained to reproduce the Mouse Baseline experiment |
| [la-cbt-relationship-f2.json](la-cbt-relationship-f2.json) | Excluded from final model; retained to reproduce the LA–CBT Relationship experiment |

The final configuration retains the full model search. See the [cutoff-selection protocol](../docs/THRESHOLD_TUNING.md) for mouse grouping, calibration, comparisons, and limitations. Its recorded cutoff of 0.367183 is a learned result, not a hard-coded configuration value.

[Mouse Baseline definitions](../docs/features/mouse-baseline.md) and [LA–CBT definitions](../docs/features/la-cbt-relationship.md) document the excluded experiments. Their explicit `feature_owners` lists enable them only for reproduction; missing or invalid requested exports stop those experiments. Generating an experimental CSV alone does not include it in the final model.

For further research, copy a configuration under a descriptive name and pass its path explicitly. Keep labels and feature definitions explicit when comparing runs; see [supported settings and quick-mode overrides](../docs/REPRODUCING.md#model-configuration-and-variants).
