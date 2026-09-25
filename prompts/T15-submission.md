# T15: Video, slides, submission package

Est. 4 h · Human-led; Bob in Ask mode for drafting from verified data; Claude Code CC-4 for the number check

## S1: Bob, Ask mode (draft the submission text ONLY from verified data)
```text
Read artifacts/metrics.json, artifacts/findings.json (only findings whose review.status is
CONFIRMED), eval/audit/findings_review.csv, docs/DEMO_AND_SUBMISSION.md section 4, and
bob_sessions/INDEX.md.
Write, into review/SUBMISSION_DRAFT.md:
1. Short description (max 150 characters).
2. Long description, following the template in DEMO_AND_SUBMISSION section 4. Fill {results}
   with the EVALUATION_FRAMEWORK section 7 sentence templates, using exact numbers with
   denominators.
3. A "claims ledger" table: every numeric or factual claim in (1) and (2) -> its source file
   and JSON key (or finding ID).
Rules: no claim without a ledger row; no rounding up; mention only CONFIRMED findings;
neutral wording about third parties.
```

## S2: Bob, Ask mode (video script from verified data)
```text
Using docs/DEMO_AND_SUBMISSION.md section 1 as the structure and the same sources as the
submission draft, write review/VIDEO_SCRIPT.md: a timed script (<= 4:50) with columns time,
screen, voice-over. Every number in the voice-over must come from the claims ledger in
review/SUBMISSION_DRAFT.md. Mark pre-recorded Bob segments as "recorded during the build".
Keep the voice-over at or under 130 words per minute.
```

## S3: Bob, Ask mode (slides outline)
```text
Produce review/SLIDES_OUTLINE.md: 10 slides following DEMO_AND_SUBMISSION section 2. For
each slide: title, max 25 words of on-slide text, the exact screenshot or artifact to show
(a path in the repo), and speaker notes. Numbers only from the claims ledger.
```

## Human checklist (do in order)
1. Take screenshots: PDF p.52 and p.56 side by side; the report hero; a finding card; the loop funnel; the Bob subagent fan-out; a Bob session summary.
2. Build the slides from `SLIDES_OUTLINE.md` (any tool) and export them to PDF.
3. Record the video per `VIDEO_SCRIPT.md` (≤ 5:00, 1080p MP4).
4. Run **CC-4** (the claims check) on the final description, slides text and script.
5. Curate `bob_sessions` (DEMO_AND_SUBMISSION §5); run `gitleaks detect --source .`.
6. Final QA checklist (DEMO_AND_SUBMISSION §6), then **submit by 18:00 BST** and screenshot the confirmation.
7. After the event: fill in the feedback form.
