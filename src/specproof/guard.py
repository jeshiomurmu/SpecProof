"""Reward-hacking guard (AGENTS.md section 8): extraction tasks must not touch the oracle."""

import subprocess
from pathlib import Path

PROTECTED_PREFIXES = ("src/specproof/verify/", "tests/")
PROTECTED_FILES = frozenset({"eval/thresholds.yaml", "sources/sources.lock.yaml"})
MARKER = ".specproof_extraction_task"
BASE_FILE = ".specproof_task_base"


def protected_paths(paths: list[str]) -> list[str]:
    """The given repo-relative paths that are protected, sorted."""
    return sorted(p for p in paths if p in PROTECTED_FILES or p.startswith(PROTECTED_PREFIXES))


def _git(root: Path, *args: str) -> list[str]:
    done = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return [line for line in done.stdout.splitlines() if line]


def changed_paths(root: Path, base: str) -> list[str]:
    """Tracked files changed since base (working tree) plus untracked files, sorted."""
    changed = _git(root, "diff", "--name-only", base)
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    return sorted(set(changed) | set(untracked))
