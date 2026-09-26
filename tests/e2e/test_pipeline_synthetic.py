import hashlib
import shutil
import sys
import time
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specproof.cli import app
from specproof.util.io_json import load_json

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]
COMMITTED = (
    "artifacts/sections_index.json",
    "artifacts/verification",
    "artifacts/status.json",
    "artifacts/findings",
    "artifacts/openapi.specproof.yaml",
    "artifacts/conformance/test_sample_replay.py",
    "artifacts/report/index.html",
    "artifacts/findings.json",
    "artifacts/findings.sarif",
    "artifacts/metrics.json",
    "artifacts/eval_result.json",
    "demo/index.html",
)


def run_pipeline(root: Path, synthetic_pdf: Path) -> float:
    """The whole deterministic pipeline on FX-01/02/04/05 inside root; returns seconds."""
    work = root / "artifacts" / "work"
    work.mkdir(parents=True)
    shutil.copyfile(synthetic_pdf, work / "spec.pdf")
    shutil.copyfile(FIXTURES / "community_min.yaml", work / "community_openapi.yaml")
    shutil.copytree(FIXTURES / "contracts_good", root / "artifacts" / "contract")
    shutil.copytree(FIXTURES / "mini_client", root / "client")
    shutil.copytree(REPO / "eval", root / "eval")
    (root / "artifacts" / "conformance").mkdir()
    mapping = [
        {
            "section_id": "S-2.3",
            "model": "models.Widget",
            "json_path": "data",
            "code": {"file": "models.py", "line": 7},
        }
    ]
    (root / "artifacts" / "conformance" / "mapping.yaml").write_text(yaml.safe_dump(mapping))
    runner = CliRunner()
    start = time.perf_counter()
    for args in (
        ["ingest"],
        ["segment"],
        ["verify", "--report-only"],
        ["classify"],
        ["export-openapi"],
        ["compare", "--community"],
        ["conform", "--client", "client", "--python", sys.executable],
        ["report"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, (args, result.output)
    runner.invoke(app, ["eval"])
    return time.perf_counter() - start


def artifact_hashes(root: Path) -> dict[str, str]:
    """sha256 of every committed-type artifact under root."""
    hashes = {}
    for rel in COMMITTED:
        path = root / rel
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in files:
            if file.is_file():
                hashes[file.relative_to(root).as_posix()] = hashlib.sha256(
                    file.read_bytes()
                ).hexdigest()
    return hashes


@pytest.mark.e2e
def test_E2E_001_synthetic_pipeline(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run_pipeline(tmp_path, synthetic_pdf)
    status = load_json(tmp_path / "artifacts" / "status.json")
    assert {sid: row["status"] for sid, row in status.items()} == {
        "S-2.1": "VERIFIED",
        "S-2.2": "VERIFIED_WITH_SPEC_FINDINGS",
        "S-2.3": "VERIFIED",
        "S-2.4": "VERIFIED_WITH_SPEC_FINDINGS",
    }
    html = (tmp_path / "artifacts" / "report" / "index.html").read_text(encoding="utf-8")
    assert "Grean" in html and "SPEC_SELF_INCONSISTENCY" in html
    types = {f["type"] for f in load_json(tmp_path / "artifacts" / "findings.json")}
    assert {
        "SPEC_SELF_INCONSISTENCY",
        "COMMUNITY_MISSING_ENDPOINT",
        "CLIENT_SAMPLE_REJECTED",
    } <= types


@pytest.mark.e2e
def test_E2E_002_determinism(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs = []
    for name in ("a", "b"):
        root = tmp_path / name
        root.mkdir()
        monkeypatch.chdir(root)
        run_pipeline(root, synthetic_pdf)
        runs.append(artifact_hashes(root))
    assert len(runs[0]) > 20
    differences = sorted(k for k in runs[0] if runs[0][k] != runs[1].get(k))
    assert differences == []
    assert runs[0].keys() == runs[1].keys()


@pytest.mark.e2e
def test_E2E_003_performance(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run_pipeline(tmp_path, synthetic_pdf) < 10.0
