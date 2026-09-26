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

    @property
    def status(self) -> Path:
        return self.artifacts / "status.json"

    @property
    def feedback_dir(self) -> Path:
        return self.artifacts / "feedback"

    @property
    def spec_findings(self) -> Path:
        return self.artifacts / "findings" / "spec.json"

    @property
    def openapi_export(self) -> Path:
        return self.artifacts / "openapi.specproof.yaml"

    @property
    def community(self) -> Path:
        return self.work / "community_openapi.yaml"

    @property
    def community_findings(self) -> Path:
        return self.artifacts / "findings" / "community.json"

    @property
    def mapping(self) -> Path:
        return self.artifacts / "conformance" / "mapping.yaml"

    @property
    def replay_test(self) -> Path:
        return self.artifacts / "conformance" / "test_sample_replay.py"

    @property
    def conformance_findings(self) -> Path:
        return self.artifacts / "findings" / "conformance.json"

    @property
    def metrics(self) -> Path:
        return self.artifacts / "metrics.json"

    @property
    def findings_all(self) -> Path:
        return self.artifacts / "findings.json"

    @property
    def sarif(self) -> Path:
        return self.artifacts / "findings.sarif"

    @property
    def report_html(self) -> Path:
        return self.artifacts / "report" / "index.html"

    @property
    def eval_result(self) -> Path:
        return self.artifacts / "eval_result.json"

    @property
    def audit_dir(self) -> Path:
        return self.root / "eval" / "audit"

    @property
    def audit_sample(self) -> Path:
        return self.audit_dir / "audit_sample.csv"

    @property
    def audit_score(self) -> Path:
        return self.audit_dir / "audit_score.json"

    @property
    def findings_review(self) -> Path:
        return self.audit_dir / "findings_review.csv"

    @property
    def manual_baseline(self) -> Path:
        return self.audit_dir / "manual_baseline.csv"

    def rel(self, path: Path) -> str:
        """Return path relative to root, with forward slashes."""
        return path.relative_to(self.root).as_posix()
