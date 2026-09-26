"""Deterministic section segmentation (architecture section 5.4, ADR-002). No LLM."""

import re
from dataclasses import dataclass
from typing import Any

from specproof.ingest.extractors import Page
from specproof.util.hashing import sha256_text
from specproof.util.text import norm

TOC_LINE = re.compile(r"\.{5,}\s*\d+\s*$")
HEADING = re.compile(r"^(\d{1,2})\.(\d{1,2})\s+([A-Z][^\n]{1,80}?)\s*$")
_HEADING_MAX_INDENT = 12
_WS_RUN = re.compile(r"\s+")
METHOD = re.compile(r"Method\s*:\s*([A-Z]+)")
REQUEST_URL = re.compile(r"Request\s+URL\s*:\s*(\S+)")
_TOC_MIN_LINES = 5


@dataclass(frozen=True)
class Section:
    """One segmented section: index entry (no full text), full text, and (page, line) pairs."""

    entry: dict[str, Any]
    text: str
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class _Heading:
    chapter: int
    number: int
    title: str
    line_index: int


def is_toc_page(text: str) -> bool:
    """True if at least five lines end in dotted leaders plus a page number."""
    return sum(1 for line in text.splitlines() if TOC_LINE.search(line)) >= _TOC_MIN_LINES


def normalize_path_hint(raw: str) -> str | None:
    """Drop the query string, ensure a leading slash, strip a trailing slash; None if not a path."""
    path = raw.split("?", 1)[0].rstrip("/")
    if "/" not in path:
        return None
    return path if path.startswith("/") else "/" + path


def _lines(pages: list[Page]) -> list[tuple[int, str, bool]]:
    rows: list[tuple[int, str, bool]] = []
    for page in sorted(pages, key=lambda p: p.number):
        toc = is_toc_page(page.text)
        rows.extend((page.number, line, toc) for line in page.text.split("\n"))
    return rows


def _heading_match(line: str) -> re.Match[str] | None:
    """Match on the whitespace-collapsed line, so layout spacing cannot exceed the title limit."""
    if len(line) - len(line.lstrip(" ")) > _HEADING_MAX_INDENT:
        return None
    return HEADING.match(_WS_RUN.sub(" ", line.strip()))


def _headings(lines: list[tuple[int, str, bool]]) -> list[_Heading]:
    accepted: list[_Heading] = []
    for index, (_page, line, toc) in enumerate(lines):
        match = _heading_match(line)
        if toc or match is None or TOC_LINE.search(line):
            continue
        chapter, number = int(match.group(1)), int(match.group(2))
        if accepted:
            last = accepted[-1]
            if (chapter, number) <= (last.chapter, last.number) or chapter < last.chapter:
                continue
        accepted.append(_Heading(chapter, number, norm(match.group(3)), index))
    return accepted


def _kind(title: str, text: str) -> str:
    if REQUEST_URL.search(text):
        return "endpoint"
    if "Schema" in title:
        return "schema"
    return "overview"


def _entry(heading: _Heading, text: str, page_start: int, page_end: int) -> dict[str, Any]:
    method = METHOD.search(text)
    url = REQUEST_URL.search(text)
    return {
        "section_id": f"S-{heading.chapter}.{heading.number}",
        "chapter": heading.chapter,
        "number": f"{heading.chapter}.{heading.number}",
        "title": heading.title,
        "kind": _kind(heading.title, text),
        "page_start": page_start,
        "page_end": page_end,
        "method_hint": method.group(1) if method else None,
        "path_hint": normalize_path_hint(url.group(1)) if url else None,
        "text_sha256": sha256_text(norm(text)),
    }


def segment(pages: list[Page]) -> list[Section]:
    """Split pages into sections sorted by (chapter, number); same pages give the same output."""
    lines = _lines(pages)
    headings = _headings(lines)
    sections = []
    for position, heading in enumerate(headings):
        end = headings[position + 1].line_index if position + 1 < len(headings) else len(lines)
        span = lines[heading.line_index : end]
        text = "\n".join(line for _page, line, _toc in span)
        page_end = max(page for page, line, _toc in span if line.strip())
        entry = _entry(heading, text, span[0][0], page_end)
        numbered = tuple((page, line) for page, line, _toc in span)
        sections.append(Section(entry=entry, text=text, lines=numbered))
    return sorted(
        sections, key=lambda s: (s.entry["chapter"], int(s.entry["number"].split(".")[1]))
    )
