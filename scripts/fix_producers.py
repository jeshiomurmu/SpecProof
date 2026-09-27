import glob
import json
import sys

BOB = {"S-3.2", "S-4.1", "S-4.2"} | {f"S-4.{i}" for i in range(3, 15)}
apply = "--apply" in sys.argv
for path in sorted(glob.glob("artifacts/contract/*.json")):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    e = d["extraction"]
    sid = d["section_id"]
    if sid in BOB:
        who = "ibm-bob" if e.get("attempt", 1) == 1 else "ibm-bob+claude-code"
    else:
        who = "claude-code"
    print(f"{sid:8} now={e.get('producer'):20} attempt={e.get('attempt')} -> {who}")
    if apply and e.get("producer") != who:
        e["producer"] = who
        if who == "claude-code":
            e["mode"] = "claude-code"
            e["bob_task_ref"] = None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
