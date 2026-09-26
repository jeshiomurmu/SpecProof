import pytest
from typer.testing import CliRunner

from specproof.cli import app

COMMANDS = [
    "fetch",
    "ingest",
    "segment",
    "verify",
    "loop-status",
    "classify",
    "export-openapi",
    "compare",
    "conform",
    "report",
    "eval",
    "audit-sample",
    "audit-score",
    "guard",
]


@pytest.mark.unit
def test_CLI_001_help_lists_all_commands() -> None:
    result = CliRunner().invoke(app, ["--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    for name in COMMANDS:
        assert name in result.output, name
