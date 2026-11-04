# Results and presentation milestone

## Verified presentation result

The full build `presentation-2026-11-03` reproduced the following result using the retained input recordings and unchanged submitted feature CSVs:

| Item | Recorded value |
| --- | --- |
| Available features | 28: Matthew 4, Alisha 18, Vivian 6 |
| Chosen classifier | Logistic regression |
| Selected feature set | Top 35%; 10 features |
| Development-validation average precision | 0.992, rounded |
| Reserved-test average precision | 0.932, rounded |
| Test cohort | 36 days from 3 mice |
| Counts at probability threshold 0.5 | 5/9 estrus-proxy days detected; 27/27 other days correctly classified |

The run used `--save-details` and retained full configuration, source/input hashes, splits, feature assessments, and predictions locally. A small [presentation record](results/presentation-2026-11-03.json) is versioned here, including exact scores, selected features, software versions, and hashes for the report and predictions. The held-out mice were f3, f6, and f11. The working tree contained this repository cleanup; the record explicitly identifies that state.

The reproduced test AP is 0.9320987654320989 and matches the earlier local three-contributor result when rounded to 0.932. This is a software reproduction on the same dataset and split, rather than independent biological validation.

## Reproducing

After installing the project, run:

```bash
python run.py all --save-details
```

Open the printed `Model Building/results/run-.../report.html` path. The default configuration is seed 190, three held-out mice, three development-validation folds, and 100 forest trees. The present submissions are the 28-feature combination above. Regenerating features or changing configuration may change the result; a reproduced score should be identified with that run's retained provenance.

For a reference-only comparison:

```bash
python run.py model --baseline --save-details
```

Compare baseline and team runs using the same labels, seed, configuration, and quick/full setting. Each run independently selects its winning model and feature subset. `--quick` is useful for checking the workflow and is a different experiment from a full run.

Generated reports are local outputs ignored by Git. Documentation intentionally does not link to local-only HTML files that disappear in a fresh checkout. Submit the chosen HTML report with its run folder as a course attachment or release artifact; the HTML embeds its images. No artifact has been published automatically. The [modeling guide](MODELING.md#output-files) explains the other files.

## Interpretation and limitations

The default labels identify recording days 2, 6, and 10 as estrus based on assumed paper alignment. Independent biological staging and clock-time alignment remain unconfirmed. Current results describe recognition of that proxy pattern.

All currently submitted feature families use complete recordings, including later measurements. Results support retrospective classification and do not establish online prediction performance. Only three mice contribute to the test estimate. Development exploration and prior inspection of this dataset further limit claims of independent generalization.

Contributor-specific exploratory classifiers may use other preprocessing, splits, and metrics. Their scores should remain attributed to those analyses and should not be presented as interchangeable with the shared model's held-out result. Feature definitions and provenance are indexed in the [feature documentation](README.md#feature-documentation); full evaluation details are in [methods](METHODS.md).
