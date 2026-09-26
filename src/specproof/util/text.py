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


def row_tokens(line: str) -> tuple[str, str, str] | None:
    """Return (name, T|F, type) when the line is a table row with 2+ space column gaps."""
    match = ROW_RE.match(line)
    if match is None:
        return None
    return match.group("name"), match.group("req"), match.group("type")
