"""Brandon's starter. Replace extract_features with your own day-local features.

Run from the repository root:
    python "Brandon Feature Engineering/features.py"
This intentionally small example is opt-in; it is not imported by model training.
"""
from estrus.contracts import export_features
from estrus.data import find_root, iter_days
import pandas as pd

OWNER = "Brandon"


def extract_features(day):
    # day has 1440 rows and cbt/la columns, with minute_of_day as its index.
    # Return unprefixed numeric feature names. Do not use labels or day number.
    return {
        "cbt_p90": float(day.cbt.quantile(.9)),
        "la_active_fraction": float((day.la.dropna() > 0).mean()),
    }


def main():
    root = find_root()
    records = []
    for mouse, day_index, signal in iter_days(root):
        values = extract_features(signal)
        records.append({
            "mouse_id": mouse, "day_index": day_index,
            **{OWNER.lower() + "__" + name: value for name, value in values.items()},
        })
    path = export_features(pd.DataFrame(records), root, OWNER)
    print(f"Validated and exported {path}")


if __name__ == "__main__":
    main()
