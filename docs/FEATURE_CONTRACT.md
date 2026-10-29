# Feature handoff contract, version 2

Each owner supplies exactly one optional file:

Once any valid export is available, model building uses the combined valid contributor exports **without reference features**. If no valid exports exist, it falls back to the reference baseline. `estrus run --baseline` explicitly runs reference features alone for comparison. The report identifies which feature source was used.

| Owner | Path | Feature prefix |
| --- | --- | --- |
| Matthew | `Matthew Feature Engineering/outputs/features.csv` | `matthew__` |
| Vivian | `Vivian Feature Engineering/outputs/features.csv` | `vivian__` |
| Brandon | `Brandon Feature Engineering/outputs/features.csv` | `brandon__` |
| Alisha | `Alisha Feature Engineering/outputs/features.csv` | `alisha__` |

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

## Feature design constraints

The default input scope is the target day's signal, as used by the reference features. Long-period circadian/infradian estimates need more than one day; treat a one-day harmonic coefficient as a shape descriptor, not robust evidence of a rhythm.

**Matthew's explicitly requested retrospective exception:** `matthew__circadian_la_amplitude_next_day_delta` and `matthew__cbt_ultradian_amplitude_h0_12` use full-recording Morse transforms, including buffer and future samples. The first subtracts the current day's mean amplitude from the next day's for target days 2–12. Day 13's LA delta is missing to avoid the final buffer's endpoint-sensitive daily amplitude; keep that row and its other features. This leaves 143 observed LA deltas and 13 missing values, filled by training-fold median imputation. Day 14's raw readings still provide wavelet context. The row still targets one day, but a model accepting these inputs requires the complete recording at inference. It is not an isolated-day or online prediction task. Keep all recording context within the same mouse partition. See [Matthew's definitions](../Matthew%20Feature%20Engineering/README.md) for exact parameters, endpoint limitations, and gap handling. This exception does not silently change other contributors' feature definitions.

Within-day smoothing, interpolation, quantiles, or scaling are acceptable when the same rule works for one unseen day without labels. All transforms learned across days or mice (scaling, PCA, feature screening, thresholds learned from class distributions) normally belong in the shared training pipeline, where they are fitted within training folds. Matthew's two requested fractions freeze the exploratory notebook's development-selected thresholds (37.2 °C and 15 counts/minute). They are documented supervised feature-design choices, not thresholds freshly selected inside each model fold; subsequent development-validation scores must be described as exploratory. They were selected without the reserved test mice. Do not standardize each mouse against its full 14-day trajectory.

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

For a contributor-only model, compute its contributor features instead; baseline columns are not required. A model accepting Matthew's wavelet features requires a complete recording and his recording-level extractor, rather than this one-day example. The saved model requires the same columns used in training. An unavailable value can be NaN and will use the frozen imputer, but an entire missing schema is rejected. Do not fabricate missing contributor columns as NaNs to bypass this check; retrain on the available feature families instead.

## Label CSV (separate from features)

```csv
mouse_id,day_index,is_estrus,label_source
f1,2,1,vaginal_cytology_reviewed
f1,3,0,vaginal_cytology_reviewed
```

These are exactly the four allowed columns. Supply unique canonical keys and `0`/`1` targets with a nonempty source. A subset of rows is allowed; blank targets are unknown and excluded from training. Every grouped training/validation fold must still contain both classes. Do not change the meaning of the task to proestrus or another stage without agreeing on a revised target with the team.
