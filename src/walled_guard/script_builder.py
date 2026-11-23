"""Builds the JavaScript injected into every page."""
from __future__ import annotations

import json
from importlib import resources

from . import config


def _read(name: str) -> str:
    return resources.files("walled_guard.inject").joinpath(name).read_text(encoding="utf-8")


def build_init_script() -> str:
    """Return config + sites.js + style.js + guard.js as one init script."""
    cfg = {
        "color": config.RESPONSE_COLOR,
        "maxFileBytes": config.MAX_FILE_BYTES,
        "enableHarness": config.harness_enabled(),
    }
    return "\n".join(
        [f"window.__WG_CONFIG = {json.dumps(cfg)};", _read("sites.js"), _read("style.js"), _read("guard.js")]
    )
