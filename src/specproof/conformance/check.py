"""Compare the client's endpoint inventory with what the specification documents."""

from collections.abc import Mapping
from typing import Any

from specproof.conformance.inventory import EndpointRef
from specproof.models.contract import ContractSection
from specproof.models.findings import Evidence, Finding
from specproof.verify.structure import norm_path


def _code(ref: EndpointRef, label: str) -> Evidence:
    return Evidence(kind="code", file=f"{label}/{ref.file}", line=ref.line, snippet=ref.snippet)


def _documented(
    index: list[Mapping[str, Any]], contracts: list[ContractSection]
) -> dict[str, dict[str, tuple[str, Evidence]]]:
    """norm path -> method -> (section id, doc evidence) from segmenter hints and contracts.

    Hints cover every endpoint section, so paths from not-yet-extracted sections still count
    as documented; verified contracts add the verbatim quote."""
    cites = {c.section_id: c.citations.get("path") for c in contracts}
    documented: dict[str, dict[str, tuple[str, Evidence]]] = {}
    for entry in index:
        path, method = entry.get("path_hint"), entry.get("method_hint")
        if entry.get("kind") != "endpoint" or not path or not method:
            continue
        sid = str(entry["section_id"])
        cite = cites.get(sid)
        evidence = (
            Evidence(kind="doc", page=cite.page, quote=cite.quote)
            if cite is not None
            else Evidence(kind="doc", page=int(entry["page_start"]))
        )
        documented.setdefault(norm_path(str(path)), {})[str(method).upper()] = (sid, evidence)
    return documented


def check_inventory(
    refs: list[EndpointRef],
    index: list[Mapping[str, Any]],
    contracts: list[ContractSection],
    client_label: str,
) -> tuple[list[Finding], list[dict[str, Any]]]:
    """CLIENT_UNDOCUMENTED_ENDPOINT / CLIENT_METHOD_MISMATCH findings, plus uncheckable refs."""
    documented = _documented(index, contracts)
    findings: dict[str, Finding] = {}
    uncheckable: list[dict[str, Any]] = []
    for ref in refs:
        if ref.dynamic or not ref.path_norm:
            uncheckable.append(
                {"file": ref.file, "line": ref.line, "method": ref.method, "path": ref.path_norm}
            )
            continue
        methods = documented.get(ref.path_norm)
        code = _code(ref, client_label)
        if methods is None:
            title = (
                f"Client calls {ref.method} {ref.path_norm}, "
                "which the specification does not document."
            )
            fid = Finding.make_id("CLIENT_UNDOCUMENTED_ENDPOINT", "-", ref.path_norm, [code])
            findings[fid] = Finding(
                id=fid,
                type="CLIENT_UNDOCUMENTED_ENDPOINT",
                severity="medium",
                section_id="-",
                title=title,
                evidence=[code],
            )
        elif ref.method != "UNKNOWN" and ref.method not in methods:
            sid, doc = sorted(methods.values(), key=lambda v: v[0])[0]
            evidence = sorted([code, doc], key=Evidence.canonical)
            title = (
                f"Client calls {ref.method} {ref.path_norm}; the specification documents "
                f"{', '.join(sorted(methods))} for this path."
            )
            fid = Finding.make_id("CLIENT_METHOD_MISMATCH", sid, ref.path_norm, evidence)
            findings[fid] = Finding(
                id=fid,
                type="CLIENT_METHOD_MISMATCH",
                severity="high",
                section_id=sid,
                title=title,
                evidence=evidence,
            )
    return [findings[k] for k in sorted(findings)], uncheckable
