import hashlib
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specproof.cli import app
from specproof.sources.fetch import FetchError, Source, fetch_file, fetch_git, load_lock


def _git(*args: str, cwd: Path) -> str:
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.mark.unit
def test_FET_001_hash_mismatch_exits_1_and_keeps_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"real bytes")
    lock = tmp_path / "lock.yaml"
    lock.write_text(
        "version: 1\nsources:\n"
        "  - id: x\n    kind: file\n"
        f"    url: {payload.as_uri()}\n"
        f"    sha256: '{'0' * 64}'\n"
        "    dest: out/x.bin\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["fetch", "--lock", str(lock)])
    assert result.exit_code == 1
    assert "sha256 mismatch" in caplog.text
    assert list((tmp_path / "out").glob("*")) == []


@pytest.mark.unit
def test_FET_004_unquoted_or_short_pin_rejected(tmp_path: Path) -> None:
    lock = tmp_path / "lock.yaml"
    lock.write_text(
        "version: 1\nsources:\n  - id: x\n    kind: file\n    url: u\n    sha256: 0\n    dest: d\n",
        encoding="utf-8",
    )
    with pytest.raises(FetchError, match="64-char hex"):
        load_lock(lock)


@pytest.mark.unit
def test_FET_005_real_lock_file_parses(repo_root: Path) -> None:
    sources = load_lock(repo_root / "sources" / "sources.lock.yaml")
    assert [s.id for s in sources] == ["community_openapi", "py_unifi_access", "unifi_spec_pdf"]


@pytest.mark.unit
def test_FET_002_cache_hit_does_not_download(tmp_path: Path) -> None:
    dest = tmp_path / "x.bin"
    dest.write_bytes(b"cached")
    source = Source(
        id="x",
        kind="file",
        url="https://example.invalid/x.bin",
        dest="x.bin",
        sha256=hashlib.sha256(b"cached").hexdigest(),
    )
    calls: list[str] = []

    def opener(url: str) -> object:
        calls.append(url)
        raise AssertionError("must not download")

    assert fetch_file(source, tmp_path, opener=opener) is False
    assert calls == []


@pytest.mark.unit
def test_FET_003_git_checkout_at_pinned_commit(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "a.txt").write_text("one", encoding="utf-8")
    _git("add", "a.txt", cwd=origin)
    _git("commit", "-q", "-m", "one", cwd=origin)
    pin = _git("rev-parse", "HEAD", cwd=origin)
    (origin / "a.txt").write_text("two", encoding="utf-8")
    _git("commit", "-q", "-am", "two", cwd=origin)
    bare = tmp_path / "bare.git"
    _git("clone", "-q", "--bare", str(origin), str(bare), cwd=tmp_path)

    root = tmp_path / "root"
    root.mkdir()
    source = Source(id="c", kind="git", url=str(bare), dest="work/client", commit=pin)
    fetch_git(source, root)
    assert _git("rev-parse", "HEAD", cwd=root / "work" / "client") == pin
