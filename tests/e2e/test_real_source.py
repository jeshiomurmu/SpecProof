import json
from pathlib import Path
from typing import Any

import pytest

from specproof.config import Paths
from specproof.ingest.extractors import Page, select_extractor
from specproof.ingest.segment import segment
from specproof.models.manifest import find_record
from specproof.util.hashing import sha256_file
from specproof.util.io_pages import read_pages
from specproof.util.text import row_tokens

PIN = "d204c8b9ad4d329f6c89e71ebb5ccf446bcc30d2668673011bbe99a909a6a534"


@pytest.fixture(scope="module")
def real_pages(repo_root: Path) -> list[Page]:
    """Use the pipeline's pages.jsonl when the manifest ties it to the pinned PDF, else extract."""
    paths = Paths.from_root(repo_root)
    record = find_record(paths.manifest, paths.rel(paths.pages))
    if (
        record is not None
        and paths.pages.exists()
        and record.producer.extractor == "pdfplumber"
        and record.inputs[0].sha256 == PIN
        and record.sha256 == sha256_file(paths.pages)
    ):
        return read_pages(paths.pages)
    return select_extractor("auto").extract(paths.spec_pdf)


@pytest.mark.real_source
def test_ING_R01_page_14_first_name_row(real_pages: list[Page]) -> None:
    page14 = real_pages[13]
    assert page14.number == 14
    rows = [row_tokens(line) for line in page14.text.splitlines()]
    assert ("first_name", "T", "String") in rows


@pytest.mark.real_source
def test_ING_R02_page_count_and_pin(real_pages: list[Page], repo_root: Path) -> None:
    assert len(real_pages) == 194
    assert sha256_file(repo_root / "artifacts" / "work" / "spec.pdf") == PIN


@pytest.fixture(scope="module")
def real_index(real_pages: list[Page]) -> dict[str, dict[str, Any]]:
    return {s.entry["section_id"]: s.entry for s in segment(real_pages)}


@pytest.mark.real_source
def test_SEG_R01_at_least_107_endpoint_sections(real_index: dict[str, dict[str, Any]]) -> None:
    endpoints = [e for e in real_index.values() if e["kind"] == "endpoint"]
    assert len(endpoints) >= 107


@pytest.mark.real_source
def test_SEG_R02_schema_section_4_1(real_index: dict[str, dict[str, Any]]) -> None:
    s41 = real_index["S-4.1"]
    assert s41["kind"] == "schema"
    assert s41["page_start"] <= 52 <= s41["page_end"]


def _require_contracts(repo_root: Path) -> None:
    if not list((repo_root / "artifacts" / "contract").glob("S-*.json")):
        pytest.skip("no extracted contracts yet (T07-T08 run in IBM Bob)")


@pytest.mark.real_source
def test_E2E_R01_visit_reason_inconsistency_reproduced(repo_root: Path) -> None:
    _require_contracts(repo_root)
    findings = json.loads((repo_root / "artifacts" / "findings" / "spec.json").read_text("utf-8"))
    for section, pages in (("S-4.2", {52, 56}), ("S-4.5", {52, 63})):
        matches = [
            f
            for f in findings
            if f["type"] == "SPEC_SELF_INCONSISTENCY"
            and f["section_id"] == section
            and "visit_reason" in f["title"]
        ]
        assert matches, section
        assert pages <= {e["page"] for e in matches[0]["evidence"]}


@pytest.mark.real_source
def test_E2E_R02_endpoint_coverage(repo_root: Path) -> None:
    _require_contracts(repo_root)
    metrics = json.loads((repo_root / "artifacts" / "metrics.json").read_text("utf-8"))
    assert metrics["endpoint_coverage"]["value"] >= 0.90


@pytest.mark.real_source
def test_E2E_R03_determinism_on_real_artifacts(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil
    import sys

    from typer.testing import CliRunner

    from specproof.cli import app

    _require_contracts(repo_root)
    sys.path.insert(0, str(Path(__file__).parent))
    from test_pipeline_synthetic import artifact_hashes

    runs = []
    for name in ("a", "b"):
        root = tmp_path / name
        (root / "artifacts").mkdir(parents=True)
        for rel in ("artifacts/contract", "artifacts/conformance", "artifacts/work"):
            source = repo_root / rel
            if source.exists():
                shutil.copytree(source, root / rel, ignore=shutil.ignore_patterns("replay-venv"))
        shutil.copytree(repo_root / "eval", root / "eval")
        shutil.copytree(repo_root / "sources", root / "sources")
        (root / "artifacts" / "conformance" / "test_sample_replay.py").unlink(missing_ok=True)
        monkeypatch.chdir(root)
        runner = CliRunner()
        client = "artifacts/work/py-unifi-access"
        for args in (
            ["ingest"],
            ["segment"],
            ["verify", "--report-only"],
            ["classify"],
            ["export-openapi"],
            ["compare", "--community"],
            ["conform", "--client", client, "--python", sys.executable],
            ["report"],
        ):
            runner.invoke(app, args)
        runs.append(artifact_hashes(root))
    differences = sorted(
        k for k in runs[0].keys() | runs[1].keys() if runs[0].get(k) != runs[1].get(k)
    )
    identical = len(runs[0].keys() & runs[1].keys()) - len(differences)
    result = {
        "runs": 2,
        "total": len(runs[0].keys() | runs[1].keys()),
        "identical": identical,
        "differences": differences,
    }
    from datetime import UTC, datetime

    from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
    from specproof.util.io_json import dump_json

    target = repo_root / "artifacts" / "determinism.json"
    dump_json(target, result)
    append_record(
        repo_root / "artifacts" / "manifest.json",
        ManifestRecord(
            artifact="artifacts/determinism.json",
            sha256=sha256_file(target),
            stage="determinism",
            producer=Producer(kind="deterministic", tool="pytest E2E-R03"),
            inputs=[
                InputRef(
                    path="artifacts/sections_index.json",
                    sha256=sha256_file(repo_root / "artifacts" / "sections_index.json"),
                )
            ],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )
    assert differences == []


@pytest.mark.real_source
def test_CNF_R01_client_inventory_has_11_paths(repo_root: Path) -> None:
    from specproof.conformance.inventory import scan_endpoints

    client = repo_root / "artifacts" / "work" / "py-unifi-access"
    refs = scan_endpoints(client)
    developer = {r.path_norm for r in refs if r.path_norm.startswith("/api/v1/developer/")}
    assert len(developer) == 11
    assert all("tests/" not in r.file for r in refs)


@pytest.mark.real_source
def test_SEG_R03_hints_section_3_2(real_index: dict[str, dict[str, Any]]) -> None:
    s32 = real_index["S-3.2"]
    assert (s32["method_hint"], s32["path_hint"]) == ("POST", "/api/v1/developer/users")
