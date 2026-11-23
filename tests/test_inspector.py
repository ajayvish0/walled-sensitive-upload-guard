from pathlib import Path

import pytest

from walled_guard import config
from walled_guard.inspector import detect_file_type, inspect_file, inspect_prompt

FIX = Path(__file__).parent / "fixtures"

MATRIX = [
    ("clean.txt", False), ("sensitive.txt", True),
    ("sensitive_utf16.txt", True),
    ("clean.pdf", False), ("sensitive.pdf", True),
    ("clean_scanned.pdf", False), ("sensitive_scanned.pdf", True),
    ("clean.png", False), ("sensitive.png", True), ("sensitive.jpg", True),
]


@pytest.mark.parametrize("name,expected", MATRIX)
def test_fixture_matrix(name, expected):
    v = inspect_file(name, (FIX / name).read_bytes())
    assert v.flagged is expected
    assert v.error is None
    assert v.kind == "file" and v.name == name


def test_corrupt_png_fail_open():
    v = inspect_file("corrupt.png", (FIX / "corrupt.png").read_bytes())
    assert v.flagged is False and v.error


@pytest.mark.parametrize("text,expected", [("hi WALLED_SENSITIVE there", True), ("hello", False), ("", False)])
def test_prompts(text, expected):
    v = inspect_prompt(text)
    assert v.flagged is expected and v.kind == "prompt"


def test_too_large(monkeypatch):
    monkeypatch.setattr(config, "MAX_FILE_BYTES", 100)
    v = inspect_file("big.txt", b"WALLED_SENSITIVE" + b"x" * 200)
    assert v.flagged is False and v.error == "too large, not inspected"


@pytest.mark.parametrize(
    "name,data,expected",
    [
        ("x.bin", b"%PDF-1.7", "pdf"), ("x", b"\x89PNG\r\n\x1a\nxx", "image"),
        ("x", b"\xff\xd8\xff\xe0", "image"), ("x", b"GIF89a", "image"),
        ("x", b"RIFF\x00\x00\x00\x00WEBPVP8", "image"), ("x", b"II*\x00", "image"),
        ("a.txt", b"\x00\x01", "text"), ("a.pdf", b"nope", "pdf"),
        ("a", b"plain words", "text"), ("a", b"\x00\x01\x02" * 50, "unknown"),
    ],
)
def test_detect_file_type(name, data, expected):
    assert detect_file_type(name, data) == expected


def test_unknown_binary_raw_check_only():
    assert inspect_file("blob.bin", b"\x00\x01" * 10 + b"WALLED_SENSITIVE").flagged
    assert not inspect_file("blob.bin", b"\x00\x01" * 50).flagged
