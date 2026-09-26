"""Contract data models (architecture sections 5.1-5.3)."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from specproof.config import SCHEMA_VERSION
from specproof.util.io_json import dump_json, load_json
from specproof.util.text import norm

QUOTE_MIN = 12
QUOTE_MAX = 200

FieldType = Literal["string", "integer", "number", "boolean", "object", "array", "unknown"]
Location = Literal["header", "path", "query", "body", "response"]
Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
Kind = Literal["endpoint", "schema", "overview"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(_Strict):
    """A 1-based page and a verbatim quote of 12-200 characters after normalization."""

    page: int = Field(ge=1)
    quote: str

    @field_validator("quote")
    @classmethod
    def _quote_length(cls, quote: str) -> str:
        length = len(norm(quote))
        if not QUOTE_MIN <= length <= QUOTE_MAX:
            raise ValueError(
                f"normalized quote has {length} chars; must be {QUOTE_MIN}-{QUOTE_MAX}"
            )
        return quote


class FieldSpec(_Strict):
    """One documented parameter or property, with its citation."""

    name: str
    location: Location
    required: bool | None
    type: FieldType
    type_raw: str
    enum: list[str] | None = None
    enum_citation: Citation | None = None
    description: str | None = None
    example: str | int | float | bool | None = None
    min_version: str | None = None
    schema_ref: str | None = None
    citation: Citation


class Sample(_Strict):
    """A request or response sample copied verbatim from the document."""

    raw: str
    citation: Citation


class Samples(_Strict):
    """The optional request and response samples of a section."""

    request: Sample | None = None
    response: Sample | None = None


class Extraction(_Strict):
    """Provenance of an AI-produced contract."""

    producer: str
    mode: str
    prompt_version: str
    attempt: int = Field(ge=1)
    bob_task_ref: str | None = None


class ContractSection(_Strict):
    """One section's cited contract; endpoints need method and path, schemas forbid them."""

    schema_version: Literal[1]
    section_id: str = Field(pattern=r"^S-\d{1,2}\.\d{1,2}$")
    kind: Kind
    title: str
    method: Method | None = None
    path: str | None = None
    permission_key: str | None = None
    citations: dict[str, Citation] = Field(default_factory=dict)
    fields: list[FieldSpec] = Field(default_factory=list)
    definitions: list[FieldSpec] = Field(default_factory=list)
    samples: Samples = Field(default_factory=Samples)
    extraction: Extraction

    @model_validator(mode="after")
    def _kind_rules(self) -> "ContractSection":
        if self.kind == "endpoint" and (self.method is None or self.path is None):
            raise ValueError("endpoint sections require method and path")
        if self.kind == "schema" and (self.method is not None or self.path is not None):
            raise ValueError("schema sections must not have method or path")
        return self

    @classmethod
    def load(cls, path: Path) -> "ContractSection":
        """Read a contract file; reject unsupported schema versions with a clear message."""
        data: Any = load_json(path)
        version = data.get("schema_version") if isinstance(data, dict) else None
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"{path.name}: schema_version {version} is not supported "
                f"(expected {SCHEMA_VERSION})"
            )
        return cls.model_validate(data)

    def to_json_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dict with fields and definitions sorted by (location, name)."""
        data = self.model_dump(mode="json")
        for key in ("fields", "definitions"):
            data[key] = sorted(data[key], key=lambda f: (f["location"], f["name"]))
        return data

    def dump(self, path: Path) -> None:
        """Write deterministic JSON (sorted keys and lists, LF, trailing newline)."""
        dump_json(path, self.to_json_dict())
