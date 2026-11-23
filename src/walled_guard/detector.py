"""Pure marker-detection functions."""
from __future__ import annotations

import re

from .config import MARKER

_STRIP = re.compile(r"[^A-Z0-9|!]")
_FUZZY = re.compile(r"WALLEDSENS[I1L|!]T[I1L|!]VE")


def contains_marker(text: str) -> bool:
    """Exact, case-sensitive marker match."""
    return MARKER in text


def contains_marker_fuzzy(text: str) -> bool:
    """OCR-tolerant marker match (case, separators and I/1/l/|/! confusions)."""
    return _FUZZY.search(_STRIP.sub("", text.upper())) is not None
