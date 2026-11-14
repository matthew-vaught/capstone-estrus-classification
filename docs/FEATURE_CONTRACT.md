# Feature handoff contract, version 2

Each owner supplies exactly one optional file:

The retained final configuration is [config/threshold-f2.json](../config/threshold-f2.json), using the original 28 supplied features and F2 cutoff tuning. Mouse Baseline and LA CBT Relationship are registered for historical experiment reproduction and excluded from the final model.

Once any valid export is available, model building uses the combined valid contributor exports **without reference features**. If no valid exports exist, it falls back to the reference baseline. `estrus run --baseline` explicitly runs reference features alone for comparison. The report identifies which feature source was used.

| Owner | Path | Feature prefix |
| --- | --- | --- |
| Matthew | `Matthew Feature Engineering/outputs/features.csv` | `matthew__` |
| Vivian | `Vivian Feature Engineering/outputs/features.csv` | `vivian__` |
| Brandon | `Brandon Feature Engineering/outputs/features.csv` | `brandon__` |
| Alisha | `Alisha Feature Engineering/outputs/features.csv` | `alisha__` |
| Mouse Baseline (excluded experiment) | `Mouse Baseline Feature Engineering/outputs/features.csv` | `mouse_baseline__` |
| LA CBT Relationship (excluded experiment) | `LA CBT Relationship Feature Engineering/outputs/features.csv` | `la_cbt_relationship__` |

By default the four original owners are eligible. An experiment may supply a nonempty, duplicate-free `feature_owners` list of registered names in its JSON configuration. Every explicitly requested export must be valid and present for a model run. [Mouse Baseline](features/mouse-baseline.md) is a separately registered experimental family enabled this way; its folder/export alone does not alter the default 28-feature comparison. Spaces in registered family names become underscores in feature prefixes. `estrus validate --owner "Mouse Baseline"` validates its handoff separately.

UTF-8 CSV, no index column. The column names are case-sensitive:

```csv
mouse_id,day_index,vivian__ur_power,vivian__plateau_minutes
f1,2,0.123,590
f1,3,0.456,370
```

The example is truncated. A valid file has **all 156 rows**: the Cartesian product of `f1` through `f13` and recording days `2` through `13`, once each. Row order does not matter. `day_index` is **1-based in the original 14-day CSV**, so day 2 consists of original data rows 1441–2880 (excluding the header), or Python slice `[1440:2880]`. Days 1 and 14 are buffers, not training examples.

`mouse_id` and `day_index` are keys only. Every other column must be a numeric feature, named `<owner>__<lowercase_name>`, with a letter first and only lowercase letters, digits, and underscores. No labels, metadata columns, class predictions, mouse identity, calendar-day indices, cycle day, or label-derived quantities are allowed. Name checks catch common mistakes, but cannot detect all semantic leakage: review your feature code.

Use blank/NaN values if a feature is unavailable for a day. Do not drop that row. Infinite values, text values, all-empty feature columns, duplicate headers, duplicate keys, extra or missing keys, and wrong namespaces reject the **whole contributor file**. Partial missing numeric values are imputed from training-fold medians. All-empty columns within a training fold are retained as zero before the variance filter. Constant features are accepted at export and removed inside training folds.

Complete keys ensure every valid contributor uses the same cohort. Missing measurements in individual features never remove a mouse-day or change cohort membership. Adding a valid contributor can still change the model and its scores. All original input files are read-only to the pipeline.

## Export from a notebook or custom script

Install the project first, then run anywhere inside the repository:

```python
import pandas as pd
from estrus.data import find_root, iter_days
from estrus.contracts import export_features

root = find_root()
rows = []
for mouse_id, day_index, day in iter_days(root):
    # day: 1440 rows, minute_of_day index, numeric cbt and la columns.
    # Replace this example with your own analysis-guided calculation.
    rows.append({
        "mouse_id": mouse_id,
        "day_index": day_index,
        "vivian__cbt_p90": day.cbt.quantile(.9),
    })
export_features(pd.DataFrame(rows), root, "Vivian")
```

The helper validates before replacing the CSV, then writes atomically. On failure, any previous export remains; fix the issue and rerun so you do not accidentally commit stale features. `estrus validate --owner Vivian` checks the on-disk artifact. Model runs read only CSV files, never import teammates' scripts, and never write to contributor folders.

## Optional input requirements

Keep feature-specific recording requirements and design notes in `input_requirements.json` at the top of your own feature engineering folder. The shared pipeline reads these notes as data and carries matching notes into the saved model, report, and run README. Feature calculations and helpers stay in your folder; shared code does not need to know their names or definitions.

The file is a JSON list of rules. Each rule has `features`, a nonempty list of fully prefixed feature names or wildcard patterns, and `note`, a nonempty string. A note applies when any model input matches one of its patterns. Patterns must use your own namespace; `*` can cover a family of features. For example:

