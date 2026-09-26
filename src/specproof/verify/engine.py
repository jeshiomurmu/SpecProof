"""Runs V1-V5 in catalog order for one section. Pure, deterministic, no LLM, no network."""

import json
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from specproof.config import SCHEMA_VERSION
from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.models.verification import Issue, VerificationResult
from specproof.verify.grounding import (
    ROW_LOCATIONS,
    SectionContext,
    check_citation,
    check_enum,
    check_name_in_quote,
    check_row,
    check_sample_verbatim,
)
from specproof.verify.samples import validate_samples
from specproof.verify.structure import check_coverage, check_endpoint, detected_rows

EXTRACTION = "extraction"


def _attempt_of(raw: str) -> int:
    try:
        data = json.loads(raw)
        attempt = data["extraction"]["attempt"]
        return attempt if isinstance(attempt, int) and attempt >= 1 else 1
    except (ValueError, KeyError, TypeError):
        return 1


def load_contract(raw: str, section_id: str) -> tuple[ContractSection | None, list[Issue]]:
    """V1: parse and validate the contract JSON; any failure is one V1_SCHEMA_INVALID issue."""
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("contract must be a JSON object")
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"schema_version {data.get('schema_version')} is not supported")
        contract = ContractSection.model_validate(data)
        if contract.section_id != section_id:
            raise ValueError(f"section_id {contract.section_id} does not match {section_id}")
        return contract, []
    except (ValueError, ValidationError) as exc:
        message = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        issue = Issue(
            code="V1_SCHEMA_INVALID", severity="error", category=EXTRACTION, message=message
        )
        return None, [issue]


def _citations(contract: ContractSection) -> list[tuple[str | None, Citation]]:
    cites: list[tuple[str | None, Citation]] = [
        (None, contract.citations[key]) for key in sorted(contract.citations)
    ]
    for field in _all_fields(contract):
        cites.append((field.name, field.citation))
        if field.enum_citation is not None:
            cites.append((field.name, field.enum_citation))
    for sample in (contract.samples.request, contract.samples.response):
        if sample is not None:
            cites.append((None, sample.citation))
    return cites


def _all_fields(contract: ContractSection) -> list[FieldSpec]:
    return sorted([*contract.fields, *contract.definitions], key=lambda f: (f.location, f.name))


def _v2(ctx: SectionContext, contract: ContractSection, counts: dict[str, int]) -> list[Issue]:
    issues: list[Issue] = []
    for field_name, citation in _citations(contract):
        found, grounded = check_citation(ctx, citation, field_name)
        issues.extend(found)
        counts["items"] += 1
        counts["grounded"] += int(grounded)
    for field in _all_fields(contract):
        issues.extend(check_name_in_quote(field))
        if field.location in ROW_LOCATIONS and field.required is not None:
            row_issues, row_found = check_row(ctx, field)
            issues.extend(row_issues)
            if row_found:
                counts["row_checked"] += 1
                counts["row_ok"] += int(not row_issues)
        issues.extend(check_enum(field))
    for which, sample in (
        ("request", contract.samples.request),
        ("response", contract.samples.response),
    ):
        if sample is not None:
            issues.extend(check_sample_verbatim(ctx, sample, which))
    return issues


def verify_section(
    raw: str,
    entry: Mapping[str, Any],
    pages: Mapping[int, str],
    lines: tuple[tuple[int, str], ...] | list[tuple[int, str]],
) -> VerificationResult:
    """Verify one contract (raw JSON text) against its section; same inputs, same result."""
    section_id = str(entry["section_id"])
    keys = (
        "items",
        "grounded",
        "row_checked",
        "row_ok",
        "rows_detected",
        "samples",
        "samples_parsed",
    )
    counts: dict[str, int] = dict.fromkeys(keys, 0)
    contract, issues = load_contract(raw, section_id)
    if contract is None:
        return VerificationResult(
            section_id=section_id, attempt=_attempt_of(raw), issues=issues, counts=counts
        )
    ctx = SectionContext.build(pages, lines, entry)
    issues.extend(_v2(ctx, contract, counts))
    sample_issues, sample_counts = validate_samples(contract)
    issues.extend(sample_issues)
    counts.update(sample_counts)
    issues.extend(check_endpoint(contract, entry))
    issues.extend(check_coverage(ctx, contract))
    counts["rows_detected"] = len(detected_rows(ctx))
    return VerificationResult(
        section_id=section_id, attempt=contract.extraction.attempt, issues=issues, counts=counts
    )


def has_extraction_errors(result: VerificationResult) -> bool:
    """True if any issue is an extraction-category error."""
    return any(i.category == EXTRACTION and i.severity == "error" for i in result.issues)
