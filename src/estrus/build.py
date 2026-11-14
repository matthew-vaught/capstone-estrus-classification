"""Coordinate reproducible stages without owning contributors' extraction logic."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from .cli import main as estrus_main
from .data import find_root, prepare, sha256
from .features import assemble_features
from .contracts import resolve_owners


def verify_inputs(root: Path) -> None:
    """Check the four retained classroom CSVs against the submitted inventory."""
    manifest = json.loads((root / "docs/references/input_manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        if sha256(root / name) != expected:
            raise ValueError(f"Input checksum differs: {name}. Preserve the supplied recordings.")


def regenerate(root: Path, owners: list[str]) -> None:
    """Execute only explicitly selected, established script-based extractors.

    Vivian's notebook remains her regeneration interface; Brandon's script is
    still a starter. Neither is offered as an automated regeneration target.
    """
    if "Alisha" in owners and importlib.util.find_spec("numba") is None:
        raise ValueError("Alisha's extractor needs numba. Install the optional extraction dependencies first; see docs/REPRODUCING.md.")
    for owner in dict.fromkeys(owners):
        subprocess.run(
            [sys.executable, str(root / f"{owner} Feature Engineering/features.py")],
            cwd=root, check=True,
        )


def clean(root: Path) -> None:
    """Remove only this build script's scratch directory, preserving reports."""
    scratch = root / "data/outputs/build"
    if scratch.is_symlink() or not scratch.resolve().is_relative_to(root.resolve()):
        raise ValueError("Refusing to clean a build directory outside the repository.")
    if scratch.exists():
        shutil.rmtree(scratch)
    print(f"Cleaned {scratch}; contributor files and Model Building/results are preserved.")


def main(argv=None, *, root: Path | None = None) -> int:
    """Dispatch build targets; return nonzero before modeling invalid exports."""
    parser = argparse.ArgumentParser(description="Build the estrus-classification project")
    parser.add_argument("targets", nargs="+", choices=["data", "features", "validate", "model", "all", "test", "clean"])
    parser.add_argument("--quick", action="store_true", help="Reduced model search for a trial run")
    parser.add_argument("--baseline", action="store_true", help="Use reference features alone")
    parser.add_argument("--config", type=Path, help="Alternate model JSON configuration")
    parser.add_argument("--labels", type=Path, help="Alternate curated labels CSV")
    parser.add_argument("--output", type=Path, help="New/empty model or synthetic-report directory")
    parser.add_argument("--save-details", action="store_true", help="Retain complete run provenance")
    parser.add_argument("--regenerate", nargs="+", choices=["Matthew", "Alisha", "Mouse Baseline", "LA CBT Relationship"], help="Explicitly rerun these owners' extractors during features/all")
    args = parser.parse_args(argv)
    if args.regenerate and not {"features", "all"}.intersection(args.targets):
        parser.error("--regenerate requires features or all")
    if args.regenerate and args.baseline:
        parser.error("--regenerate cannot be combined with --baseline")
    if "test" in args.targets and (len(args.targets) != 1 or args.regenerate or args.labels or args.config or args.baseline or args.quick):
        parser.error("test uses its own synthetic configuration; run it separately, optionally with --output")
    if args.output and not {"model", "all", "test"}.intersection(args.targets):
        parser.error("--output requires model, all, or test")
    try:
        root = root.resolve() if root is not None else find_root()
        scratch = root / "data/outputs/build"
        stages = []
        for target in args.targets:
            stages.extend(["data", "features", "model"] if target == "all" else [target])
        for target in dict.fromkeys(stages):
            print(f"Build stage: {target}", flush=True)
            if target == "clean":
                clean(root)
            elif target == "test":
                from .synthetic import smoke_test

                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                destination = args.output or scratch / f"synthetic-{stamp}"
                smoke_test(root, destination)
            elif target == "data":
                verify_inputs(root)
                print(f"Prepared {prepare(root, scratch / 'prepared')}")
            elif target == "features":
                if args.regenerate:
                    regenerate(root, args.regenerate)
                config = json.loads(args.config.read_text()) if args.config else {}
                owners = resolve_owners(config.get("feature_owners"))
                features, diagnostics = assemble_features(root, scratch, baseline_only=args.baseline, owners=owners)
                if any(item["status"] == "invalid" for item in diagnostics):
                    raise ValueError("Invalid feature exports; inspect data/outputs/build/feature_validation.json.")
                if "feature_owners" in config and not args.baseline and any(item["status"] != "accepted" for item in diagnostics):
                    raise ValueError("Every explicitly configured feature owner needs a valid export.")
                features.to_csv(scratch / "features.csv", index=False)
                print(f"Assembled {len(features)} rows and {len(features.columns) - 2} features at {scratch / 'features.csv'}")
            elif target == "validate":
                status = estrus_main(["--root", str(root), "validate"])
                if status:
                    return status
            elif target == "model":
                # The build workflow stops on invalid exports. The lower-level
                # estrus CLI retains its documented skip-invalid behavior.
                if not args.baseline:
                    status = estrus_main(["--root", str(root), "validate"])
                    if status:
                        return status
                command = ["--root", str(root), "run"]
                for flag in ["quick", "baseline", "save_details"]:
                    if getattr(args, flag):
                        command.append("--" + flag.replace("_", "-"))
                for option in ["config", "labels", "output"]:
                    if getattr(args, option) is not None:
                        command.extend(["--" + option, str(getattr(args, option))])
                status = estrus_main(command)
                if status:
                    return status
        return 0
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
