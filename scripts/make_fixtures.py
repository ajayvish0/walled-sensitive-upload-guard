"""Generate small test fixtures into tests/fixtures/."""
from __future__ import annotations

import io
import os
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
SENSITIVE_LINE = "Quarterly report WALLED_SENSITIVE do not share"
CLEAN_LINE = "Quarterly report lunch menu dal and rice"


def _font(size: int = 56) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def text_image(line: str) -> Image.Image:
    """White background, black text."""
    font = _font()
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    box = probe.textbbox((0, 0), line, font=font)
    img = Image.new("RGB", (box[2] + 80, box[3] + 80), "white")
    ImageDraw.Draw(img).text((40, 40), line, fill="black", font=font)
    return img


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def text_pdf(path: Path, line: str) -> None:
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), line, fontsize=14)
    doc.save(path)


def scanned_pdf(path: Path, line: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(fitz.Rect(30, 60, 565, 160), stream=png_bytes(text_image(line)))
    doc.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "clean.txt").write_text("Weekly notes: lunch menu is dal and rice.\n", encoding="utf-8")
    (OUT / "sensitive.txt").write_text("Roadmap draft. WALLED_SENSITIVE. Do not share.\n", encoding="utf-8")
    (OUT / "sensitive_utf16.txt").write_bytes(b"\xff\xfe" + "Roadmap WALLED_SENSITIVE".encode("utf-16-le"))
    text_pdf(OUT / "clean.pdf", CLEAN_LINE)
    text_pdf(OUT / "sensitive.pdf", SENSITIVE_LINE)
    scanned_pdf(OUT / "sensitive_scanned.pdf", SENSITIVE_LINE)
    scanned_pdf(OUT / "clean_scanned.pdf", CLEAN_LINE)
    text_image(CLEAN_LINE).save(OUT / "clean.png")
    text_image(SENSITIVE_LINE).save(OUT / "sensitive.png")
    text_image(SENSITIVE_LINE).save(OUT / "sensitive.jpg", quality=92)
    (OUT / "corrupt.png").write_bytes(b"\x01" + os.urandom(512))


if __name__ == "__main__":
    main()
