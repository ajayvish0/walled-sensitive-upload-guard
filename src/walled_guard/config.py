"""Central configuration constants."""
from __future__ import annotations

import os
from pathlib import Path

MARKER: str = "WALLED_SENSITIVE"
MARKER_BYTES: bytes = MARKER.encode()
MAX_FILE_BYTES: int = 30 * 1024 * 1024
MAX_PDF_PAGES: int = 50
MAX_OCR_PAGES: int = 10
RESPONSE_COLOR: str = "#FF7A00"

DATA_DIR: Path = Path.home() / ".walled-guard"
PROFILE_DIR: Path = DATA_DIR / "chrome-profile"
LOG_FILE: Path = DATA_DIR / "guard.log"
DIALOG_AUTO_ENV: str = "WALLED_DIALOG_AUTO"

SITES: dict[str, dict] = {
    "chatgpt": {"name": "ChatGPT", "url": "https://chatgpt.com", "hosts": ["chatgpt.com"]},
    "perplexity": {
        "name": "Perplexity",
        "url": "https://www.perplexity.ai",
        "hosts": ["www.perplexity.ai", "perplexity.ai"],
    },
}


def harness_enabled() -> bool:
    """True when the test harness host is enabled (tests only); read at call time."""
    return os.environ.get("WALLED_ENABLE_HARNESS") == "1"
