"""Inspect boundary and buffer sensitivity without changing the model export.

Run: python "Matthew Feature Engineering/check_wavelet_sensitivity.py"
Uses no labels and does not change the requested periodic feature definition.
"""
import numpy as np
import pandas as pd

from estrus.data import find_root, load_signals
from features import FEATURE_NAMES, extract_recording_features

RAW_DELTA = "circadian_la_next_day_delta_untrimmed"


def main():
    root = find_root()
    signals = load_signals(root)
    rows = []
    for mouse in signals["la"].columns:
        la = signals["la"][mouse].to_numpy()
        cbt = signals["cbt"][mouse].to_numpy()
        periodic = extract_recording_features(la, cbt)
        reflected = extract_recording_features(la, cbt, boundary="reflect")
        # Intentionally remove real buffers to measure their effect, not as a
        # substitute definition. The last shortened day has no next-day value.
        no_buffers = extract_recording_features(la[1440:-1440], cbt[1440:-1440])
        # Audit untrimmed estimates: the production export excludes day 13's
        # delta precisely because of the boundary sensitivity measured here.
        delta = periodic.iloc[1:13][RAW_DELTA].to_numpy()
        reflect_delta = reflected.iloc[1:13][RAW_DELTA].to_numpy()
        rows.append({
            "mouse_id": mouse,
            "last_day_LA_delta_periodic": delta[-1],
            "last_day_LA_delta_reflect": reflect_delta[-1],
            "max_LA_delta_boundary_change": np.max(np.abs(delta - reflect_delta)),
            "max_LA_delta_without_buffers_change": np.max(np.abs(
                delta[:11] - no_buffers.iloc[:11][RAW_DELTA].to_numpy())),
            "max_CBT_UR_boundary_change": np.max(np.abs(
                periodic.iloc[1:13][FEATURE_NAMES[1]].to_numpy()
                - reflected.iloc[1:13][FEATURE_NAMES[1]].to_numpy())),
        })
    result = pd.DataFrame(rows)
    output = root / "Matthew Feature Engineering/outputs/wavelet_sensitivity.csv"
    output.parent.mkdir(exist_ok=True)
    result.to_csv(output, index=False)
    changes = (np.sign(result.last_day_LA_delta_periodic)
               != np.sign(result.last_day_LA_delta_reflect)).sum()
    print(f"Day 13 LA delta changes sign for {changes}/{len(result)} mice under reflected boundaries.")
    print("These untrimmed day 13 estimates are excluded from the model feature export.")
    print(f"Saved {output}; model features were not changed.")


if __name__ == "__main__":
    main()
