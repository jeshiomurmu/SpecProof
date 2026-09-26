"""Export verified contract sections to OpenAPI 3.1, with PDF citations as x- extensions."""

import logging
import re
from typing import Any

from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.verify.samples import build_schema

log = logging.getLogger(__name__)
_COLON_PARAM = re.compile(r":([A-Za-z_]\w*)")
_TEMPLATE = re.compile(r"\{([^}/]+)\}")
CITATION_KEY = "x-specproof-citation"
SECTION_KEY = "x-specproof-section"


def openapi_path(path: str) -> str:
    """Leading '/', no query or trailing '/', and ':name' parameters written as '{name}'."""
    path = path.strip().split("?", 1)[0].rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return _COLON_PARAM.sub(r"{\1}", path)


def _cite(citation: Citation) -> dict[str, Any]:
    return {"page": citation.page, "quote": citation.quote}


def _schema(fields: list[FieldSpec]) -> dict[str, Any]:
    schema = build_schema(fields)
    schema.pop("$schema", None)
    by_name = {f.name: f for f in fields}
    for name, prop in schema["properties"].items():
        prop[CITATION_KEY] = _cite(by_name[name].citation)
        if by_name[name].description:
            prop["description"] = by_name[name].description
    return schema


def _parameters(contract: ContractSection, path: str) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    # OpenAPI requires path parameter names to match the template exactly; the document
    # sometimes prints them in another case (Id vs :id). Unmatched path rows are skipped.
    template = {name.lower(): name for name in _TEMPLATE.findall(path)}
    declared: set[tuple[str, str]] = set()
    for field in sorted(contract.fields, key=lambda f: (f.location, f.name)):
        if field.location not in ("header", "path", "query"):
            continue
        name = field.name
        if field.location == "path":
            if name.lower() not in template:
                continue
            name = template[name.lower()]
        if (field.location, name) in declared:
            continue
        declared.add((field.location, name))
        params.append(
            {
                "in": field.location,
                "name": name,
                "required": True if field.location == "path" else bool(field.required),
                "schema": build_schema([field])["properties"].get(field.name, {}),
                CITATION_KEY: _cite(field.citation),
            }
        )
    for name in template.values():
        if ("path", name) not in declared:
            params.append(
                {"in": "path", "name": name, "required": True, "schema": {"type": "string"}}
            )
    return params


def _operation(contract: ContractSection, path: str) -> dict[str, Any]:
    op: dict[str, Any] = {
        "summary": contract.title,
        SECTION_KEY: contract.section_id,
        "responses": {"200": {"description": "Success"}},
    }
    if "path" in contract.citations:
        op[CITATION_KEY] = _cite(contract.citations["path"])
    params = _parameters(contract, path)
    if params:
        op["parameters"] = params
    body = [f for f in contract.fields if f.location == "body"]
    if body:
        op["requestBody"] = {"content": {"application/json": {"schema": _schema(body)}}}
    response = [f for f in contract.fields if f.location == "response"]
    if response:
        envelope = {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "msg": {"type": "string"},
                "data": _schema(response),
            },
        }
        op["responses"]["200"]["content"] = {"application/json": {"schema": envelope}}
    return op


def export(contracts: list[ContractSection], verified_ids: list[str]) -> dict[str, Any]:
    """OpenAPI 3.1 document for verified sections only; the same inputs give the same dict."""
    allowed = set(verified_ids)
    paths: dict[str, dict[str, Any]] = {}
    schemas: dict[str, Any] = {}
    for contract in sorted(contracts, key=lambda c: c.section_id):
        if contract.section_id not in allowed:
            continue
        if contract.kind == "schema" and contract.definitions:
            schemas[contract.section_id] = _schema(contract.definitions)
            schemas[contract.section_id]["title"] = contract.title
        if contract.kind != "endpoint" or not contract.method or not contract.path:
            continue
        if "/" not in contract.path:
            log.warning(
                "%s: path %r is not a URL path; not exported", contract.section_id, contract.path
            )
            continue
        path = openapi_path(contract.path)
        paths.setdefault(path, {})[contract.method.lower()] = _operation(contract, path)
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "SpecProof verified contract", "version": "0.1.0"},
        "paths": paths,
    }
    if schemas:
        spec["components"] = {"schemas": schemas}
    return spec
