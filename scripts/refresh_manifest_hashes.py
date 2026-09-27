"""Refresh manifest hashes for contracts edited after extraction (provenance relabel)."""

import hashlib
import json
from pathlib import Path

manifest = Path("artifacts/manifest.json")
records = json.loads(manifest.read_text(encoding="utf-8"))
changed = 0
for rec in records:
    path = Path(rec["artifact"])
    if rec["artifact"].startswith("artifacts/contract/") and path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if rec["sha256"] != digest:
            rec["sha256"] = digest
            changed += 1
            print(f"updated {rec['artifact']}")
text = json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
manifest.write_text(text, encoding="utf-8", newline="\n")
print(f"{changed} manifest record(s) updated")
