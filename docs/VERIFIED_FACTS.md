# Facts verified before kickoff (2026-09-25)

Every claim in the pitch must trace to this file or to generated artifacts. Each fact below records **how** it was verified.

## Verified

| # | Fact | How verified |
|---|---|---|
| F1 | The UniFi Access API is officially documented only as a PDF; a community repo converted it to OpenAPI with MinerU + Claude and warns it "may contain omissions or errors". | Read the community repo README |
| F2 | The PDF has 194 pages (A4), an embedded text layer (CID TrueType fonts), and was created 2026-03-25. | `pdfinfo`, `pdffonts` |
| F3 | Marker counts in the text layer: "Request URL" 108, "Request Sample" 106, "Response Sample" 99, "Request Body" 122, "Permission Key" 107, "Required" 393. | `pdftotext -layout` + `grep -c` |
| F4 | A regex over the PDF finds 107 (method, path) pairs; the community OpenAPI has 107 operations. The endpoint sets match after path normalization, so **endpoint-level coverage of the community spec is good**. Findings must come from field or sample level. | Python probe |
| F5 | Section layout is regular: title, `Request URL:`, `Permission Key:`, `Method:`, header table, body table (Parameter / Required T-F / Type / Description / Example), `Response Sample` JSON, `Request Sample` curl with `--data-raw '{...}'`. | Read §3.2 User Registration text |
| F6 | `pdftotext -layout` preserves table rows on single lines, e.g. `first_name  T  String`. The User Registration `first_name` row is on **PDF page 14**. | Per-page extraction |
| F7 | **Spec self-inconsistency:** §4.1 Schemas (page 52) defines `visit_reason` as `enum reason {Interview,Business,Cooperation,Others}`, while the request samples in §4.2 Create Visitor (page 56) and §4.5 Update Visitor (page 63) send `"visit_reason": "Interviemw"`. | Text search + page mapping |
| F8 | A crude probe validating 18 PDF request samples against the community schemas found 1 enum violation (F7) and 1 sample that did not parse as JSON. **This probe was incomplete; do not cite its numbers.** | jsonschema probe |
| F9 | Chapters contain "Schemas" sections (e.g. 3.1, 4.1) that define shared objects and enums referenced by endpoint sections. | Table of contents + text |
| F10 | `py-unifi-access` (MIT, commit 6466978) is an async client with Pydantic models (`models/door.py`, `device_settings.py`, `user.py`, `websocket.py`). It references 11 `/api/v1/developer/...` paths and has its own test suite. | Cloned and grepped |
| F11 | Pinned hashes: PDF `d204c8b9…a534`, community OpenAPI `629c809c…3e24` (commit `426e948b`). | `sha256sum` via commit-pinned URLs |
| F12 | IBM Bob project config locations: root `AGENTS.md`, `.bob/rules/*.md`, `.bob/custom_modes.yaml`, `.bob/commands/*.md`, `.bob/skills/<name>/SKILL.md`, `.bob/mcp.json`, `.bobignore`. Custom mode fields: slug, name, description, scope, role definition, when to use, custom instructions, tool permissions. | bob.ibm.com docs + community adapters |
| F13 | Claude Code's native installer is `curl -fsSL https://claude.ai/install.sh \| bash` (macOS/Linux) or `irm https://claude.ai/install.ps1 \| iex` (Windows). npm install is deprecated. CLAUDE.md supports `@path` imports. | Setup guide, April 2026 |
| F14 | Hackathon: judged on Application of Technology (clear application of Bob 2.0), Presentation, Business Value (high-priority issue), and Originality (incl. approach in applying Bob 2.0). Submission must include files where Bob assisted and screenshots of Bob task session summaries. Deadline: Sun 27 Sep, 21:00 BST. | lablab event page screenshot |

## NOT yet verified (check at kickoff; update this file)

| # | Assumption | How to check |
|---|---|---|
| U1 | Bobcoin allowance (May event: 40 per person) | Kickoff guide at 21:35 BST / Discord |
| U2 | Exact YAML keys Bob accepts in `custom_modes.yaml` (`groups`, `fileRegex`) | Reload Bob; if the mode doesn't appear, create it via the UI (START_HERE Step 2.4) |
| U3 | Slash-command frontmatter keys (`description`, `argument-hint`) | Type `/` in Bob chat and check that `sp-extract` appears |
| U4 | Bob reads a 194-page PDF from the workspace with page-accurate references | Pilot extraction on §3.2 (task T07) |
| U5 | Policy on pre-event planning docs and on using Claude Code alongside Bob. Human's own reading (2026-09-25): other AI tools may build code; not confirmed by an organizer or written rule. Pre-event product code policy also unconfirmed | Ask in the kickoff Discord Q&A (22:00 BST) |
| U6 | Whether an older UniFi Access PDF version exists (needed for the version-diff stretch goal) | Search the vendor site / Wayback Machine; stretch only |
