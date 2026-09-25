# Demo, Video, Slides and Submission: SpecProof

**Golden rule:** every number shown on screen comes from `artifacts/metrics.json`. Any number shown is labeled as either machine-verified or human-confirmed.

## 1. Video (≤ 5:00, MP4, 1080p)
Record the screen at 1080p. Use a clean browser profile, a large editor font (≥ 16 px), and turn notifications off. Record in segments, then cut them together.

| Time | Scene | On screen | Voice-over (adapt; keep it honest) |
|---|---|---|---|
| 0:00–0:20 | **Hook** | PDF page 52 (the enum), then page 56 (the sample) | "This 194-page PDF is the only official spec for the UniFi Access API. On page 52 it says `visit_reason` must be Interview, Business, Cooperation, or Others. On page 56, its own example sends 'Interviemw'. Copy the example, and you ship a bug. No tool catches this, because there's no machine-readable spec." |
| 0:20–0:45 | **Problem** | README problem section | "Payment networks, tax authorities, hardware vendors: many integrations are specified only in documents. Developers transcribe them by hand. Hand conversions come with disclaimers, not guarantees." |
| 0:45–1:45 | **Bob does the reading** | Bob: Spec Auditor mode → `/sp-extract 4` → subagents fanning out → a contract JSON with citations | "SpecProof runs inside IBM Bob 2.0. A custom Spec Auditor mode and skill have Bob read the PDF directly, with one subagent per chapter running in parallel. Every field it records carries a page number and a verbatim quote." |
| 1:45–2:30 | **Machine checks, not trust** | `specproof verify` output → a feedback file → `/sp-loop` → the status flips to VERIFIED; the loop funnel in the report | "Bob never grades itself. Deterministic code checks every quote against the page, every table row against its required flag and type, and the document's own samples against the contract. Failures loop back with precise feedback, with at most two retries. What still fails is quarantined, not hidden." |
| 2:30–3:15 | **Findings** | Report → finding card with both page citations → community diff → the client replay test failing or passing in the terminal | "When two grounded parts of the document disagree, that's a defect in the spec itself, reported with both citations. Then we test real code: the document's own response samples are replayed through the py-unifi-access models." (State only what `findings_review.csv` confirmed.) |
| 3:15–4:00 | **Impact** | Report hero metrics with denominators | Use the templates in EVALUATION §7 verbatim: coverage, grounding, loop lift, audited precision with CI, and minutes per endpoint vs the manual baseline (with its caveat). |
| 4:00–4:40 | **Built with Bob 2.0** | `bob_sessions/INDEX.md`, `.bob/` folder, a session screenshot | "Every engine component was built test-first in Bob's Agent mode, scoped in Plan mode. Extraction uses Bob's document understanding, subagents and parallel tasks. All sessions are in the repo." |
| 4:40–5:00 | **Close** | Prior-art slide → live URL | "Other tools extract specs with AI. SpecProof is the one that doesn't take the AI's word for it. The report and repo are linked below." |

**Recording tips:**
- Pre-run everything. Show the committed artifacts rather than waiting on live extraction.
- Label pre-recorded Bob segments truthfully ("recorded during the build on Saturday").
- Do a final check of every number against `metrics.json` before exporting.

## 2. Slides (PDF, 10 slides)
1. **Title.** "SpecProof: verified contracts from document-only API specs." Name, event, live URL.
2. **The problem.** Document-only specs; manual transcription; defects propagate. Include the one-line F1 evidence.
3. **Proof it's real.** Screenshot: page 52 enum vs page 56 sample (F7).
4. **How it works.** The pipeline diagram (architecture §2).
5. **IBM Bob 2.0 at the core.** The feature map table (architecture §18) plus a session screenshot.
6. **AI proposes, code decides.** The V1–V5 rules and the loop state machine.
7. **Results.** Hero metrics with denominators; the loop funnel.
8. **Findings.** Confirmed spec defects, community discrepancies and client issues, with citations.
9. **Prior art and our delta** (`PRIOR_ART.md` table, condensed).
10. **Impact and next steps.** Time saved per endpoint; generalizing to XLSX/DOCX specs; version-diff mode; upstream PRs.

