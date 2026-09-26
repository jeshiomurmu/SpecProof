from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_GOV_005_gitleaks_hook_present(repo_root: Path) -> None:
    config = yaml.safe_load((repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook_ids = [hook["id"] for repo in config["repos"] for hook in repo["hooks"]]
    assert "gitleaks" in hook_ids
