"""Verification result models (architecture sections 5.5 and 6)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from specproof.models.contract import Citation

IssueCode = Literal[
    "V1_SCHEMA_INVALID",
    "V2_QUOTE_TOO_SHORT",
    "V2_CITATION_NOT_FOUND",
    "V2_CITATION_WRONG_PAGE",
    "V2_NAME_NOT_IN_QUOTE",
    "V2_ROW_MISMATCH",
    "V2_ROW_NOT_FOUND",
    "V2_ENUM_NOT_GROUNDED",
    "V2_SAMPLE_NOT_VERBATIM",
    "V3_SAMPLE_UNPARSEABLE",
    "V3_REQUIRED_MISSING",
    "V3_TYPE_MISMATCH",
    "V3_ENUM_VIOLATION",
    "V3_UNKNOWN_FIELD",
    "V4_METHOD_MISMATCH",
    "V4_PATH_MISMATCH",
    "V5_COVERAGE_GAP",
]
Severity = Literal["error", "warning", "info"]
Category = Literal["extraction", "sample_conflict", "info"]
SectionStatus = Literal[
    "EXTRACTED", "NEEDS_RETRY", "VERIFIED", "VERIFIED_WITH_SPEC_FINDINGS", "QUARANTINED"
]

RULE_ORDER: tuple[str, ...] = (
    "V1_SCHEMA_INVALID",
    "V2_QUOTE_TOO_SHORT",
    "V2_CITATION_NOT_FOUND",
    "V2_CITATION_WRONG_PAGE",
    "V2_NAME_NOT_IN_QUOTE",
    "V2_ROW_MISMATCH",
    "V2_ROW_NOT_FOUND",
    "V2_ENUM_NOT_GROUNDED",
    "V2_SAMPLE_NOT_VERBATIM",
    "V3_SAMPLE_UNPARSEABLE",
    "V3_REQUIRED_MISSING",
    "V3_TYPE_MISMATCH",
    "V3_ENUM_VIOLATION",
    "V3_UNKNOWN_FIELD",
    "V4_METHOD_MISMATCH",
    "V4_PATH_MISMATCH",
    "V5_COVERAGE_GAP",
)


class Issue(BaseModel):
    """One rule violation, with optional document evidence and a retry hint."""

    model_config = ConfigDict(extra="forbid")

    code: IssueCode
    severity: Severity
    category: Category
    field: str | None = None
    message: str
    evidence: Citation | None = None
    hint: dict[str, str | int] | None = None

    def sort_key(self) -> tuple[int, str, str, str]:
        """Order by rule catalog position, then field, code and message."""
        return (RULE_ORDER.index(self.code), self.field or "", self.code, self.message)


class VerificationResult(BaseModel):
    """All issues for one section attempt, sorted by rule order, plus item counts."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    attempt: int
    issues: list[Issue]
    counts: dict[str, int]

    @field_validator("issues")
    @classmethod
    def _sorted(cls, issues: list[Issue]) -> list[Issue]:
        return sorted(issues, key=Issue.sort_key)
