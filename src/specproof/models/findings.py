"""Finding models with stable IDs (architecture section 5.6)."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from specproof.util.hashing import sha256_text

FindingType = Literal[
    "SPEC_SELF_INCONSISTENCY",
    "SPEC_MALFORMED_SAMPLE",
    "SPEC_SAMPLE_INCOMPLETE",
    "COMMUNITY_REQUIRED_MISMATCH",
    "COMMUNITY_TYPE_MISMATCH",
    "COMMUNITY_ENUM_MISMATCH",
    "COMMUNITY_MISSING_FIELD",
    "COMMUNITY_EXTRA_FIELD",
    "COMMUNITY_MISSING_ENDPOINT",
    "CLIENT_UNDOCUMENTED_ENDPOINT",
    "CLIENT_METHOD_MISMATCH",
    "CLIENT_TYPE_MISMATCH",
    "CLIENT_REQUIRES_UNDOCUMENTED_FIELD",
    "CLIENT_SAMPLE_REJECTED",
]
FindingSeverity = Literal["high", "medium", "low", "info"]
ReviewStatus = Literal["CANDIDATE", "CONFIRMED", "REJECTED"]


class Evidence(BaseModel):
    """A document citation (page + quote) or a code citation (file + line)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["doc", "code"]
    page: int | None = None
    quote: str | None = None
    file: str | None = None
    line: int | None = None
    snippet: str | None = None

    def canonical(self) -> str:
        """Return a stable string form used for finding IDs and sorting."""
        return json.dumps(self.model_dump(), sort_keys=True, ensure_ascii=False)


class Review(BaseModel):
    """Human review state; only eval/audit/findings_review.csv may change it."""

    model_config = ConfigDict(extra="forbid")

    status: ReviewStatus = "CANDIDATE"
    reviewer: str | None = None
    note: str | None = None


class Finding(BaseModel):
    """A candidate defect in the spec, the community conversion or the client."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: FindingType
    severity: FindingSeverity
    section_id: str
    title: str
    evidence: list[Evidence]
    review: Review = Field(default_factory=Review)

    @staticmethod
    def make_id(type_: str, section_id: str, field: str | None, evidence: list[Evidence]) -> str:
        """Return "F-" + 8 hex chars of sha256 over type, section, field and sorted evidence."""
        parts = [type_, section_id, field or "", *sorted(e.canonical() for e in evidence)]
        return "F-" + sha256_text("|".join(parts))[:8]
