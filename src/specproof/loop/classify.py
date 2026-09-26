"""Classification state machine (architecture section 7, ADR-005, ADR-006). Pure, no LLM."""

from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.models.findings import Evidence, Finding, FindingSeverity, FindingType
from specproof.models.verification import Issue, SectionStatus, VerificationResult

MAX_ATTEMPTS = 3
_FINDING: dict[str, tuple[FindingType, FindingSeverity, str]] = {
    "V3_ENUM_VIOLATION": (
        "SPEC_SELF_INCONSISTENCY",
        "high",
        "Sample value violates the documented enum for {field}",
    ),
    "V3_TYPE_MISMATCH": (
        "SPEC_SELF_INCONSISTENCY",
        "high",
        "Sample value type contradicts the documented type of {field}",
    ),
    "V3_REQUIRED_MISSING": (
        "SPEC_SAMPLE_INCOMPLETE",
        "medium",
        "Sample omits {field}, which the document marks required",
    ),
    "V3_SAMPLE_UNPARSEABLE": (
        "SPEC_MALFORMED_SAMPLE",
        "medium",
        "Document sample is not valid JSON",
    ),
}


def extraction_errors(result: VerificationResult) -> list[Issue]:
    """Issues that mean the extraction is wrong: category extraction, severity error."""
    return [i for i in result.issues if i.category == "extraction" and i.severity == "error"]


def _fields_by_name(contract: ContractSection) -> dict[str, FieldSpec]:
    fields: dict[str, FieldSpec] = {}
    for field in sorted(
        [*contract.fields, *contract.definitions], key=lambda f: (f.location, f.name)
    ):
        fields.setdefault(field.name, field)
    return fields


def _doc(citation: Citation) -> Evidence:
    return Evidence(kind="doc", page=citation.page, quote=citation.quote)


def _evidence(issue: Issue, field: FieldSpec | None) -> list[Evidence]:
    evidence: list[Evidence] = []
    if field is not None and issue.code != "V3_SAMPLE_UNPARSEABLE":
        if issue.code == "V3_ENUM_VIOLATION" and field.enum_citation is not None:
            evidence.append(_doc(field.enum_citation))
        else:
            evidence.append(_doc(field.citation))
    if issue.evidence is not None:
        evidence.append(_doc(issue.evidence))
    return sorted(evidence, key=Evidence.canonical)


def _is_grounded(issue: Issue, result: VerificationResult, field: FieldSpec | None) -> bool:
    """ADR-006: the conflicting field and the sample citation must both have passed V2."""
    if extraction_errors(result) or issue.evidence is None:
        return False
    if issue.field is not None and issue.code != "V3_REQUIRED_MISSING" and field is None:
        return False
    return not any(i.field == issue.field and i.category == "extraction" for i in result.issues)


def spec_findings(result: VerificationResult, contract: ContractSection) -> list[Finding]:
    """Findings about the document itself, from grounded sample conflicts only."""
    fields = _fields_by_name(contract)
    findings: dict[str, Finding] = {}
    for issue in result.issues:
        if issue.category != "sample_conflict" or issue.code not in _FINDING:
            continue
        field = fields.get(issue.field) if issue.field else None
        if not _is_grounded(issue, result, field):
            continue
        type_, severity, title = _FINDING[issue.code]
        evidence = _evidence(issue, field)
        finding_id = Finding.make_id(type_, result.section_id, issue.field, evidence)
        findings[finding_id] = Finding(
            id=finding_id,
            type=type_,
            severity=severity,
            section_id=result.section_id,
            title=title.format(field=issue.field or "the sample"),
            evidence=evidence,
        )
    return [findings[key] for key in sorted(findings)]


def classify(
    result: VerificationResult,
    contract: ContractSection | None,
    previous: VerificationResult | None,
) -> tuple[SectionStatus, list[Finding]]:
    """Return the section status and its spec findings; the same inputs give the same output."""
    errors = len(extraction_errors(result))
    if errors:
        # A schema-invalid attempt ran no other rule, so its error count is not comparable.
        measured = previous is not None and not any(
            i.code == "V1_SCHEMA_INVALID" for i in previous.issues
        )
        stalled = measured and previous is not None and errors >= len(extraction_errors(previous))
        if stalled or result.attempt >= MAX_ATTEMPTS:
            return "QUARANTINED", []
        return "NEEDS_RETRY", []
    findings = spec_findings(result, contract) if contract is not None else []
    return ("VERIFIED_WITH_SPEC_FINDINGS" if findings else "VERIFIED"), findings
