"""Deterministic retry feedback in the format of docs/LOOP_ENGINEERING.md. Pure."""

from specproof.loop.classify import extraction_errors
from specproof.models.contract import ContractSection
from specproof.models.verification import Issue, VerificationResult
from specproof.util.text import norm

INSTRUCTION = "Fix ONLY the items below. Do not change items that passed."
SECTION_BLOCK = "(section)"


def _location(field: str, contract: ContractSection | None) -> str:
    if contract is None:
        return "unknown"
    for spec in [*contract.fields, *contract.definitions]:
        if spec.name == field:
            return spec.location
    return "not in contract"


def _detail(issue: Issue, span: str) -> str | None:
    hint = issue.hint or {}
    if "closest_match" in hint:
        return (
            f"  Closest text on pages {span} (page {hint['closest_page']}): "
            f'"{hint["closest_match"]}"'
        )
    if "suggested_page" in hint:
        return f"  The quote is on page {hint['suggested_page']}."
    if "first_unmatched" in hint:
        return f'  First line not found verbatim: "{hint["first_unmatched"]}"'
    if issue.evidence is not None:
        return f'  Evidence: page {issue.evidence.page}, "{norm(issue.evidence.quote)}"'
    return None


def render_feedback(
    result: VerificationResult, contract: ContractSection | None, page_span: tuple[int, int]
) -> str:
    """Markdown listing only the failing extraction items, grouped by field and sorted."""
    blocks: dict[str, list[Issue]] = {}
    for issue in extraction_errors(result):
        blocks.setdefault(issue.field or SECTION_BLOCK, []).append(issue)
    span = f"{page_span[0]}-{page_span[1]}"
    lines = [
        f"# Feedback: {result.section_id} (attempt {result.attempt} → {result.attempt + 1})",
        INSTRUCTION,
    ]
    for name in sorted(blocks, key=lambda n: (n != SECTION_BLOCK, n)):
        heading = (
            name if name == SECTION_BLOCK else f"{name} (location: {_location(name, contract)})"
        )
        lines += ["", f"## {heading}"]
        for issue in blocks[name]:
            lines.append(f"- {issue.code}: {issue.message}")
            detail = _detail(issue, span)
            if detail is not None:
                lines.append(detail)
    return "\n".join(lines) + "\n"
