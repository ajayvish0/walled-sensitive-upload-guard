"""Single entry point for inspecting prompts and files."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import config
from .detector import contains_marker, contains_marker_fuzzy
from .extractors.image import IMAGE_EXTENSIONS, ocr_image_bytes
from .extractors.pdf import extract_pdf_content
from .extractors.text import TEXT_EXTENSIONS, decode_text, is_probably_text

logger = logging.getLogger(__name__)

FileType = Literal["pdf", "image", "text", "unknown"]

_RAW_PATTERNS = (
    config.MARKER_BYTES,
    config.MARKER.encode("utf-16-le"),
    config.MARKER.encode("utf-16-be"),
)


@dataclass
class Verdict:
    """Result of an inspection."""

    flagged: bool
    kind: Literal["prompt", "file"]
    name: str
    file_type: str
    reason: str
    error: str | None = None


def detect_file_type(name: str, data: bytes) -> FileType:
    """Classify by magic bytes, then extension, then a text heuristic."""
    head = data[:16]
    if head.startswith(b"%PDF-"):
        return "pdf"
    if (head.startswith(b"\x89PNG\r\n\x1a\n") or head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"GIF8") or head.startswith(b"BM")
            or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
            or head.startswith(b"II*\x00") or head.startswith(b"MM\x00*")):
        return "image"
    ext = Path(name).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "text" if is_probably_text(data) else "unknown"


def inspect_prompt(text: str) -> Verdict:
    """Inspect a text prompt."""
    flagged = contains_marker(text)
    return Verdict(flagged, "prompt", "prompt", "text",
                   "marker found in prompt" if flagged else "no marker")


def _raw_hit(data: bytes) -> bool:
    return any(p in data for p in _RAW_PATTERNS)


def _scan(ftype: FileType, name: str, data: bytes) -> tuple[bool, str]:
    if ftype == "text":
        return contains_marker(decode_text(data)), "text content"
    if ftype == "pdf":
        content = extract_pdf_content(data)
        if contains_marker(content.text):
            return True, "PDF text layer"
        return contains_marker_fuzzy(content.ocr_text), "PDF OCR"
    if ftype == "image":
        return contains_marker_fuzzy(ocr_image_bytes(data)), "image OCR"
    return False, "unknown type"


def inspect_file(name: str, data: bytes) -> Verdict:
    """Inspect file bytes; fail-open on errors or oversized files."""
    ftype = detect_file_type(name, data)
    try:
        if len(data) > config.MAX_FILE_BYTES:
            logger.warning("file too large to inspect (%d bytes); allowing", len(data))
            return Verdict(False, "file", name, ftype, "not inspected", "too large, not inspected")
        if _raw_hit(data):
            return Verdict(True, "file", name, ftype, "marker found in raw bytes")
        flagged, where = _scan(ftype, name, data)
        return Verdict(flagged, "file", name, ftype,
                       f"marker found in {where}" if flagged else "no marker")
    except Exception as exc:
        logger.warning("inspection failed (%s); allowing", type(exc).__name__)
        return Verdict(False, "file", name, ftype, "inspection error", str(exc))
