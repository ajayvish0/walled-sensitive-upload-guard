"""Entry point: python -m walled_guard (or the walled-guard console script)."""
from __future__ import annotations

from .gui import run
from .logging_setup import setup_logging


def main() -> int:
    """Set up logging and run the desktop app."""
    setup_logging()
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
