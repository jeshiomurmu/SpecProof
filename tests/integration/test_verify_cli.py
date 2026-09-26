import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fixtures.mutations import mutate
from typer.testing import CliRunner

from specproof.cli import app
from specproof.util.io_json import load_json

Good = Callable[[str], dict[str, Any]]
GOOD_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "contracts_good"


@pytest.mark.integration
def test_ENG_006_verify_cli_writes_results(workspace: Path) -> None:
    shutil.copytree(GOOD_DIR, workspace / "artifacts" / "contract")
    result = CliRunner().invoke(app, ["verify"])
    assert result.exit_code == 0, result.output
    out = workspace / "artifacts" / "verification"
    assert sorted(p.name for p in out.glob("*.json")) == sorted(
        [f"S-2.{n}.json" for n in range(1, 5)] + [f"S-2.{n}_attempt1.json" for n in range(1, 5)]
    )
    s22 = load_json(out / "S-2.2.json")
    assert [i["code"] for i in s22["issues"]] == ["V2_ROW_NOT_FOUND", "V3_ENUM_VIOLATION"]
    assert (out / "S-2.2.json").read_bytes() == (out / "S-2.2_attempt1.json").read_bytes()
    stages = {
        r["artifact"]: r["stage"] for r in load_json(workspace / "artifacts" / "manifest.json")
    }
    assert stages["artifacts/verification/S-2.2.json"] == "verify"


@pytest.mark.integration
def test_ENG_007_verify_exit_codes_and_selection(workspace: Path, good: Good) -> None:
    contracts = workspace / "artifacts" / "contract"
    contracts.mkdir(parents=True)
    runner = CliRunner()
    assert runner.invoke(app, ["verify", "--report-only"]).exit_code == 0
    (contracts / "S-2.2.json").write_text(
        json.dumps(mutate(good("S-2.2"), "wrong_path")), encoding="utf-8"
    )
    shutil.copyfile(GOOD_DIR / "S-2.3.json", contracts / "S-2.3.json")
    assert runner.invoke(app, ["verify"]).exit_code == 1
    assert runner.invoke(app, ["verify", "--report-only"]).exit_code == 0
    assert runner.invoke(app, ["verify", "--section", "S-2.3"]).exit_code == 0
    assert runner.invoke(app, ["verify", "--chapter", "2"]).exit_code == 1
