"""Text decoding helpers."""
from __future__ import annotations

import codecs

TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".md", ".csv", ".json", ".log", ".xml", ".yaml", ".yml", ".html", ".htm",
     ".rtf", ".ini", ".py", ".js", ".ts", ".sql", ".tsv"}
)

_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def _bom_encoding(data: bytes) -> str | None:
    for bom, enc in _BOMS:
        if data.startswith(bom):
            return enc
    return None


def decode_text(data: bytes) -> str:
    """Decode bytes to str, honouring BOMs; never raises."""
    enc = _bom_encoding(data)
    if enc:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def is_probably_text(data: bytes) -> bool:
    """Heuristic: False for NUL-containing or control-heavy data."""
    head = data[:8192]
    if not head:
        return True
    if _bom_encoding(head) in ("utf-16", "utf-32"):
        return True
    if b"\x00" in head:
        return False
    control = sum(1 for b in head if b < 32 and b not in (9, 10, 12, 13))
    return control / len(head) <= 0.30
