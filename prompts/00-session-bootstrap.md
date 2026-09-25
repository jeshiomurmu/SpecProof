# 00: Session bootstrap (first message in every new Bob task)

Mode: **Ask**. Replace `<<EDIT: T0X>>`.

```text
New task: <<EDIT: T0X>> for SpecProof.

Before anything else:
1. Read AGENTS.md in full, and the files in .bob/rules/.
2. Read the task card <<EDIT: T0X>> in docs/IMPLEMENTATION_PLAN.md and the prompt file
   prompts/<<EDIT: T0X-*.md>>.
3. Read docs/CHANGELOG.md to see what previous tasks completed.

Then reply with ONLY this block (no edits, no code):
- Task: <id + one-line goal>
- Previous tasks complete (from CHANGELOG): <list>
- Files I expect to create or modify: <list>
- Test IDs I will write first: <list>
- Protected paths I must not touch: <list from AGENTS.md section 8 that apply>
- Risks or ambiguities I see: <max 3; say "none" if none>

Do not start implementing. Wait for the next message.
```
