"""V4 (method/path vs deterministic hints) and V5 (table-row coverage). Pure."""

import re
from collections.abc import Mapping
from typing import Any

from specproof.models.contract import ContractSection
from specproof.models.verification import Issue
from specproof.util.text import norm, row_tokens
from specproof.verify.grounding import SectionContext

TABLE_HEADERS = (
    "Request Header",
    "Request Body",
    "Query Parameters",
    "Path Parameters",
    "Response Body",
)
TABLE_ENDS = ("Request Sample", "Response Sample")
_PARAM = re.compile(r":[A-Za-z_]\w*|\{[^}/]*\}")


def norm_path(path: str) -> str:
    """Leading '/', no query, no trailing '/', and ':name' / '{name}' segments as '{}'."""
    path = path.strip().split("?", 1)[0].rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return _PARAM.sub("{}", path)


def check_endpoint(contract: ContractSection, entry: Mapping[str, Any]) -> list[Issue]:
    """Compare the contract's method and path with the segmenter's hints."""
    if contract.kind != "endpoint":
        return []
    issues: list[Issue] = []
    method_hint = entry.get("method_hint")
    if method_hint and (contract.method or "").upper() != str(method_hint).upper():
        issues.append(
            Issue(
                code="V4_METHOD_MISMATCH",
                severity="error",
                category="extraction",
                message=f"method {contract.method} but the document says {method_hint}",
            )
        )
    path_hint = entry.get("path_hint")
    if path_hint and norm_path(contract.path or "") != norm_path(str(path_hint)):
        issues.append(
            Issue(
                code="V4_PATH_MISMATCH",
                severity="error",
                category="extraction",
                message=f"path {contract.path} but the document says {path_hint}",
            )
        )
    return issues


def _header(line: str) -> str | None:
    text = norm(line)
    for header in TABLE_HEADERS + TABLE_ENDS:
        if text.startswith(header):
            return header
    return None


def detected_rows(ctx: SectionContext) -> list[str]:
    """Row names found inside the section's parameter tables, in document order, deduplicated."""
    names: list[str] = []
    in_table = False
    for _page, line in ctx.lines:
        header = _header(line)
        if header is not None:
            in_table = header in TABLE_HEADERS
            continue
        tokens = row_tokens(line) if in_table else None
        if tokens is not None and tokens[0] not in names:
            names.append(tokens[0])
    return names


def check_coverage(ctx: SectionContext, contract: ContractSection) -> list[Issue]:
    """Every detected table row must be a contract field or definition (V5)."""
    known = {f.name for f in contract.fields} | {f.name for f in contract.definitions}
    return [
        Issue(
            code="V5_COVERAGE_GAP",
            severity="error",
            category="extraction",
            field=name,
            message=f"table row {name!r} is missing from the contract",
        )
        for name in sorted(set(detected_rows(ctx)) - known)
    ]
