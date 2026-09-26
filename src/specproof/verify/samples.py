"""V3 rules: parse document samples and validate them against the extracted contract.

No format checks: placeholders such as {{host}} or masked tokens never raise issues.
"""

import json
import re
from typing import Any

from jsonschema import Draft202012Validator

from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.models.verification import Issue

_JSON_TYPES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "object": "object",
    "array": "array",
}
_DATA_RAW = re.compile(r"(?<!\S)(?:--data(?:-raw|-binary)?|-d)\s+(['\"])")
# The document's responses always carry code and msg; data is absent or null for
# operations that return nothing (e.g. DELETE), so it is not required.
ENVELOPE_REQUIRED = ("code", "msg")
_REQUIRED_NAME = re.compile(r"^'(.+)' is a required property$")
_V3 = {"required": "V3_REQUIRED_MISSING", "type": "V3_TYPE_MISMATCH", "enum": "V3_ENUM_VIOLATION"}
_SEVERITY = {"required": "warning", "type": "error", "enum": "error"}


def extract_payload(raw: str) -> str | None:
    """JSON text of a sample: the --data-raw payload of a curl command, the raw text itself
    for a plain JSON sample, or None for a curl command without a body (e.g. GET/DELETE)."""
    match = _DATA_RAW.search(raw)
    if match is None:
        return None if raw.lstrip().startswith("curl") else raw.strip()
    quote = match.group(1)
    start = match.end()
    if raw[start:].lstrip(" ").startswith(quote):
        return None
    # The body ends at the first closing bracket followed by the closing quote, so a
    # second curl example later in the same block is not swallowed.
    closing = re.search(r"[}\]]\s*" + re.escape(quote), raw[start:])
    if closing is not None:
        return raw[start : start + closing.start() + 1].strip() or None
    end = raw.rfind(quote)
    payload = raw[start:end].strip() if end >= start else raw[start:].strip()
    return payload or None


def join_wrapped_strings(text: str) -> str:
    """Remove line breaks (and the indentation after them) inside JSON string literals.

    A raw newline is illegal inside a JSON string, so one there can only be the PDF code
    box wrapping a long value onto the next line."""
    out: list[str] = []
    in_string = escaped = skipping = False
    for char in text:
        if skipping:
            if char in " \t":
                continue
            skipping = False
        if in_string:
            if char == "\n":
                skipping = True
                continue
            escaped = char == "\\" and not escaped
            if char == '"' and not escaped:
                in_string = False
        elif char == '"':
            in_string = True
        out.append(char)
    return "".join(out)


def _simple(fields: list[FieldSpec]) -> list[FieldSpec]:
    return sorted(
        (f for f in fields if "." not in f.name and "[" not in f.name), key=lambda f: f.name
    )


def build_schema(fields: list[FieldSpec], nullable: bool = False) -> dict[str, Any]:
    """Draft 2020-12 schema over top-level fields: types, enums, required; extra keys allowed.

    nullable=True also accepts null for every field; used when validating samples, because
    the document never states nullability."""
    properties: dict[str, Any] = {}
    for field in _simple(fields):
        prop: dict[str, Any] = {}
        if field.type in _JSON_TYPES:
            prop["type"] = (
                [_JSON_TYPES[field.type], "null"] if nullable else _JSON_TYPES[field.type]
            )
        if field.enum:
            prop["enum"] = [*field.enum, None] if nullable else list(field.enum)
        properties[field.name] = prop
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": True,
        "properties": properties,
        "required": sorted(f.name for f in _simple(fields) if f.required is True),
        "type": "object",
    }


def build_request_schema(contract: ContractSection) -> dict[str, Any]:
    """Schema for the request body fields of a contract."""
    return build_schema([f for f in contract.fields if f.location == "body"])


