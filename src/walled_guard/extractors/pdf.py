"""PDF extraction: text layer plus OCR of scanned/image pages."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pymupdf

from .. import config
from . import ExtractionError
from .image import ocr_image_bytes

logger = logging.getLogger(__name__)

_MIN_TEXT_CHARS = 20


@dataclass
class PdfContent:
    """Text layer and OCR text of a PDF."""

    text: str
    ocr_text: str


def extract_pdf_content(data: bytes, ocr: bool = True) -> PdfContent:
    """Extract text layer and (optionally) OCR text from scanned or image-bearing pages."""
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ExtractionError(f"unreadable PDF: {type(exc).__name__}") from exc
    try:
        if doc.needs_pass:
            raise ExtractionError("password-protected PDF")
        pages = [doc[i] for i in range(min(doc.page_count, config.MAX_PDF_PAGES))]
        page_texts = [p.get_text() for p in pages]
        ocr_parts: list[str] = []
        if ocr:
            done = 0
            for page, text in zip(pages, page_texts):
                if done >= config.MAX_OCR_PAGES:
                    break
                if len(text.strip()) >= _MIN_TEXT_CHARS and not page.get_images():
                    continue
                done += 1
                try:
                    png = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
                    ocr_parts.append(ocr_image_bytes(png))
                except Exception as exc:
                    logger.warning("OCR failed on a PDF page: %s", type(exc).__name__)
        return PdfContent(text="\n".join(page_texts), ocr_text="\n".join(ocr_parts))
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"PDF extraction failed: {type(exc).__name__}") from exc
    finally:
        doc.close()
