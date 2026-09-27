import csv
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specproof.audit import AuditItem, sample_items
from specproof.cli import app
from specproof.util.io_json import load_json

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


def _items() -> list[AuditItem]:
    items = []
    for chapter in (1, 2, 3):
        for loc in ("body", "header", "response"):
            for i in range(6 if chapter != 3 else 1):
                items.append(
                    AuditItem(
                        f"S-{chapter}.1/{loc}/f{i}",
                        f"S-{chapter}.1",
                        chapter,
                        loc,
                        1,
                        f"f{i}",
                        "T",
                        "String",
                        "",
                        "q" * 12,
                    )
                )
    return items


@pytest.mark.unit
def test_AUD_001_stratified_and_seeded() -> None:
    first = sample_items(_items(), 10, 20260926)
    assert first == sample_items(_items(), 10, 20260926)
    assert first != sample_items(_items(), 10, 1)
    per_chapter = {c: sum(1 for i in first if i.chapter == c) for c in (1, 2, 3)}
    assert per_chapter == {1: 4, 2: 3, 3: 3}
    assert {i.location for i in first if i.chapter == 1} == {"body", "header", "response"}


@pytest.mark.unit
def test_AUD_002_small_chapter_topped_up() -> None:
    picked = sample_items(_items(), 20, 7)
    assert sum(1 for i in picked if i.chapter == 3) == 3
    assert len(picked) == 20


@pytest.fixture
def classified(workspace: Path) -> Path:
    shutil.copytree(FIXTURES / "contracts_good", workspace / "artifacts" / "contract")
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    return workspace


@pytest.mark.integration
def test_AUD_003_sheet_is_blind_and_never_redrawn(classified: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["audit-sample", "--n", "8"]).exit_code == 0
    sheet = classified / "eval" / "audit" / "audit_sample.csv"
    text = sheet.read_text(encoding="utf-8")
    header = text.splitlines()[0].split(",")
    assert header == [
        "item_id",
        "section_id",
        "page",
        "claimed_name",
        "claimed_required",
        "claimed_type",
        "claimed_enum",
        "quote",
        "verdict",
        "reason",
        "missed_neighbor",
    ]
    assert "VERIFIED" not in text and "status" not in header
    assert runner.invoke(app, ["audit-sample", "--n", "8"]).exit_code == 1
    assert sheet.read_text(encoding="utf-8") == text


@pytest.mark.integration
def test_AUD_004_score_and_metrics(classified: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["audit-sample", "--n", "6"])
    sheet = classified / "eval" / "audit" / "audit_sample.csv"
    with sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for i, row in enumerate(rows):
        row["verdict"] = "incorrect" if i == 0 else "correct"
    rows[1]["missed_neighbor"] = "x"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    assert runner.invoke(app, ["audit-score"]).exit_code == 0
    score = load_json(classified / "eval" / "audit" / "audit_score.json")
    assert (score["n"], score["correct"]) == (6, 5)
    metrics = load_json(classified / "artifacts" / "metrics.json")
    assert (
        metrics["audited_precision"]["numerator"],
        metrics["audited_precision"]["denominator"],
    ) == (5, 6)
    assert len(metrics["audited_precision"]["ci95"]) == 2


@pytest.mark.integration
def test_EVL_006_eval_cli(classified: Path) -> None:
    (classified / "eval").mkdir(exist_ok=True)
    shutil.copy(REPO / "eval" / "thresholds.yaml", classified / "eval" / "thresholds.yaml")
    result = CliRunner().invoke(app, ["eval"])
    assert result.exit_code == 1
    assert "audited_precision" in result.stdout and "FAIL" in result.stdout
    out = load_json(classified / "artifacts" / "eval_result.json")
    rows = {r["metric"]: r for r in out["results"]}
    assert rows["citation_grounding_rate"]["verdict"] == "PASS"
    assert rows["audited_precision"]["reason"].startswith("missing:")
    metrics = json.loads((classified / "artifacts" / "metrics.json").read_text("utf-8"))
    assert metrics["final_verified_rate"] == {"denominator": 4, "numerator": 4, "value": 1.0}
