import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fixtures.mutations import mutate
from typer.testing import CliRunner

from specproof.cli import app
from specproof.loop.classify import classify
from specproof.loop.feedback import render_feedback
from specproof.loop.status import verified_section_ids
from specproof.models.contract import ContractSection
from specproof.models.findings import Finding
from specproof.models.verification import SectionStatus, VerificationResult
from specproof.util.io_json import load_json

Good = Callable[[str], dict[str, Any]]
Run = Callable[[dict[str, Any] | str, str], VerificationResult]
GOOD_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "contracts_good"


def _with_attempt(contract: dict[str, Any], attempt: int) -> dict[str, Any]:
    contract["extraction"]["attempt"] = attempt
    return contract


def _classify(
    run: Run,
    contract: dict[str, Any],
    section_id: str,
    previous: VerificationResult | None = None,
) -> tuple[SectionStatus, list[Finding], VerificationResult]:
    result = run(contract, section_id)
    status, findings = classify(result, ContractSection.model_validate(contract), previous)
    return status, findings, result


@pytest.mark.integration
def test_LOOP_001_clean_section_verified(run_verify: Run, good: Good) -> None:
    status, findings, _ = _classify(run_verify, good("S-2.3"), "S-2.3")
    assert (status, findings) == ("VERIFIED", [])


@pytest.mark.integration
def test_LOOP_002_grounded_conflict_is_spec_finding(run_verify: Run, good: Good) -> None:
    status, findings, _ = _classify(run_verify, good("S-2.2"), "S-2.2")
    assert status == "VERIFIED_WITH_SPEC_FINDINGS"
    assert [(f.type, f.severity, f.section_id) for f in findings] == [
        ("SPEC_SELF_INCONSISTENCY", "high", "S-2.2")
    ]
    finding = findings[0]
    assert sorted(e.page for e in finding.evidence if e.page is not None) == [3, 5]
    assert all(e.kind == "doc" for e in finding.evidence)
    assert finding.review.status == "CANDIDATE"
    assert finding.id == Finding.make_id(finding.type, "S-2.2", "color", finding.evidence)


