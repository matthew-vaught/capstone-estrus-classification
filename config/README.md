# Experiment configurations

The maintained default is [Model Building/config.json](../Model%20Building/config.json). Copy it here under a descriptive experiment name, change the intended parameters, and run:

```bash
python run.py model --config config/EXPERIMENT.json --save-details
```

Keep labels and feature definitions explicit when comparing experiments. See the [reproduction guide](../docs/REPRODUCING.md#model-configuration-and-variants) for supported settings and quick-mode overrides.

[threshold-f2.json](threshold-f2.json) uses the maintained full search and adds development-only decision-cutoff selection by F2. The default configuration still uses 0.5. See the [experiment protocol](../docs/THRESHOLD_TUNING.md) for mouse grouping, calibration, comparisons, and limitations.
