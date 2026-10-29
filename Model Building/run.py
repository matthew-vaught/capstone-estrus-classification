"""Convenient entry point; install the package first: pip install -e '.[dev]'."""
from estrus.cli import main

if __name__ == "__main__":
    import sys
    raise SystemExit(main(["run", *sys.argv[1:]]))