## 3. Cover image
16:9, dark background. Left: a PDF page fragment with a highlighted row. Right: a green "VERIFIED · p.14" badge and a red "SPEC DEFECT · p.52 ↔ p.56" badge. Title text "SpecProof". No logos you don't own.

## 4. Submission fields (lablab.ai)

| Field | Draft |
|---|---|
| Project title | SpecProof: verified contracts from document-only API specs |
| Short description | IBM Bob 2.0 reads PDF API specs into cited contracts; deterministic checks verify every claim, find spec defects, and test real client code. |
| Long description | Use the template below; fill it only from `metrics.json` and `findings_review.csv` |
| Technology tags | IBM Bob 2.0, Document understanding, Subagents, Python, Pydantic, OpenAPI, Testing |
| Category tags | Developer tools, Application maintenance, Testing, API integration |
| Cover image | §3 |
| Video | ≤ 5 min MP4 (§1) |
| Slides | PDF (§2) |
| Demo application platform | Static web (Vercel or GitHub Pages) |
| Application URL | Deployed report URL |
| Code repository | Public GitHub URL (MIT) |

**Long description template:**
> **Problem.** Many integrations are specified only as documents. Developers transcribe hundreds of pages by hand, and document defects propagate into code. Example: the official UniFi Access API PDF defines `visit_reason` as an enum on page 52, while its own samples on pages 56 and 63 use "Interviemw".
>
> **Solution.** SpecProof runs inside IBM Bob 2.0. A custom Spec Auditor mode and skill have Bob read the PDF with document understanding, with one subagent per chapter in parallel, producing a contract where every field cites a page and a verbatim quote. Deterministic code, never the model, verifies every claim: quotes must exist on the cited page, table rows must match required flags and types, and the document's own samples must validate. Failures loop back with precise feedback (at most 2 retries); what remains is quarantined. Conflicts between two grounded parts of the document are reported as spec defects. The verified contract then tests real code: it is compared against a community OpenAPI conversion, and the document's response samples are replayed through the py-unifi-access client's Pydantic models.
>
> **Results.** {coverage} · {grounding} · {loop} · {audit} · {findings} · {impact}  ← from metrics.json
>
> **Built with IBM Bob 2.0.** Agent mode (test-first engine build), Plan mode, document understanding, subagents, parallel tasks, custom mode + skill + slash commands, checkpoints. All task sessions are exported in `bob_sessions/`.

## 5. `bob_sessions` curation (Sun 14:30–15:30)
1. For every task T01–T14, confirm that `exports/T0X.md` and `screenshots/T0X.png` exist.
2. Fill in `bob_sessions/INDEX.md`: goal, modes, features, commit hash.
3. Scan the exports: run `gitleaks detect --source bob_sessions`, and grep for tokens and emails.
4. Commit: `T15: session evidence curated`.

## 6. Final QA checklist (Sun 16:00–18:00)
- [ ] Fresh clone in a new folder: `make setup fetch pipeline eval` all green
- [ ] `make check` green; coverage ≥ 85%
- [ ] Live URL opens on desktop and mobile; no console errors; no external requests
- [ ] README results match `metrics.json` (generated by script)
- [ ] Every claimed finding is CONFIRMED in `findings_review.csv`
- [ ] Video ≤ 5:00, every number checked; slides exported to PDF
- [ ] `docs/AI_USAGE_LOG.md` complete; `VERIFIED_FACTS.md` updated (U1–U6)
- [ ] gitleaks clean on the whole repo
- [ ] Submitted by 18:00 BST; screenshot of the submission confirmation saved
- [ ] Post-hackathon feedback form (eligible for the 20 × $100 participant rewards)
