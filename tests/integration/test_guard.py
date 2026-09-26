import logging
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specproof.cli import app
from specproof.guard import protected_paths


def _git(repo: Path, *args: str) -> str:
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def tmp_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """FX-07: a temp repo with a base commit recorded in .specproof_task_base."""
    for rel in ("tests/test_a.py", "artifacts/contract/S-1.1.json", "src/specproof/verify/x.py"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    (tmp_path / ".specproof_task_base").write_text(_git(tmp_path, "rev-parse", "HEAD") + "\n")
    (tmp_path / ".specproof_extraction_task").write_text("")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.integration
def test_GRD_001_protected_change_fails(
    tmp_git_repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_git_repo / "tests" / "test_a.py").write_text("weakened\n", encoding="utf-8")
    (tmp_git_repo / "eval").mkdir()
    (tmp_git_repo / "eval" / "thresholds.yaml").write_text("new\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["guard"])
    assert result.exit_code == 1
    assert "tests/test_a.py" in caplog.text
    assert "eval/thresholds.yaml" in caplog.text


@pytest.mark.integration
def test_GRD_002_allowed_change_passes(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "artifacts" / "contract" / "S-1.1.json").write_text("new\n")
    (tmp_git_repo / "artifacts" / "contract" / "S-1.2.json").write_text("new\n")
    assert CliRunner().invoke(app, ["guard"]).exit_code == 0


@pytest.mark.integration
def test_GRD_003_not_an_extraction_task(
    tmp_git_repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    (tmp_git_repo / ".specproof_extraction_task").unlink()
    (tmp_git_repo / "tests" / "test_a.py").write_text("weakened\n", encoding="utf-8")
    assert CliRunner().invoke(app, ["guard"]).exit_code == 0
    assert "not an extraction task" in caplog.text


@pytest.mark.unit
def test_GRD_004_protected_patterns() -> None:
    paths = [
        "src/specproof/verify/engine.py",
        "src/specproof/loop/classify.py",
        "tests/unit/test_x.py",
        "eval/thresholds.yaml",
        "eval/audit/audit_sample.csv",
        "sources/sources.lock.yaml",
        "artifacts/contract/S-1.1.json",
    ]
    assert protected_paths(paths) == [
        "eval/thresholds.yaml",
        "sources/sources.lock.yaml",
        "src/specproof/verify/engine.py",
        "tests/unit/test_x.py",
    ]