def _parse(text: str, which: str, citation: Citation) -> tuple[Any, list[Issue]]:
    try:
        return json.loads(join_wrapped_strings(text)), []
    except json.JSONDecodeError as exc:
        msg = f"{which} sample is not valid JSON: {exc.msg} (line {exc.lineno})"
        issue = Issue(
            code="V3_SAMPLE_UNPARSEABLE",
            severity="error",
            category="sample_conflict",
            message=msg,
            evidence=citation,
        )
        return None, [issue]


def _validate(instance: Any, schema: dict[str, Any], which: str, cite: Citation) -> list[Issue]:
    issues: list[Issue] = []
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda e: ([str(p) for p in e.absolute_path], e.validator),
    )
    for error in errors:
        kind = str(error.validator)
        if kind not in _V3:
            continue
        if kind == "required":
            # jsonschema raises one "required" error per missing property.
            named = _REQUIRED_NAME.match(str(error.message))
            names: list[str | None] = [named.group(1)] if named else [None]
        else:
            names = [str(error.absolute_path[0]) if error.absolute_path else None]
        for name in names:
            msg = f"{which} sample: {error.message}"
            issues.append(
                Issue(
                    code=_V3[kind],
                    severity=_SEVERITY[kind],
                    category="sample_conflict",
                    field=name,
                    message=msg,
                    evidence=cite,
                )
            )
    return issues


def _request_issues(contract: ContractSection, payload: Any, cite: Citation) -> list[Issue]:
    if not any(f.location == "body" for f in contract.fields):
        return []
    body = [f for f in contract.fields if f.location == "body"]
    issues = _validate(payload, build_schema(body, nullable=True), "request", cite)
    if isinstance(payload, dict):
        known = {f.name for f in contract.fields if f.location == "body"}
        for key in sorted(set(payload) - known):
            issues.append(
                Issue(
                    code="V3_UNKNOWN_FIELD",
                    severity="info",
                    category="info",
                    field=key,
                    message=f"request sample key {key!r} is not a documented body field",
                    evidence=cite,
                )
            )
    return issues


def _response_issues(contract: ContractSection, payload: Any, cite: Citation) -> list[Issue]:
    envelope = {
        "properties": {},
        "required": list(ENVELOPE_REQUIRED),
        "type": "object",
    }
    issues = _validate(payload, envelope, "response", cite)
    if not isinstance(payload, dict) or payload.get("data") is None:
        return issues
    response = [f for f in contract.fields if f.location == "response"]
    data = payload["data"]
    for spec in (f for f in response if f.name.lower() == "data"):
        # A "Data" row in a Response Body table describes the envelope's data value itself.
        schema = build_schema([spec.model_copy(update={"name": "data"})], nullable=True)
        schema["required"] = []
        for issue in _validate({"data": data}, schema, "response", cite):
            issues.append(issue.model_copy(update={"field": spec.name}))
    items = [f for f in response if f.name.lower() not in ("data", "code", "msg")]
    if not items:
        return issues
    schema = build_schema(items, nullable=True)
    for item in data if isinstance(data, list) else [data]:
        issues.extend(_validate(item, schema, "response data", cite))
    return issues


def validate_samples(contract: ContractSection) -> tuple[list[Issue], dict[str, int]]:
    """Run V3 on the request and response samples; return (issues, sample counts)."""
    issues: list[Issue] = []
    counts = {"samples": 0, "samples_parsed": 0}
    for which, sample in (
        ("request", contract.samples.request),
        ("response", contract.samples.response),
    ):
        text = extract_payload(sample.raw) if sample is not None else None
        if sample is None or text is None:
            continue
        counts["samples"] += 1
        payload, parse_issues = _parse(text, which, sample.citation)
        issues.extend(parse_issues)
        if parse_issues:
            continue
        counts["samples_parsed"] += 1
        check = _request_issues if which == "request" else _response_issues
        issues.extend(check(contract, payload, sample.citation))
    return sorted(issues, key=Issue.sort_key), counts
