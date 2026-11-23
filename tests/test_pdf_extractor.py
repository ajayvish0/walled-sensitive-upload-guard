import os
from pathlib import Path

import pytest

from walled_guard.detector import contains_marker, contains_marker_fuzzy
from walled_guard.extractors import ExtractionError
from walled_guard.extractors.pdf import extract_pdf_content

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return extract_pdf_content((FIX / name).read_bytes())


def test_text_layer_marker():
    assert contains_marker(_load("sensitive.pdf").text)


def test_clean_pdf():
    c = _load("clean.pdf")
    assert not contains_marker(c.text) and not contains_marker_fuzzy(c.ocr_text)


def test_scanned_sensitive():
    c = _load("sensitive_scanned.pdf")
    assert c.text.strip() == ""
    assert contains_marker_fuzzy(c.ocr_text)


def test_scanned_clean():
    c = _load("clean_scanned.pdf")
    assert not contains_marker_fuzzy(c.ocr_text) and not contains_marker_fuzzy(c.text)


def test_garbage_raises():
    with pytest.raises(ExtractionError):
        extract_pdf_content(os.urandom(1000))


def test_ocr_disabled():
    assert _load_no_ocr().ocr_text == ""


def _load_no_ocr():
    return extract_pdf_content((FIX / "sensitive_scanned.pdf").read_bytes(), ocr=False)
