"""Repository paths and version constants."""

from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1
RULES_VERSION = "v1"


@dataclass(frozen=True)
class Paths:
    """Well-known artifact locations under a repository root."""

    root: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        """Build paths relative to root."""
        return cls(root=root)

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def work(self) -> Path:
        return self.artifacts / "work"

    @property
    def spec_pdf(self) -> Path:
        return self.work / "spec.pdf"

    @property
    def pages(self) -> Path:
        return self.work / "pages.jsonl"

    @property
    def manifest(self) -> Path:
        return self.artifacts / "manifest.json"

    @property
    def sections_index(self) -> Path:
        return self.artifacts / "sections_index.json"

    @property
    def sections_text(self) -> Path:
        return self.work / "sections.jsonl"

    @property
    def contract_dir(self) -> Path:
        return self.artifacts / "contract"

    @property
    def verification_dir(self) -> Path:
        return self.artifacts / "verification"

    def rel(self, path: Path) -> str:
        """Return path relative to root, with forward slashes."""
        return path.relative_to(self.root).as_posix()
