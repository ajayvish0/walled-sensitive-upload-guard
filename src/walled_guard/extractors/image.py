"""Image OCR extraction."""
from __future__ import annotations

import io
import logging
import threading
from typing import Any

from PIL import Image, ImageOps

from . import ExtractionError

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
)

_MAX_SIDE = 2200
_MIN_SIDE = 600
_engine: Any = None
_lock = threading.Lock()


def _get_engine() -> Any:
    """Lazy, thread-safe OCR engine singleton."""
    global _engine
    with _lock:
        if _engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError:
                from rapidocr import RapidOCR  # type: ignore[no-redef]
            _engine = RapidOCR()
        return _engine


def _prepare(data: bytes) -> bytes:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    longest = max(img.size)
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    elif longest < _MIN_SIDE:
        img = img.resize((img.width * 2, img.height * 2))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _lines(result: Any) -> list[str]:
    """Normalise the OCR result of either supported package to a list of lines."""
    if isinstance(result, tuple):  # rapidocr_onnxruntime: (list | None, timings)
        result = result[0]
    if result is None:
        return []
    if hasattr(result, "txts"):  # rapidocr (new API)
        return [t for t in (result.txts or ())]
    return [item[1] for item in result]


def ocr_image_bytes(data: bytes) -> str:
    """Run OCR over image bytes and return recognised lines joined by newlines."""
    try:
        png = _prepare(data)
        return "\n".join(_lines(_get_engine()(png)))
    except ExtractionError:
        raise
    except Exception as exc:
        logger.warning("OCR failed: %s", type(exc).__name__)
        raise ExtractionError(f"image OCR failed: {type(exc).__name__}") from exc