```json
[
  {
    "features": ["vivian__example_*"],
    "note": "These example inputs require the complete recording."
  }
]
```

The file is optional. If present for a contributor whose features are used, malformed rules stop training with an error. Only matching notes are included; baseline runs ignore contributor notes. `--save-details` records the notes file's hash alongside the CSV and optional `outputs/feature_metadata.json`. Numeric model inputs still come exclusively from `outputs/features.csv`.

## Feature design constraints

The default input scope is the target day's signal, as used by the reference features. Long-period circadian/infradian estimates need more than one day; treat a one-day harmonic coefficient as a shape descriptor, not robust evidence of a rhythm.

**Matthew's retrospective recording features:** `matthew__circadian_la_amplitude_next_day_delta` and `matthew__cbt_ultradian_amplitude_h0_12` use full-recording Morse transforms, including buffer and future samples. The first subtracts the current day's mean amplitude from the next day's for target days 2–12. Day 13's LA delta is missing to avoid the final buffer's endpoint-sensitive daily amplitude; keep that row and its other features. This leaves 143 observed LA deltas and 13 missing values, filled by training-fold median imputation. Day 14's raw readings still provide wavelet context. The row still targets one day, but a model accepting these inputs requires the complete recording at inference. It is not an isolated-day or online prediction task. Keep all recording context within the same mouse partition. See [Matthew's definitions](features/matthew.md) for exact parameters, endpoint limitations, and gap handling. Alisha and Vivian also submit recording-level features under their own documented definitions; see below.

[Alisha's DTW features](features/alisha.md) compare a target day with the other thirteen days of the same mouse. [Vivian's features](features/vivian.md) use full-recording cleaning, activity adjustment, and wavelets. Both are retrospective. Their `input_requirements.json` files carry those requirements into model outputs. No contributor's recording context may cross mouse partitions.

[Mouse Baseline's four contrasts](features/mouse-baseline.md) also declare retrospective scope: they compare established per-day summaries with the same mouse's other analysis days, without stage labels or cross-mouse aggregation. They reuse Matthew's unchanged Morse helper during explicit extraction; shared model fitting still reads only their independent CSV/JSON handoff.

[LA CBT Relationship](features/la-cbt-relationship.md) uses only the target day's complete paired signals, including within-day ten-minute forward changes. It does not require other days/mice or labels. It supports end-of-day description, while a combined model still requires the original recording-level features. It is an independent CSV/JSON family and does not implicitly enable Mouse Baseline.

Within-day smoothing, interpolation, quantiles, or scaling are acceptable when the same rule works for one unseen day without labels. All transforms learned across days or mice (scaling, PCA, feature screening, thresholds learned from class distributions) normally belong in the shared training pipeline, where they are fitted within training folds. Matthew's two requested fractions freeze the exploratory notebook's development-selected thresholds (37.2 °C and 15 counts/minute). They are documented supervised feature-design choices, not thresholds freshly selected inside each model fold; subsequent development-validation scores must be described as exploratory. They were selected without the reserved test mice. Do not introduce full-trajectory centering into day-local exports. Recording-level preprocessing must be explicitly documented, as in Vivian's uncentered activity-adjusted export; her exploratory classifier's centering is not used in the shared model.

There are no clock timestamps in these files. The paper's lights-on/off schedule does not establish which clock time row zero represents. Until that is confirmed, use first/second half or relative phase names instead of calling them light/dark features.

## Predict a new day with the reference baseline

For a model trained with no contributor exports:

```python
from pathlib import Path
import pandas as pd
from estrus.features import extract_day
from estrus.modeling import predict

# new_day.csv has exactly 1440 rows and cbt/la columns in recording-day order.
day = pd.read_csv("new_day.csv")
assert len(day) == 1440
features = {"baseline__" + k: v for k, v in extract_day(day).items()}
row = pd.DataFrame([{"mouse_id": "new_mouse", "day_index": 1, **features}])
print(predict(Path("Model Building/results/RUN/model.joblib"), row))
```

For a contributor-only model, compute its contributor features instead; baseline columns are not required. Models accepting the current Matthew, Alisha, or Vivian recording-level inputs require their documented complete-recording extraction instead of this one-day example. The saved model requires the same columns used in training. An unavailable value can be NaN and will use the frozen imputer, but an entire missing schema is rejected. Do not fabricate missing contributor columns as NaNs to bypass this check; retrain on the available feature families instead.

## Label CSV (separate from features)

```csv
mouse_id,day_index,is_estrus,label_source
f1,2,1,vaginal_cytology_reviewed
f1,3,0,vaginal_cytology_reviewed
```

These are exactly the four allowed columns. Supply unique canonical keys and `0`/`1` targets with a nonempty source. A subset of rows is allowed; blank targets are unknown and excluded from training. Every grouped training/validation fold must still contain both classes. Do not change the meaning of the task to proestrus or another stage without agreeing on a revised target with the team.
