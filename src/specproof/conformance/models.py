"""C2: Pydantic model introspection and diff against documented response fields."""

import enum
import types
import typing
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from specproof.conformance.mapping import Mapping
from specproof.models.contract import ContractSection, FieldSpec
from specproof.models.findings import Evidence, Finding


@dataclass(frozen=True)
class ModelField:
    """One model field as the wire sees it: key (alias or name), required, type, enum."""

    key: str
    required: bool
    type: str
    enum: tuple[str, ...] | None


def _scalar(ann: Any) -> tuple[str, tuple[str, ...] | None]:
    if isinstance(ann, type):
        if issubclass(ann, enum.Enum):
            values = tuple(str(m.value) for m in ann)
            return ("string" if issubclass(ann, str) else "unknown"), values
        for base, name in ((bool, "boolean"), (int, "integer"), (float, "number"), (str, "string")):
            if issubclass(ann, base):
                return name, None
        if issubclass(ann, BaseModel | dict):
            return "object", None
        if issubclass(ann, list | tuple | set):
            return "array", None
    return "unknown", None


def annotation_type(ann: Any) -> tuple[str, tuple[str, ...] | None]:
    """Map a Python annotation to the contract type vocabulary (Optional[X] -> X)."""
    origin = typing.get_origin(ann)
    args = [a for a in typing.get_args(ann) if a is not type(None)]
    if origin in (typing.Union, types.UnionType):
        return annotation_type(args[0]) if len(args) == 1 else ("unknown", None)
    if origin is typing.Literal:
        values = tuple(str(a) for a in typing.get_args(ann))
        return (
            "string" if all(isinstance(a, str) for a in typing.get_args(ann)) else "unknown"
        ), values
    if origin in (list, tuple, set):
        return "array", None
    if origin is dict:
        return "object", None
    if origin is typing.Annotated:
        return annotation_type(typing.get_args(ann)[0])
    return _scalar(ann)


def describe_model(model: type[BaseModel]) -> list[ModelField]:
    """The model's fields from model_fields, sorted by wire key."""
    fields = []
    for name, info in model.model_fields.items():
        type_, values = annotation_type(info.annotation)
        fields.append(ModelField(info.alias or name, info.is_required(), type_, values))
    return sorted(fields, key=lambda f: f.key)


def _doc_fields(contract: ContractSection) -> dict[str, FieldSpec]:
    fields: dict[str, FieldSpec] = {}
    for spec in sorted(contract.fields, key=lambda f: f.name):
        if spec.location != "response":
            continue
        name = spec.name.removeprefix("data.")
        if "." not in name and "[" not in name:
            fields.setdefault(name, spec)
    return fields


def diff_model(
    fields: list[ModelField], mapping: Mapping, contract: ContractSection, client_label: str
) -> list[Finding]:
    """CLIENT_REQUIRES_UNDOCUMENTED_FIELD and CLIENT_TYPE_MISMATCH for one mapped model."""
    documented = _doc_fields(contract)
    code = Evidence(
        kind="code",
        file=f"{client_label}/{mapping.file}",
        line=mapping.line,
        snippet=f"class {mapping.class_name}",
    )
    findings: dict[str, Finding] = {}
    for field in fields:
        doc = documented.get(field.key)
        if doc is None:
            if field.required:
                title = (
                    f"Model {mapping.class_name} requires `{field.key}`, which the "
                    f"documented response of {contract.section_id} does not contain."
                )
                _add(
                    findings,
                    "CLIENT_REQUIRES_UNDOCUMENTED_FIELD",
                    "high",
                    contract,
                    field.key,
                    title,
                    [code],
                )
            continue
        if "unknown" in (doc.type, field.type) or doc.type == field.type:
            continue
        evidence = sorted(
            [code, Evidence(kind="doc", page=doc.citation.page, quote=doc.citation.quote)],
            key=Evidence.canonical,
        )
        title = (
            f"Model {mapping.class_name} types `{field.key}` as {field.type}; the PDF on page "
            f"{doc.citation.page} documents it as {doc.type}."
        )
        _add(findings, "CLIENT_TYPE_MISMATCH", "medium", contract, field.key, title, evidence)
    return [findings[k] for k in sorted(findings)]


def _add(
    findings: dict[str, Finding],
    type_: Any,
    severity: Any,
    contract: ContractSection,
    field: str,
    title: str,
    evidence: list[Evidence],
) -> None:
    fid = Finding.make_id(type_, contract.section_id, field, evidence)
    findings[fid] = Finding(
        id=fid,
        type=type_,
        severity=severity,
        section_id=contract.section_id,
        title=title,
        evidence=evidence,
    )
