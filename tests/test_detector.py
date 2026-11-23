import pytest

from walled_guard.detector import contains_marker, contains_marker_fuzzy


def test_marker_alone():
    assert contains_marker("WALLED_SENSITIVE") and contains_marker_fuzzy("WALLED_SENSITIVE")


def test_marker_in_long_text():
    assert contains_marker("lorem ipsum " * 500 + "WALLED_SENSITIVE" + " dolor" * 500)


def test_split_by_newline():
    assert not contains_marker("WALLED\nSENSITIVE")
    assert contains_marker_fuzzy("WALLED\nSENSITIVE")


def test_lowercase():
    assert not contains_marker("walled_sensitive")
    assert contains_marker_fuzzy("walled_sensitive")


def test_empty():
    assert not contains_marker("") and not contains_marker_fuzzy("")


@pytest.mark.parametrize("t", ["walled", "sensitive", "walled garden ... sensitive data"])
def test_unrelated(t):
    assert not contains_marker(t) and not contains_marker_fuzzy(t)


@pytest.mark.parametrize("t", ["WALLED SENSITIVE", "walled-sensitive", "WALLED_SENS1TIVE", "WALLED_SENSlTIVE"])
def test_ocr_variants(t):
    assert contains_marker_fuzzy(t)
