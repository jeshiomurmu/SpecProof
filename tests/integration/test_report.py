import re
from typing import Any

import pytest

from specproof.report.html import ReportState, fraction, render
from specproof.report.sarif import to_sarif


def _finding(
    fid: str, type_: str, evidence: list[dict[str, Any]], status: str = "CANDIDATE"
) -> dict[str, Any]:
    return {
        "id": fid,
        "type": type_,
        "severity": "high",
        "section_id": "S-2.2",
        "title": f"title {fid}",
        "evidence": evidence,
        "review": {"status": status},
    }


DOC = {"kind": "doc", "page": 5, "quote": '"color": "Grean",'}
CODE = {"kind": "code", "file": "client/models.py", "line": 7, "snippet": "class Widget"}
FINDINGS = [
    _finding("F-00000001", "SPEC_SELF_INCONSISTENCY", [DOC], "CONFIRMED"),
    _finding("F-00000002", "CLIENT_SAMPLE_REJECTED", [DOC, CODE]),
    _finding("F-00000003", "COMMUNITY_TYPE_MISMATCH", [DOC], "REJECTED"),
]
METRICS = {
    "endpoint_coverage": {"numerator": 3, "denominator": 4, "value": 0.75},
    "citation_grounding_rate": {"numerator": 26, "denominator": 28, "value": 0.9285},
    "final_verified_rate": {"numerator": 2, "denominator": 3, "value": 0.6666},
    "audited_precision": {"value": None, "reason": "blind audit not scored yet"},
    "spec_findings_confirmed": {"by_type": {}, "total": 1},
    "spec_findings_candidate": {"by_type": {}, "total": 1},
    "community_discrepancies_candidate": {"by_type": {}, "total": 1},
    "community_discrepancies_confirmed": {"by_type": {}, "total": 0},
    "client_findings_candidate": {"by_type": {}, "total": 1},
    "client_findings_confirmed": {"by_type": {}, "total": 0},
}


@pytest.fixture(scope="module")
def html() -> str:
    state = ReportState(
        spec_title="Widget API",
        source_sha="d204c8b9ad4d329f",
        metrics=METRICS,
        findings=FINDINGS,
        endpoints=[
            {
                "section_id": "S-2.2",
                "method": "POST",
                "path": "/api/v1/widgets",
                "status": "VERIFIED_WITH_SPEC_FINDINGS",
                "attempts": 1,
                "items": 11,
                "grounded": 11,
                "row_ok": 4,
                "row_checked": 4,
            }
        ],
        funnel=[{"label": "After attempt 1", "verified": 1, "total": 3}],
        lineage=[
            {
                "artifact": "artifacts/status.json",
                "sha256": "ab" * 32,
                "stage": "classify",
                "producer": "deterministic",
            }
        ],
        content_hash="0" * 64,
    )
    return render(state)


@pytest.mark.integration
def test_RPT_001_renders(html: str) -> None:
    assert html.startswith("<!doctype html>")
    assert "<h1>" in html and "Widget API" in html


@pytest.mark.integration
def test_RPT_002_self_contained(html: str) -> None:
    assert not re.search(r"""(src|href)\s*=\s*["']https?://""", html.split('id="prior-art"')[0])
    assert "<link" not in html and "@import" not in html and "fetch(" not in html


@pytest.mark.integration
def test_RPT_003_every_finding_appears(html: str) -> None:
    for finding in FINDINGS:
        assert finding["id"] in html
    assert "CONFIRMED" in html and "REJECTED" in html


@pytest.mark.integration
def test_RPT_004_evidence_shown(html: str) -> None:
    assert "page 5" in html
    assert "&#34;color&#34;: &#34;Grean&#34;," in html or '"color": "Grean",' in html
    assert "client/models.py:7" in html


@pytest.mark.integration
def test_RPT_005_sarif() -> None:
    sarif = to_sarif(FINDINGS)
    assert sarif["version"] == "2.1.0"
    results = sarif["runs"][0]["results"]
    assert [r["ruleId"] for r in results] == ["CLIENT_SAMPLE_REJECTED"]
    location = results[0]["locations"][0]["physicalLocation"]
    assert location == {"artifactLocation": {"uri": "client/models.py"}, "region": {"startLine": 7}}
    assert results[0]["level"] == "error"


@pytest.mark.integration
def test_RPT_006_denominators_shown(html: str) -> None:
    assert "3/4 (75.0%)" in html
    assert "26/28 (92.8%)" in html
    assert "pending - blind audit not scored yet" in html
    assert fraction({"numerator": 2, "denominator": 3, "value": 0.6666}) == "2/3 (66.6%)"


@pytest.mark.integration
def test_RPT_008_endpoint_row_values(html: str) -> None:
    assert "<td>11</td><td>11</td><td>4/4</td>" in html
    assert "built-in method" not in html and " at 0x" not in html


@pytest.mark.integration
def test_RPT_007_no_timestamps_in_body(html: str) -> None:
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", html)
    assert "manifest.json" in html
