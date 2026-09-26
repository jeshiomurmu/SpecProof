"""Reading artifacts/status.json for downstream stages."""

from pathlib import Path
from typing import Any

from specproof.util.io_json import load_json

TRUSTED = frozenset({"VERIFIED", "VERIFIED_WITH_SPEC_FINDINGS"})


def load_status(path: Path) -> dict[str, dict[str, Any]]:
    """Read status.json; a missing file means no classified sections."""
    if not path.exists():
        return {}
    data: dict[str, dict[str, Any]] = load_json(path)
    return data


def verified_section_ids(path: Path) -> list[str]:
    """Section ids that downstream stages may use: VERIFIED or VERIFIED_WITH_SPEC_FINDINGS."""
    return sorted(sid for sid, row in load_status(path).items() if row["status"] in TRUSTED)


def retryable(path: Path, max_attempts: int = 3) -> list[dict[str, Any]]:
    """NEEDS_RETRY sections below the attempt cap, sorted by section id."""
    return [
        {
            "section_id": sid,
            "attempt": row["attempt"],
            "extraction_errors": row["extraction_errors"],
        }
        for sid, row in sorted(load_status(path).items())
        if row["status"] == "NEEDS_RETRY" and row["attempt"] < max_attempts
    ]
