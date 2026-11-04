"""Build project stages after installing the package; see docs/REPRODUCING.md."""
from pathlib import Path

from estrus.build import main


if __name__ == "__main__":
    raise SystemExit(main(root=Path(__file__).resolve().parent))
