"""V2 rules: citation grounding, row consistency, enum grounding, verbatim samples.

Pure and deterministic. rapidfuzz only fills retry hints; it never decides an outcome.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from specproof.models.contract import QUOTE_MIN, Citation, FieldSpec, Sample
from specproof.models.verification import Issue
from specproof.util.text import norm, row_tokens

ROW_LOCATIONS = frozenset({"header", "body", "query", "path"})
_HINT_MAX = 200


@dataclass(frozen=True)
class SectionContext:
    """Normalized page texts plus one section's (page, line) pairs and page range."""

    norm_pages: Mapping[int, str]
    lines: tuple[tuple[int, str], ...]
    page_start: int
    page_end: int

    @classmethod
    def build(
        cls,
        pages: Mapping[int, str],
        lines: tuple[tuple[int, str], ...] | list[tuple[int, str]],
        entry: Mapping[str, Any],
    ) -> "SectionContext":
        """Normalize every page once; keep the section's lines and page range."""
        return cls(
            norm_pages={n: norm(t) for n, t in pages.items()},
            lines=tuple((int(p), str(line)) for p, line in lines),
            page_start=int(entry["page_start"]),
            page_end=int(entry["page_end"]),
        )

    def section_pages(self) -> list[int]:
        """Pages of the section that exist in the document, ascending."""
        return [n for n in range(self.page_start, self.page_end + 1) if n in self.norm_pages]


def _issue(code: Any, message: str, **extra: Any) -> Issue:
    return Issue(code=code, severity="error", category="extraction", message=message, **extra)


def _closest(ctx: SectionContext, quote: str) -> tuple[str, int]:
    """Best-matching whole section line (first wins ties). Used only as a retry hint."""
    best, best_page, best_score = "", ctx.page_start, -1.0
    for page, line in ctx.lines:
        text = norm(line)
        if not text:
            continue
        found = fuzz.partial_ratio_alignment(quote, text)
        if found is not None and found.score > best_score:
            best, best_page, best_score = text, page, found.score
    return best[:_HINT_MAX], best_page


def check_citation(
    ctx: SectionContext, citation: Citation, field: str | None = None
) -> tuple[list[Issue], bool]:
    """Return (issues, grounded); grounded means the quote is on the cited page."""
    quote = norm(citation.quote)
    if len(quote) < QUOTE_MIN:
        msg = f"quote has {len(quote)} chars after normalization; minimum is {QUOTE_MIN}"
        return [_issue("V2_QUOTE_TOO_SHORT", msg, field=field, evidence=None)], False
    if quote in ctx.norm_pages.get(citation.page, ""):
        return [], True
    for page in ctx.section_pages():
        if quote in ctx.norm_pages[page]:
            msg = f"quote is not on page {citation.page} but is on page {page}"
            hint: dict[str, str | int] = {"suggested_page": page}
            return [_issue("V2_CITATION_WRONG_PAGE", msg, field=field, hint=hint)], False
    match, page = _closest(ctx, quote)
    msg = f"quote not found on page {citation.page} or elsewhere in the section"
    hint = {"closest_match": match, "closest_page": page}
    return [_issue("V2_CITATION_NOT_FOUND", msg, field=field, hint=hint)], False


def check_name_in_quote(field: FieldSpec) -> list[Issue]:
    """The field name must appear verbatim in its own normalized quote."""
    if field.name in norm(field.citation.quote):
        return []
    msg = f"field name {field.name!r} does not appear in its citation quote"
    return [_issue("V2_NAME_NOT_IN_QUOTE", msg, field=field.name, evidence=field.citation)]


def check_row(ctx: SectionContext, field: FieldSpec) -> tuple[list[Issue], bool]:
    """Compare required/type with a single-line table row; return (issues, row_found)."""
    rows = [(page, line, tok) for page, line in ctx.lines if (tok := row_tokens(line))]
    matches = [(page, line, tok) for page, line, tok in rows if tok[0] == field.name]
    if not matches:
        msg = f"no single-line table row for {field.name!r}; row check skipped"
        info = Issue(
            code="V2_ROW_NOT_FOUND", severity="info", category="info", field=field.name, message=msg
        )
        return [info], False
    want_req = "T" if field.required else "F"
    for _page, _line, (_name, req, type_raw) in matches:
        if req == want_req and type_raw.lower() == field.type_raw.lower():
            return [], True
    page, line, (_name, req, type_raw) = matches[0]
    msg = (
        f"row says required={req} type={type_raw}; contract says "
        f"required={field.required} type_raw={field.type_raw}"
    )
    evidence = Citation.model_construct(page=page, quote=line.strip()[:_HINT_MAX])
    return [_issue("V2_ROW_MISMATCH", msg, field=field.name, evidence=evidence)], True


def check_enum(field: FieldSpec) -> list[Issue]:
    """Every enum value must appear in the enum citation (or the field citation) quote."""
    if not field.enum:
        return []
    source = field.enum_citation or field.citation
    quote = norm(source.quote)
    missing = [value for value in field.enum if value not in quote]
    if not missing:
        return []
    msg = f"enum values not in the cited quote: {', '.join(missing)}"
    return [_issue("V2_ENUM_NOT_GROUNDED", msg, field=field.name, evidence=source)]


BOUNDARIES = (
    "Request Sample",
    "Response Sample",
    "Request Header",
    "Request Body",
    "Request Path",
    "Response Body",
    "Query Parameters",
    "Path Parameters",
    "curl",
    "-",
)
_HEADING = re.compile(r"^\d{1,2}\.\d{1,2}\s+[A-Z]")


def _is_boundary(text: str) -> bool:
    return text.startswith(BOUNDARIES) or bool(_HEADING.match(text))


def _next_content(ctx: SectionContext, start: int) -> str | None:
    """The next non-empty line after start, skipping a page's last line (a footer)."""
    lines = ctx.lines
    for index in range(start, len(lines)):
        page, text = lines[index]
        if not text.strip():
            continue
        later = [p for p, t in lines[index + 1 :] if t.strip()]
        if not later or later[0] != page:
            continue
        return norm(text)
    return None


def check_sample_verbatim(ctx: SectionContext, sample: Sample, which: str) -> list[Issue]:
    """Sample lines appear in order in the section, and the copy runs to the end of its block.

    A block ends at the next sample marker, table header, section heading or curl line, so
    a sample that is malformed in the document itself still counts as complete."""
    section = [norm(line) for _page, line in ctx.lines]
    position = 0
    last = -1
    for raw_line in sample.raw.split("\n"):
        wanted = norm(raw_line)
        if not wanted:
            continue
        while position < len(section) and wanted not in section[position]:
            position += 1
        if position == len(section):
            msg = f"{which} sample is not a verbatim copy of the document"
            hint: dict[str, str | int] = {"first_unmatched": wanted[:_HINT_MAX]}
            return [_issue("V2_SAMPLE_NOT_VERBATIM", msg, field=None, hint=hint)]
        last = position
        position += 1
    following = _next_content(ctx, last + 1) if last >= 0 else None
    if following is not None and not _is_boundary(following):
        msg = f"{which} sample is an incomplete copy: the document continues after it"
        hint = {"first_unmatched": following[:_HINT_MAX]}
        return [_issue("V2_SAMPLE_NOT_VERBATIM", msg, field=None, hint=hint)]
    return []
