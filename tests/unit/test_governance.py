import ast
import json
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


def _tracked(repo_root: Path, prefix: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", prefix], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout
    return sorted(line for line in out.splitlines() if line)


def _quotes(node: object) -> list[str]:
    if isinstance(node, dict):
        found = [node["quote"]] if isinstance(node.get("quote"), str) else []
        return found + [q for value in node.values() for q in _quotes(value)]
    if isinstance(node, list):
        return [q for value in node for q in _quotes(value)]
    return []


@pytest.mark.unit
def test_GOV_002_committed_quotes_are_short(repo_root: Path) -> None:
    from specproof.util.text import norm

    too_long = []
    for rel in _tracked(repo_root, "artifacts/contract"):
        data = json.loads((repo_root / rel).read_text(encoding="utf-8"))
        too_long += [f"{rel}: {len(norm(q))}" for q in _quotes(data) if len(norm(q)) > 200]
    assert too_long == []


@pytest.mark.unit
def test_GOV_004_committed_artifacts_are_in_manifest(repo_root: Path) -> None:
    from specproof.util.hashing import sha256_file

    manifest_path = repo_root / "artifacts" / "manifest.json"
    records = {r["artifact"]: r["sha256"] for r in json.loads(manifest_path.read_text("utf-8"))}
    problems = []
    for rel in _tracked(repo_root, "artifacts"):
        if rel == "artifacts/manifest.json":
            continue
        if rel not in records:
            problems.append(f"{rel}: no manifest record")
        elif records[rel] != sha256_file(repo_root / rel):
            problems.append(f"{rel}: sha256 differs from manifest")
    assert problems == []


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
