"""The Bob-written model-to-section mapping, validated deterministically before use."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

JSON_PATH = re.compile(r"^data(\[\*\])*$")


class MappingError(ValueError):
    """A mapping entry that cannot be trusted."""


@dataclass(frozen=True)
class Mapping:
    """One client model that parses the response of one contract section."""

    section_id: str
    model: str
    json_path: str
    file: str
    line: int

    @property
    def class_name(self) -> str:
        """The model's class name (last dotted component)."""
        return self.model.rsplit(".", 1)[-1]


def validate_mapping(entry: Mapping, client_root: Path, verified_ids: set[str]) -> Mapping:
    """Return the entry if it is trustworthy, else raise MappingError with the reason."""
    where = f"{entry.section_id} -> {entry.model}"
    if entry.section_id not in verified_ids:
        raise MappingError(f"{where}: section is not VERIFIED or VERIFIED_WITH_SPEC_FINDINGS")
    if not JSON_PATH.match(entry.json_path):
        raise MappingError(f"{where}: json_path {entry.json_path!r} must be data, data[*], ...")
    source = client_root / entry.file
    if not source.is_file():
        raise MappingError(f"{where}: code file {entry.file} does not exist")
    lines = source.read_text(encoding="utf-8").splitlines()
    text = lines[entry.line - 1] if 0 < entry.line <= len(lines) else ""
    if not re.search(rf"\bclass {re.escape(entry.class_name)}\b", text):
        raise MappingError(
            f"{where}: line {entry.line} of {entry.file} does not contain "
            f"'class {entry.class_name}'"
        )
    return entry


def parse_mapping(data: Any) -> list[Mapping]:
    """Turn the YAML list into Mapping entries, sorted by (section, model)."""
    entries = []
    for row in data or []:
        code = row.get("code") or {}
        entries.append(
            Mapping(
                section_id=str(row["section_id"]),
                model=str(row["model"]),
                json_path=str(row.get("json_path", "data")),
                file=str(code.get("file", "")),
                line=int(code.get("line", 0)),
            )
        )
    return sorted(entries, key=lambda m: (m.section_id, m.model, m.line))


def load_mappings(
    path: Path, client_root: Path, verified_ids: set[str]
) -> tuple[list[Mapping], list[str]]:
    """Valid entries plus one error message per rejected entry."""
    if not path.exists():
        return [], []
    valid: list[Mapping] = []
    errors: list[str] = []
    for entry in parse_mapping(yaml.safe_load(path.read_text(encoding="utf-8"))):
        try:
            valid.append(validate_mapping(entry, client_root, verified_ids))
        except MappingError as exc:
            errors.append(str(exc))
    return valid, errors
