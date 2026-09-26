"""SARIF 2.1.0 export of code-located findings, for GitHub code scanning."""

from typing import Any

from specproof import __version__

LEVEL = {"high": "error", "medium": "warning", "low": "note", "info": "note"}
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def to_sarif(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """One result per finding with code evidence; sorted and deterministic."""
    results = []
    rules: dict[str, dict[str, Any]] = {}
    for finding in sorted(findings, key=lambda f: str(f["id"])):
        code = next(
            (e for e in finding["evidence"] if e.get("kind") == "code" and e.get("file")), None
        )
        if code is None:
            continue
        rules.setdefault(finding["type"], {"id": finding["type"], "name": finding["type"]})
        location: dict[str, Any] = {"artifactLocation": {"uri": code["file"]}}
        if code.get("line"):
            location["region"] = {"startLine": int(code["line"])}
        results.append(
            {
                "ruleId": finding["type"],
                "level": LEVEL.get(finding["severity"], "note"),
                "message": {"text": finding["title"]},
                "locations": [{"physicalLocation": location}],
                "partialFingerprints": {"specproofFindingId": finding["id"]},
            }
        )
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "SpecProof",
                        "version": __version__,
                        "rules": [rules[k] for k in sorted(rules)],
                    }
                },
                "results": results,
            }
        ],
    }
