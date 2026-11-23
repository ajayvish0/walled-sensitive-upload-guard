import time
from pathlib import Path

import pytest

from walled_guard.detector import contains_marker_fuzzy
from walled_guard.extractors import ExtractionError
from walled_guard.extractors.image import ocr_image_bytes

FIX = Path(__file__).parent / "fixtures"


def _ocr(name: str) -> str:
    start = time.time()
    text = ocr_image_bytes((FIX / name).read_bytes())
    print(f"\n[{name}] {time.time() - start:.2f}s -> {text!r}")
    return text


@pytest.mark.parametrize("name", ["sensitive.png", "sensitive.jpg"])
def test_sensitive_images_detected(name):
    assert contains_marker_fuzzy(_ocr(name))


def test_clean_image_not_flagged():
    assert not contains_marker_fuzzy(_ocr("clean.png"))


def test_corrupt_image_raises():
    with pytest.raises(ExtractionError):
        ocr_image_bytes((FIX / "corrupt.png").read_bytes())
