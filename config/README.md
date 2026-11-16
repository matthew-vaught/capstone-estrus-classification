# Final and historical configurations

The final setup, adopted November 15, 2026, is [mouse-relative-fixed-cutoff.json](mouse-relative-fixed-cutoff.json): original contributor features plus mouse-relative copies, with a development-only F2 cutoff selected one mouse at a time using one fixed model. Run:

```bash
python run.py model --config config/mouse-relative-fixed-cutoff.json --save-details
```

| Configuration | Status |
| --- | --- |
| [mouse-relative-fixed-cutoff.json](mouse-relative-fixed-cutoff.json) | **Final choice:** original 28 plus mouse-relative copies, F2 cutoff from one-mouse-at-a-time folds refitting one fixed model, no calibration. 148/156 on all mice, 35/36 (97.2%) on test mice |
| [threshold-f2.json](threshold-f2.json) | Previous final choice (November 13–15): original 28 features, grouped-fold F2 cutoff with calibration. 145/156 on all mice, 34/36 (94.4%) on test mice |
| [Model Building/config.json](../Model%20Building/config.json) | Historical fixed-0.5 setup; selected when `--config` is omitted |
| [mouse-baseline-f2.json](mouse-baseline-f2.json) | Excluded from final model; retained to reproduce the Mouse Baseline experiment |
| [la-cbt-relationship-f2.json](la-cbt-relationship-f2.json) | Excluded from final model; retained to reproduce the LA–CBT Relationship experiment |
| [mouse-relative-f2.json](mouse-relative-f2.json) | Excluded from final model; original 28 plus mouse-relative copies, F2 cutoff ([experiment](../docs/research/mouse-relative-2026-11-15.md)) |
| [mouse-relative-accuracy.json](mouse-relative-accuracy.json) | Excluded from final model; mouse-relative copies with plain-accuracy cutoff |
| [threshold-accuracy.json](threshold-accuracy.json) | Excluded from final model; original 28 with plain-accuracy cutoff (not recommended) |
| [mouse-relative-lomo-cutoff.json](mouse-relative-lomo-cutoff.json) | Excluded from final model; mouse-relative copies, F2 cutoff from leave-one-mouse-out folds, no calibration (tied the previous final model's test accuracy) |
| [threshold-lomo-cutoff.json](threshold-lomo-cutoff.json) | Excluded from final model; original 28 with the same cutoff protocol |
| [threshold-fixed-cutoff.json](threshold-fixed-cutoff.json) | Control: original 28 with the same fixed-model cutoff; tied the previous final model on all mice |

The final configuration retains the full model search for the final model; the cutoff folds reuse that choice. See the [cutoff-selection protocol](../docs/THRESHOLD_TUNING.md) for mouse grouping, calibration, comparisons, and limitations. Its recorded cutoff of 0.505732 is a learned result, not a hard-coded configuration value.

[Mouse Baseline definitions](../docs/features/mouse-baseline.md) and [LA–CBT definitions](../docs/features/la-cbt-relationship.md) document the excluded experiments. Their explicit `feature_owners` lists enable them only for reproduction; missing or invalid requested exports stop those experiments. Generating an experimental CSV alone does not include it in the final model.

For further research, copy a configuration under a descriptive name and pass its path explicitly. Keep labels and feature definitions explicit when comparing runs; see [supported settings and quick-mode overrides](../docs/REPRODUCING.md#model-configuration-and-variants).
