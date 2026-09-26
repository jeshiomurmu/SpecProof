"""Field-level diff of our verified export against the community OpenAPI. Pure, offline."""

from typing import Any

import yaml

from specproof.compare.openapi_export import CITATION_KEY, SECTION_KEY
from specproof.compare.paths import normalize_path as norm_path
from specproof.models.findings import Evidence, Finding, FindingSeverity, FindingType

METHODS = ("get", "post", "put", "patch", "delete")
_SEVERITY: dict[FindingType, FindingSeverity] = {
    "COMMUNITY_REQUIRED_MISMATCH": "medium",
    "COMMUNITY_TYPE_MISMATCH": "medium",
    "COMMUNITY_ENUM_MISMATCH": "medium",
    "COMMUNITY_MISSING_FIELD": "low",
    "COMMUNITY_EXTRA_FIELD": "info",
    "COMMUNITY_MISSING_ENDPOINT": "medium",
}


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _pointer(*tokens: str) -> str:
    return "#/" + "/".join(_escape(t) for t in tokens)


def _resolve(spec: dict[str, Any], node: Any, pointer: str) -> tuple[Any, str]:
    """Follow local $ref chains; returns the target node and its JSON pointer."""
    seen: set[str] = set()
    while isinstance(node, dict) and isinstance(node.get("$ref"), str):
        ref = node["$ref"]
        if not ref.startswith("#/") or ref in seen:
            break
        seen.add(ref)
        target: Any = spec
        for raw in ref[2:].split("/"):
            key = raw.replace("~1", "/").replace("~0", "~")
            target = target.get(key) if isinstance(target, dict) else None
        node, pointer = target, ref
    return node, pointer


def _operations(spec: dict[str, Any]) -> dict[tuple[str, str], tuple[str, str, dict[str, Any]]]:
    ops: dict[tuple[str, str], tuple[str, str, dict[str, Any]]] = {}
    for path, item in sorted((spec.get("paths") or {}).items()):
        for method in METHODS:
            if isinstance(item, dict) and isinstance(item.get(method), dict):
                ops[(method.upper(), norm_path(path))] = (path, method, item[method])
    return ops


def _body(
    spec: dict[str, Any], path: str, method: str, op: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    pointer = _pointer("paths", path, method, "requestBody")
    body, pointer = _resolve(spec, op.get("requestBody"), pointer)
    if not isinstance(body, dict):
        return {}, pointer
    pointer += "/content/application~1json/schema"
    schema = ((body.get("content") or {}).get("application/json") or {}).get("schema")
    schema, pointer = _resolve(spec, schema, pointer)
    return (schema if isinstance(schema, dict) else {}), pointer


def line_index(text: str) -> dict[str, int]:
    """Map every JSON pointer in a YAML document to its 1-based line number."""
    lines: dict[str, int] = {}

    def walk(node: yaml.Node, pointer: str) -> None:
        lines[pointer] = node.start_mark.line + 1
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                walk(value, f"{pointer}/{_escape(str(key.value))}")
        elif isinstance(node, yaml.SequenceNode):
            for i, value in enumerate(node.value):
                walk(value, f"{pointer}/{i}")

    root = yaml.compose(text)
    if root is not None:
        walk(root, "#")
    return lines


class _Differ:
    def __init__(self, lines: dict[str, int], label: str) -> None:
        self.lines = lines
        self.label = label
        self.findings: dict[str, Finding] = {}

    def add(
        self,
        type_: FindingType,
        section: str,
        field: str | None,
        title: str,
        cite: dict[str, Any] | None,
        pointer: str,
    ) -> None:
        evidence = [
            Evidence(kind="code", file=self.label, line=self.lines.get(pointer), snippet=pointer)
        ]
        if cite:
            evidence.append(Evidence(kind="doc", page=int(cite["page"]), quote=str(cite["quote"])))
        evidence.sort(key=Evidence.canonical)
        fid = Finding.make_id(type_, section, field, evidence)
        self.findings[fid] = Finding(
            id=fid,
            type=type_,
            severity=_SEVERITY[type_],
            section_id=section,
            title=title,
            evidence=evidence,
        )


def _req(flag: bool) -> str:
    return "required (T)" if flag else "optional (F)"


def _compare_body(
    d: _Differ, section: str, ours: dict[str, Any], theirs: dict[str, Any], ptr: str
) -> None:
    our_props, their_props = ours.get("properties") or {}, theirs.get("properties") or {}
    our_req, their_req = set(ours.get("required") or []), set(theirs.get("required") or [])
    for name in sorted(set(our_props) | set(their_props)):
        mine, other = our_props.get(name), their_props.get(name)
        cite = (mine or {}).get(CITATION_KEY)
        page = f"page {cite['page']}" if cite else "the PDF"
        if other is None:
            d.add(
                "COMMUNITY_MISSING_FIELD",
                section,
                name,
                f"Community spec omits `{name}`, which the PDF documents on {page}.",
                cite,
                ptr + "/properties",
            )
            continue
        if mine is None:
            d.add(
                "COMMUNITY_EXTRA_FIELD",
                section,
                name,
                f"Community spec has `{name}`, which the PDF section does not document.",
                None,
                f"{ptr}/properties/{_escape(name)}",
            )
            continue
        if (name in our_req) != (name in their_req):
            theirs_says = "required" if name in their_req else "optional"
            d.add(
                "COMMUNITY_REQUIRED_MISMATCH",
                section,
                name,
                f"Community spec marks `{name}` as {theirs_says}; "
                f"the PDF row on {page} marks it {_req(name in our_req)}.",
                cite,
                ptr + "/required",
            )
        if "type" in mine and "type" in other and mine["type"] != other["type"]:
            d.add(
                "COMMUNITY_TYPE_MISMATCH",
                section,
                name,
                f"Community spec types `{name}` as {other['type']}; the PDF on {page} "
                f"types it as {mine['type']}.",
                cite,
                f"{ptr}/properties/{_escape(name)}/type",
            )
        if "enum" in mine and "enum" in other and set(mine["enum"]) != set(other["enum"]):
            missing = sorted(set(mine["enum"]) - set(other["enum"]))
            extra = sorted(set(other["enum"]) - set(mine["enum"]))
            d.add(
                "COMMUNITY_ENUM_MISMATCH",
                section,
                name,
                f"Community enum for `{name}` differs from the PDF on {page}: "
                f"missing {missing or 'none'}, extra {extra or 'none'}.",
                cite,
                f"{ptr}/properties/{_escape(name)}/enum",
            )


def diff(
    ours: dict[str, Any], theirs: dict[str, Any], theirs_text: str, label: str
) -> list[Finding]:
    """COMMUNITY_* findings, each with our PDF citation and a pointer into the community file."""
    d = _Differ(line_index(theirs_text), label)
    their_ops = _operations(theirs)
    for key, (path, method, op) in sorted(_operations(ours).items()):
        section = str(op.get(SECTION_KEY, "?"))
        if key not in their_ops:
            d.add(
                "COMMUNITY_MISSING_ENDPOINT",
                section,
                None,
                f"Community spec has no operation for {key[0]} {path}, which the PDF documents.",
                op.get(CITATION_KEY),
                "#/paths",
            )
            continue
        our_body, _ = _body(ours, path, method, op)
        t_path, t_method, t_op = their_ops[key]
        their_body, pointer = _body(theirs, t_path, t_method, t_op)
        if our_body or their_body:
            _compare_body(d, section, our_body, their_body, pointer)
    return [d.findings[k] for k in sorted(d.findings)]
