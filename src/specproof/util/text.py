"""Text normalization and table-row tokenization (architecture section 6)."""

import re
import unicodedata

_QUOTES = str.maketrans({chr(0x201C): '"', chr(0x201D): '"', chr(0x2018): "'", chr(0x2019): "'"})
_WS = re.compile(r"\s+")
ROW_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z_][\w.\[\]]*)\s{2,}(?P<req>T|F)\s{2,}(?P<type>[A-Za-z][\w\[\]]*)"
)


def norm(s: str) -> str:
    """NFKC, straight quotes, every whitespace run collapsed to one space, stripped; idempotent."""
    previous = None
    while s != previous:
        previous = s
        s = _WS.sub(" ", unicodedata.normalize("NFKC", s).translate(_QUOTES)).strip()
    return s


TYPE_WORD = re.compile(
    r"(?:string|integer|int|long|number|float|double|boolean|bool|object|file|array"
    r"|array\[[a-z]+\])",
    re.IGNORECASE,
)


def row_tokens(line: str) -> tuple[str, str, str] | None:
    """Return (name, T|F, type) for a table row with 2+ space gaps and a real type word.

    A row whose type cell wrapped onto other lines has a description word in the type
    position; it is rejected here so it is treated as a wrapped row, not a mismatch.
    """
    match = ROW_RE.match(line)
    if match is None or not TYPE_WORD.fullmatch(match.group("type")):
        return None
    return match.group("name"), match.group("req"), match.group("type")
