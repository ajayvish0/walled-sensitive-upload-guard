"""Logging configuration: console plus rotating file."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from . import config


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_wg_configured", False):
        return
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    file_handler = RotatingFileHandler(config.LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)
    root._wg_configured = True  # type: ignore[attr-defined]
