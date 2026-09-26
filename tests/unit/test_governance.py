import ast
import subprocess
from pathlib import Path

import pytest
import yaml

NETWORK_MODULES = {"requests", "httpx", "urllib.request", "aiohttp", "socket"}
FETCH_MODULE = Path("src/specproof/sources/fetch.py")


def _imported_modules(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


@pytest.mark.unit
def test_GOV_001_no_sources_tracked(repo_root: Path) -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    banned = [
        p
        for p in tracked
        if p.lower().endswith(".pdf")
        or p.endswith("pages.jsonl")
        or p.endswith("community_openapi.yaml")
    ]
    assert banned == []


@pytest.mark.unit
def test_GOV_003_network_imports_only_in_fetch(repo_root: Path) -> None:
    offenders = []
    for path in sorted((repo_root / "src").rglob("*.py")):
        rel = path.relative_to(repo_root)
        if rel == FETCH_MODULE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = _imported_modules(tree) & NETWORK_MODULES
        if hits:
            offenders.append(f"{rel.as_posix()}: {sorted(hits)}")
    assert offenders == []


@pytest.mark.unit
def test_GOV_005_gitleaks_hook_present(repo_root: Path) -> None:
    config = yaml.safe_load((repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook_ids = [hook["id"] for repo in config["repos"] for hook in repo["hooks"]]
    assert "gitleaks" in hook_ids
