"""Deterministic JSON reading and writing."""

import json
import os
from pathlib import Path
from typing import Any


def dumps_json(obj: Any) -> str:
    """Serialize with sorted keys, 2-space indent, raw UTF-8 and a trailing newline."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write bytes via a temp file and os.replace, so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def dump_json(path: Path, obj: Any) -> None:
    """Atomically write obj as deterministic JSON with LF line endings."""
    write_bytes_atomic(path, dumps_json(obj).encode("utf-8"))


def load_json(path: Path) -> Any:
    """Read a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))
