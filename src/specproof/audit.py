"""Blind-audit sampling and scoring (EVALUATION_FRAMEWORK section 4). Pure."""

import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from specproof.models.contract import ContractSection

SHEET_COLUMNS = (
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
)


@dataclass(frozen=True)
class AuditItem:
    """One contract item as the auditor sees it; no verifier status."""

    item_id: str
    section_id: str
    chapter: int
    location: str
    page: int
    name: str
    required: str
    type_raw: str
    enum: str
    quote: str

    def row(self) -> dict[str, str]:
        """The CSV row, with empty verdict columns."""
        return {
            "item_id": self.item_id,
            "section_id": self.section_id,
            "page": str(self.page),
            "claimed_name": self.name,
            "claimed_required": self.required,
            "claimed_type": self.type_raw,
            "claimed_enum": self.enum,
            "quote": self.quote,
            "verdict": "",
            "reason": "",
            "missed_neighbor": "",
        }


def contract_items(contracts: Iterable[ContractSection]) -> list[AuditItem]:
    """Every field and definition of every contract, sorted by item id."""
    items = []
    for contract in contracts:
        chapter = int(contract.section_id[2:].split(".")[0])
        for spec in [*contract.fields, *contract.definitions]:
            required = "" if spec.required is None else ("T" if spec.required else "F")
            items.append(
                AuditItem(
                    item_id=f"{contract.section_id}/{spec.location}/{spec.name}",
                    section_id=contract.section_id,
                    chapter=chapter,
                    location=spec.location,
                    page=spec.citation.page,
                    name=spec.name,
                    required=required,
                    type_raw=spec.type_raw,
                    enum="|".join(spec.enum or []),
                    quote=spec.citation.quote,
                )
            )
    return sorted(items, key=lambda i: i.item_id)


def sample_items(items: list[AuditItem], n: int, seed: int) -> list[AuditItem]:
    """Stratified draw: round-robin over chapters, each cycling its locations; seeded."""
    rng = random.Random(seed)
    pools: dict[int, dict[str, list[AuditItem]]] = {}
    for item in items:
        pools.setdefault(item.chapter, {}).setdefault(item.location, []).append(item)
    for by_location in pools.values():
        for group in by_location.values():
            rng.shuffle(group)
    cursor = dict.fromkeys(pools, 0)
    picked: list[AuditItem] = []
    while len(picked) < n and any(any(g) for g in (list(p.values()) for p in pools.values())):
        for chapter in sorted(pools):
            locations = [loc for loc in sorted(pools[chapter]) if pools[chapter][loc]]
            if not locations or len(picked) >= n:
                continue
            location = locations[cursor[chapter] % len(locations)]
            cursor[chapter] += 1
            picked.append(pools[chapter][location].pop())
    return sorted(picked, key=lambda i: (i.chapter, i.item_id))


def score(rows: list[dict[str, str]], extraction_fields: dict[str, set[str]]) -> dict[str, Any]:
    """Audit counts; extraction_fields maps section id -> fields with extraction issues."""
    scored = [r for r in rows if r.get("verdict", "").strip().lower() in ("correct", "incorrect")]
    correct = sum(1 for r in scored if r["verdict"].strip().lower() == "correct")
    sections = {r["section_id"] for r in scored}
    missed = {r["section_id"] for r in scored if r.get("missed_neighbor", "").strip()}
    passed = [
        r
        for r in scored
        if r["section_id"] in extraction_fields
        and r["claimed_name"] not in extraction_fields[r["section_id"]]
    ]
    passed_incorrect = sum(1 for r in passed if r["verdict"].strip().lower() == "incorrect")
    return {
        "correct": correct,
        "n": len(scored),
        "sections": len(sections),
        "sections_with_miss": len(missed),
        "unscored": len(rows) - len(scored),
        "verifier_passed": len(passed),
        "verifier_passed_incorrect": passed_incorrect,
    }
