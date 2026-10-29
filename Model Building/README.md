# Model building

Run from the repository root:

```bash
estrus run --quick  # Faster trial run
estrus run          # Full evaluation
```

The pipeline combines valid exports from whichever teammates have finished and uses **only their features**. Reference features are excluded whenever at least one valid export exists. Missing or invalid exports are skipped with feedback. If no valid exports exist, it falls back to the reference baseline.

Matthew's current four features include full-recording Morse amplitudes and a next-day LA comparison. Models accepting these inputs require the complete recording for retrospective classification. Day 13's LA delta is missing to avoid the final buffer's endpoint-sensitive amplitude. All 156 rows and the other three features are retained; missing LA deltas use medians learned only from fitting data. His two thresholds were frozen after development exploration; development-validation scores remain exploratory. Details: [Matthew's README](../Matthew%20Feature%20Engineering/README.md).

For example, Matthew's four exported features give four available features. Adding Vivian's three gives seven. Feature selection can still choose a smaller subset.

To run the reference baseline explicitly, even after the team has features:

```bash
estrus run --baseline --output "Model Building/results/reference-comparison"
```

Compare it with a normal team run using the same labels, configuration, and quick/full setting. The mouse split stays the same. The existing `final-baseline/` run remains unchanged, and each new run gets its own folder.

The workflow is: **compare models and feature sets → choose the best validation AP → fit that combination → test it on reserved mice.** It uses 10 mice for training/validation and reserves 3 for the final test. There is one chosen model and one exact selected feature list.

Each run creates a folder inside `results/` containing just four files:

| File | What to do with it |
| --- | --- |
| **`report.html`** | **Start here.** See the chosen model, score, feature rankings by person, features used in the final model, and expandable test-day plots. You can share this one file. |
| `predictions.csv` | Open in Excel or another spreadsheet. Each row gives the mouse, day, actual class, predicted class, probability of estrus, and confidence. |
| `model.joblib` | The saved trained model, for reuse with Python or `estrus predict`. You do not need to open it to review results. |
| `README.md` | A short guide to that particular run. |

Probabilities in the spreadsheet use 0–1: `0.8` means 80%. Confidence is the probability assigned to the predicted class. The report shows percentages and spells out **Estrus** and **Non-estrus**.

Each expanded day has activity and temperature **side by side**. Colored traces show that mouse; the black trace is the average female profile for the same cycle day. It averages three cycles within each mouse, then averages all 13 females, including test mice, for visual comparison only. Cycle day 1 matches recording days 2, 6, and 10. Both main traces use 15-minute display averages.

**Average precision is the metric used to compare and choose models.** It measures how well estrus days rank near the top of the model's scores. Higher is better; 1 is perfect. It is not a percentage of correct predictions. The report also gives simple counts of correctly classified estrus and non-estrus days.

The report compares all usable features against the top 35% and top 70%. Its feature section lists every contributor's features, how predictive each is on its own, its contribution to the chosen model, and whether the final model uses it. These assessments use training/validation mice only.

The current reference result is [final-baseline/report.html](results/final-baseline/report.html). Model-comparison scores are **validation scores used to choose** the winner. The main score is the **winner's result on reserved test mice**, so those numbers can differ.

For deeper analysis or debugging, explicitly keep the technical files:

```bash
estrus run --save-details
```

That adds a `details/` folder containing the feature summary CSV, full model comparisons, exact split and model settings, input records, and individual day plots. `--labels /path/to/labels.csv` replaces the provisional labels. Settings live in [config.json](config.json); full methods are in [docs/METHODS.md](../docs/METHODS.md).

Every test mouse stays out of training, feature selection, calibration, and feature assessment. The saved classifier is the same one shown in the report. Recording days 2, 6, and 10 remain provisional estrus labels.
