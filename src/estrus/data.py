"""Read original CSVs without modifying them; use explicit recording-day keys."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

MINUTES_PER_DAY = 1440
ANALYSIS_DAYS = tuple(range(2, 14))
MICE = tuple(f"f{i}" for i in range(1, 14))
KEYS = ["mouse_id", "day_index"]
PROXY_SOURCE = "paper_alignment_proxy_days_2_6_10_UNVERIFIED"


def find_root(start: Path | None = None) -> Path:
    """Locate a checkout by its package metadata and retained female input."""
    start = (start or Path.cwd()).resolve()
    for path in (start, *start.parents):
        if (path / "data/inputs/fem_temp.csv").exists() and (path / "pyproject.toml").exists():
            return path
    raise FileNotFoundError("Run inside the repository, or pass --root /path/to/repo.")


def load_signals(root: Path) -> dict[str, pd.DataFrame]:
    """Read female CBT/LA recordings with fixed shape and numeric validation."""
    result = {}
    for name, filename in [("cbt", "fem_temp.csv"), ("la", "fem_act.csv")]:
        frame = pd.read_csv(root / "data/inputs" / filename, encoding="utf-8-sig")
        if list(frame.columns) != list(MICE) or frame.shape != (20160, 13):
            raise ValueError(f"{filename}: expected 20160 minute rows and columns f1..f13; got {frame.shape}.")
        frame = frame.apply(pd.to_numeric, errors="raise").astype(float)
        if np.isinf(frame.to_numpy()).any():
            raise ValueError(f"{filename}: infinite measurements are invalid.")
        result[name] = frame
    return result


def canonical_keys() -> pd.DataFrame:
    """Return the 156 permitted female mouse-day keys in stable order."""
    return pd.MultiIndex.from_product([MICE, ANALYSIS_DAYS], names=KEYS).to_frame(index=False)


def iter_days(root: Path):
    """Yield (mouse_id, 1-based recording day, 1440-row CBT/LA dataframe).

    No clipping or population normalization; raw missing values are preserved.
    Row zero of each returned day is minute zero of that recording-day segment.
    """
    signals = load_signals(root)
    for mouse in MICE:
        for day in ANALYSIS_DAYS:
            start = (day - 1) * MINUTES_PER_DAY
            yield mouse, day, pd.DataFrame({
                name: frame[mouse].iloc[start:start + MINUTES_PER_DAY].to_numpy()
                for name, frame in signals.items()
            }).rename_axis("minute_of_day")


def proxy_labels() -> pd.DataFrame:
    """Label assumed paper-aligned days; these are not independent stage labels."""
    frame = canonical_keys()
    frame["is_estrus"] = frame.day_index.isin([2, 6, 10]).astype(int)
    frame["label_source"] = PROXY_SOURCE
    return frame


def load_labels(path: Path | None = None) -> pd.DataFrame:
    """Load validated custom labels, or return the explicit provisional proxy."""
    if path is None:
        return proxy_labels()
    frame = pd.read_csv(path)
    required = set(KEYS + ["is_estrus", "label_source"])
    if set(frame.columns) != required:
        raise ValueError(f"Labels require exactly {sorted(required)}.")
    if frame.duplicated(KEYS).any() or frame[KEYS].isna().any().any():
        raise ValueError("Labels contain duplicate or missing mouse-day keys.")
    if not frame.mouse_id.isin(MICE).all() or not frame.day_index.isin(ANALYSIS_DAYS).all():
        raise ValueError("Labels must use female IDs f1..f13 and recording days 2..13.")
    if frame.label_source.isna().any() or frame.label_source.astype(str).str.strip().eq("").any():
        raise ValueError("Every label needs a nonempty label_source.")
    frame["label_source"] = frame.label_source.astype(str).str.strip()
    # Blank labels mean unknown and are excluded from supervised evaluation.
    if not frame.is_estrus.dropna().isin([0, 1]).all():
        raise ValueError("is_estrus must be 0, 1, or blank for unknown.")
    return frame


def sha256(path: Path) -> str:
    """Hash a file in chunks for input and source provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(root: Path, output: Path | None = None) -> Path:
    """Write reproducible tables and label templates without changing raw inputs.

    ``output`` can isolate build-script intermediates from other local analysis.
    Existing generated tables at that destination are replaced.
    """
    output = output if output is not None else root / "data/outputs"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for mouse, day, signal in iter_days(root):
        block = signal.reset_index()
        block["mouse_id"], block["day_index"] = mouse, day
        rows.append(block[KEYS + ["minute_of_day", "cbt", "la"]])
    pd.concat(rows, ignore_index=True).to_csv(output / "female_minutes.csv", index=False)
    canonical_keys().to_csv(output / "mouse_days.csv", index=False)
    proxy_labels().to_csv(output / "labels.paper_proxy.csv", index=False)
    template = canonical_keys()
    template["is_estrus"], template["label_source"] = np.nan, ""
    template.to_csv(output / "labels.template.csv", index=False)
    return output