@pytest.mark.integration
def test_LOOP_003_retry_writes_feedback(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    contracts.mkdir(parents=True)
    bad = mutate(good("S-2.2"), "fabricate_quote")
    (contracts / "S-2.2.json").write_text(json.dumps(bad), encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["verify", "--report-only"]).exit_code == 0
    assert runner.invoke(app, ["classify"]).exit_code == 0
    status = load_json(workspace / "artifacts" / "status.json")
    assert status == {"S-2.2": {"attempt": 1, "extraction_errors": 1, "status": "NEEDS_RETRY"}}
    feedback = (workspace / "artifacts" / "feedback" / "S-2.2.md").read_text(encoding="utf-8")
    assert feedback.startswith("# Feedback: S-2.2 (attempt 1 → 2)\n")


@pytest.mark.integration
def test_LOOP_004_quarantine_at_attempt_3(run_verify: Run, good: Good) -> None:
    contract = _with_attempt(mutate(good("S-2.2"), "fabricate_quote"), 3)
    status, findings, _ = _classify(run_verify, contract, "S-2.2")
    assert (status, findings) == ("QUARANTINED", [])


@pytest.mark.integration
def test_LOOP_005_ungrounded_conflict_is_not_a_finding(run_verify: Run, good: Good) -> None:
    contract = good("S-2.2")
    color = next(f for f in contract["fields"] if f["name"] == "color")
    color["citation"]["quote"] = "color   T   String   A made-up description."
    status, findings, result = _classify(run_verify, contract, "S-2.2")
    assert "V3_ENUM_VIOLATION" in [i.code for i in result.issues]
    assert (status, findings) == ("NEEDS_RETRY", [])


@pytest.mark.integration
def test_LOOP_006_feedback_lists_only_failures(run_verify: Run, good: Good) -> None:
    contract = mutate(mutate(good("S-2.2"), "fabricate_quote"), "flip_required")
    result = run_verify(contract, "S-2.2")
    text = render_feedback(result, ContractSection.model_validate(contract), (4, 5))
    assert text == (
        "# Feedback: S-2.2 (attempt 1 → 2)\n"
        "Fix ONLY the items below. Do not change items that passed.\n"
        "\n"
        "## name (location: body)\n"
        "- V2_ROW_MISMATCH: row says required=T type=String; contract says required=False "
        "type_raw=String\n"
        '  Evidence: page 4, "name T String Name of the widget. Bolt"\n'
        "\n"
        "## size (location: body)\n"
        "- V2_CITATION_NOT_FOUND: quote not found on page 4 or elsewhere in the section\n"
        '  Closest text on pages 4-5 (page 4): "size F Integer Size in millimetres. 3"\n'
    )
    for passing in ("## color", "## notes", "## Authorization", "V3_ENUM_VIOLATION"):
        assert passing not in text


@pytest.mark.integration
def test_LOOP_007_feedback_deterministic(run_verify: Run, good: Good) -> None:
    contract = mutate(good("S-2.2"), "drop_field")
    model = ContractSection.model_validate(contract)
    first = render_feedback(run_verify(contract, "S-2.2"), model, (4, 5))
    second = render_feedback(run_verify(contract, "S-2.2"), model, (4, 5))
    assert first == second
    assert "## size (location: not in contract)" in first


@pytest.mark.integration
def test_LOOP_008_malformed_sample_finding(run_verify: Run, good: Good) -> None:
    status, findings, _ = _classify(run_verify, good("S-2.4"), "S-2.4")
    assert status == "VERIFIED_WITH_SPEC_FINDINGS"
    assert [(f.type, f.severity) for f in findings] == [("SPEC_MALFORMED_SAMPLE", "medium")]
    assert [e.page for e in findings[0].evidence] == [7]


@pytest.mark.integration
def test_LOOP_009_loop_status_lists_retryable(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    contracts.mkdir(parents=True)
    (contracts / "S-2.2.json").write_text(
        json.dumps(mutate(good("S-2.2"), "wrong_path")), encoding="utf-8"
    )
    (contracts / "S-2.4.json").write_text(
        json.dumps(_with_attempt(mutate(good("S-2.4"), "wrong_method"), 3)), encoding="utf-8"
    )
    shutil.copyfile(GOOD_DIR / "S-2.3.json", contracts / "S-2.3.json")
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    assert runner.invoke(app, ["classify"]).exit_code == 0
    result = runner.invoke(app, ["loop-status", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == [
        {"attempt": 1, "extraction_errors": 1, "section_id": "S-2.2"}
    ]


@pytest.mark.integration
def test_LOOP_010_downstream_excludes_unverified(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    shutil.copytree(GOOD_DIR, contracts)
    (contracts / "S-2.3.json").write_text(
        json.dumps(_with_attempt(mutate(good("S-2.3"), "wrong_method"), 3)), encoding="utf-8"
    )
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    status_path = workspace / "artifacts" / "status.json"
    assert load_json(status_path)["S-2.3"]["status"] == "QUARANTINED"
    assert verified_section_ids(status_path) == ["S-2.1", "S-2.2", "S-2.4"]
    spec = load_json(workspace / "artifacts" / "findings" / "spec.json")
    assert sorted(f["type"] for f in spec) == ["SPEC_MALFORMED_SAMPLE", "SPEC_SELF_INCONSISTENCY"]


@pytest.mark.integration
def test_LOOP_011_early_stop_when_errors_do_not_decrease(run_verify: Run, good: Good) -> None:
    first = run_verify(mutate(good("S-2.2"), "wrong_path"), "S-2.2")
    retry = _with_attempt(mutate(good("S-2.2"), "wrong_method"), 2)
    status, _, _ = _classify(run_verify, retry, "S-2.2", previous=first)
    assert status == "QUARANTINED"
    fixed = _with_attempt(good("S-2.2"), 2)
    status, _, _ = _classify(run_verify, fixed, "S-2.2", previous=first)
    assert status == "VERIFIED_WITH_SPEC_FINDINGS"


@pytest.mark.integration
def test_LOOP_012_feedback_removed_once_terminal(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    contracts.mkdir(parents=True)
    target = contracts / "S-2.2.json"
    target.write_text(json.dumps(mutate(good("S-2.2"), "wrong_path")), encoding="utf-8")
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    feedback = workspace / "artifacts" / "feedback" / "S-2.2.md"
    assert feedback.exists()
    target.write_text(json.dumps(_with_attempt(good("S-2.2"), 2)), encoding="utf-8")
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    assert not feedback.exists()
    status = load_json(workspace / "artifacts" / "status.json")["S-2.2"]
    assert status == {"attempt": 2, "extraction_errors": 0, "status": "VERIFIED_WITH_SPEC_FINDINGS"}


@pytest.mark.integration
def test_CLI_003_verify_exits_1_when_retry_needed(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    contracts.mkdir(parents=True)
    (contracts / "S-2.2.json").write_text(
        json.dumps(mutate(good("S-2.2"), "flip_type")), encoding="utf-8"
    )
    runner = CliRunner()
    assert runner.invoke(app, ["verify"]).exit_code == 1
    runner.invoke(app, ["classify"])
    status = load_json(workspace / "artifacts" / "status.json")
    assert status["S-2.2"]["status"] == "NEEDS_RETRY"
