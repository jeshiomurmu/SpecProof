"""Regenerate the README results table from artifacts/metrics.json (`make readme`)."""

import json
from pathlib import Path

from specproof.report.readme import update_readme

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    metrics = json.loads((ROOT / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    updated = update_readme(text, metrics)
    if updated != text:
        readme.write_bytes(updated.encode("utf-8"))
        print("README.md results table updated")
    else:
        print("README.md results table already up to date")


if __name__ == "__main__":
    main()
