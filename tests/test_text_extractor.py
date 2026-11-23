import os

import pytest

from walled_guard.detector import contains_marker
from walled_guard.extractors.text import decode_text, is_probably_text

M = "WALLED_SENSITIVE"


@pytest.mark.parametrize(
    "data",
    [
        f"x {M} y".encode("utf-8"),
        b"\xef\xbb\xbf" + f"x {M} y".encode("utf-8"),
        b"\xff\xfe" + f"x {M} y".encode("utf-16-le"),
        b"\xfe\xff" + f"x {M} y".encode("utf-16-be"),
        f"x {M} y".encode("utf-32"),
        f"“quoted” {M}".encode("cp1252"),
    ],
)
def test_marker_survives_decoding(data):
    assert contains_marker(decode_text(data))


def test_utf8_roundtrip():
    assert decode_text("héllo".encode()) == "héllo"


def test_bom_stripped():
    assert decode_text(b"\xef\xbb\xbfabc") == "abc"


def test_cp1252_curly_quotes():
    assert decode_text(b"\x93hi\x94") == "“hi”"


def test_never_raises_on_random():
    assert isinstance(decode_text(os.urandom(2000)), str)


def test_binary_not_text():
    assert not is_probably_text(b"\x00\x01\x02\x03" * 100)
    assert not is_probably_text(bytes(range(1, 9)) * 200)


def test_text_is_text():
    assert is_probably_text(b"hello world\nline 2")
    assert is_probably_text(b"\xff\xfe" + "hello".encode("utf-16-le"))
