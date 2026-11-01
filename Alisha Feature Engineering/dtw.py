"""Within-mouse DTW time shifts between recording days, cached as 14 x 14 matrices.

DTW matches MATLAB's default dtw for scalar series: L1 cost, no warping window.
From the optimal alignment path we keep the mean time offset between the two
days. Each mouse is compared only with itself.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit, prange

from estrus.data import MINUTES_PER_DAY, sha256

DAYS = 14
SEGMENT_MINUTES = 180
N_SEGMENTS = MINUTES_PER_DAY // SEGMENT_MINUTES
# Scope 0 is the whole day; scopes 1-8 are hours [0,3), [3,6), ... [21,24).
SCOPES = [(0, MINUTES_PER_DAY)] + [(s * SEGMENT_MINUTES, (s + 1) * SEGMENT_MINUTES)
                                   for s in range(N_SEGMENTS)]
INPUTS = {"female": ("fem_temp.csv", "fem_act.csv"), "male": ("male_temp.csv", "male_act.csv")}
SIGNALS = ("temp", "act")
CACHE_DIR = Path(__file__).resolve().parent / "outputs" / "cache"


@njit(cache=True)
def dtw_shift(a, b):
    """Mean (j - i) along the optimal DTW path, in samples.

    Cost D[i,j] = |a_i - b_j| + min(D[i-1,j-1], D[i-1,j], D[i,j-1]). A positive
    shift means a's pattern occurs earlier than b's: a[i] is matched to b[j]
    later in time. Needs the full cost matrix to backtrack.
    """
    n, m = a.size, b.size
    D = np.empty((n, m))
    for i in range(n):
        for j in range(m):
            cost = abs(a[i] - b[j])
            if i == 0 and j == 0:
                D[i, j] = cost
            elif i == 0:
                D[i, j] = cost + D[i, j - 1]
            elif j == 0:
                D[i, j] = cost + D[i - 1, j]
            else:
                D[i, j] = cost + min(D[i - 1, j - 1], D[i - 1, j], D[i, j - 1])
    i, j = n - 1, m - 1
    total, steps = 0.0, 0
    while True:
        total += j - i
        steps += 1
        if i == 0 and j == 0:
            break
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            diagonal, up, left = D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]
            if diagonal <= up and diagonal <= left:
                i -= 1
                j -= 1
            elif up <= left:
                i -= 1
            else:
                j -= 1
    return total / steps


@njit(parallel=True, cache=True)
def _pair_shifts(days, starts, stops, jobs):
    """days: (mice, 14, 1440). jobs rows: mouse, scope, day a, day b."""
    out = np.empty(jobs.shape[0])
    for k in prange(jobs.shape[0]):
        mouse, scope, a, b = jobs[k]
        lo, hi = starts[scope], stops[scope]
        out[k] = dtw_shift(days[mouse, a, lo:hi], days[mouse, b, lo:hi])
    return out


def load_recordings(root: Path, sex: str) -> dict[str, pd.DataFrame]:
    """Full 14-day recordings (20160 minutes x 13 mice) for one sex."""
    result = {}
    for signal, filename in zip(SIGNALS, INPUTS[sex]):
        frame = pd.read_csv(root / "data/inputs" / filename, encoding="utf-8-sig").astype(float)
        values = frame.to_numpy()
        if frame.shape != (DAYS * MINUTES_PER_DAY, 13) or not np.isfinite(values).all():
            raise ValueError(f"{filename}: expected 20160 x 13 finite readings; DTW cannot skip gaps")
        result[signal] = frame
    return result


def clean(frame: pd.DataFrame, signal: str) -> pd.DataFrame:
    """Smarr & Kriegsfeld (2022) cleaning, per mouse over its full recording.

    CBT below 35 is set to 35; values beyond 3 SD of the mouse mean are clipped
    to that limit (activity: high side only).
    """
    frame = frame.clip(lower=35.0) if signal == "temp" else frame.copy()
    mean, sd = frame.mean(), frame.std()
    upper = mean + 3 * sd
    lower = mean - 3 * sd if signal == "temp" else None
    return frame.clip(lower=lower, upper=upper, axis=1)


def compute(frame: pd.DataFrame) -> np.ndarray:
    """(mice, 9 scopes, 14, 14) shifts in minutes for one signal of one sex.

    shifts[.., a, b] > 0 when day a runs earlier than day b; antisymmetric.
    """
    days = frame.to_numpy().T.reshape(frame.shape[1], DAYS, MINUTES_PER_DAY).copy()
    mice = days.shape[0]
    starts = np.array([lo for lo, _ in SCOPES])
    stops = np.array([hi for _, hi in SCOPES])
    pairs = [(a, b) for a in range(DAYS) for b in range(a + 1, DAYS)]
    jobs = np.array([(m, s, a, b) for m in range(mice) for s in range(len(SCOPES)) for a, b in pairs])
    flat = _pair_shifts(days, starts, stops, jobs)
    shifts = np.zeros((mice, len(SCOPES), DAYS, DAYS))
    m, s, a, b = jobs.T
    shifts[m, s, a, b], shifts[m, s, b, a] = flat, -flat
    return shifts


def load_or_compute(root: Path, sex: str, cleaned: bool) -> dict[str, np.ndarray]:
    """Return {signal: shifts}, reusing the cache while the inputs are unchanged."""
    path = CACHE_DIR / f"shifts_{sex}_{'clean' if cleaned else 'raw'}.npz"
    hashes = np.array([sha256(root / "data/inputs" / name) for name in INPUTS[sex]])
    if path.exists():
        with np.load(path) as stored:
            if np.array_equal(stored["input_sha256"], hashes):
                return {signal: stored[signal] for signal in SIGNALS}
    recordings = load_recordings(root, sex)
    result = {signal: compute(clean(frame, signal) if cleaned else frame)
              for signal, frame in recordings.items()}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(path, input_sha256=hashes, **result)
    return result
