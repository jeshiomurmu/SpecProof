"""Download pinned sources and verify them. The only module allowed to touch the network."""

import logging
import re
import shutil
import subprocess
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

import yaml

from specproof.util.hashing import sha256_file

log = logging.getLogger(__name__)

Opener = Callable[[str], Any]
_HEX = re.compile(r"[0-9a-f]+")


class FetchError(Exception):
    """A source could not be fetched or failed verification."""


@dataclass(frozen=True)
class Source:
    """One pinned entry of sources.lock.yaml."""

    id: str
    kind: str
    url: str
    dest: str
    sha256: str | None = None
    commit: str | None = None


def _pin(entry: dict[str, Any], key: str, length: int) -> str | None:
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not _HEX.fullmatch(value) or len(value) != length:
        raise FetchError(f"{entry.get('id')}: {key} must be a quoted {length}-char hex string")
    return value


def load_lock(path: Path) -> list[Source]:
    """Parse a lock file into sources sorted by id; pins must be hex strings of full length."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = [
        Source(
            id=str(entry["id"]),
            kind=str(entry["kind"]),
            url=str(entry["url"]),
            dest=str(entry["dest"]),
            sha256=_pin(entry, "sha256", 64),
            commit=_pin(entry, "commit", 40),
        )
        for entry in data["sources"]
    ]
    return sorted(sources, key=lambda s: s.id)


def _default_opener(url: str) -> IO[bytes]:
    return urllib.request.urlopen(url, timeout=120)  # type: ignore[no-any-return]


def fetch_file(source: Source, root: Path, opener: Opener = _default_opener) -> bool:
    """Ensure dest holds bytes with the pinned sha256; return True if a download happened."""
    if not source.sha256:
        raise FetchError(f"{source.id}: file source needs a sha256 pin")
    dest = root / source.dest
    if dest.exists() and sha256_file(dest) == source.sha256:
        log.info("%s: cached, sha256 ok", source.id)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with opener(source.url) as response, part.open("wb") as out:
        shutil.copyfileobj(response, out)
    actual = sha256_file(part)
    if actual != source.sha256:
        part.unlink()
        raise FetchError(f"{source.id}: sha256 mismatch (expected {source.sha256}, got {actual})")
    part.replace(dest)
    log.info("%s: downloaded, sha256 ok", source.id)
    return True


def _git(*args: str) -> str:
    cmd = ["git", "-c", "advice.detachedHead=false", *args]
    done = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def fetch_git(source: Source, root: Path) -> bool:
    """Ensure dest is a clone checked out at the pinned commit; return True if it cloned."""
    if not source.commit:
        raise FetchError(f"{source.id}: git source needs a commit pin")
    dest = root / source.dest
    if dest.exists():
        head = _git("-C", str(dest), "rev-parse", "HEAD")
        if head != source.commit:
            raise FetchError(f"{source.id}: {dest} is at {head}, not {source.commit}; delete it")
        log.info("%s: cached at pinned commit", source.id)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", "--quiet", source.url, str(dest))
    _git("-C", str(dest), "checkout", "--quiet", source.commit)
    log.info("%s: cloned at %s", source.id, source.commit)
    return True


def fetch_all(lock: Path, root: Path, opener: Opener = _default_opener) -> None:
    """Fetch and verify every source in the lock file."""
    for source in load_lock(lock):
        if source.kind == "file":
            fetch_file(source, root, opener)
        elif source.kind == "git":
            fetch_git(source, root)
        else:
            raise FetchError(f"{source.id}: unknown kind {source.kind!r}")
