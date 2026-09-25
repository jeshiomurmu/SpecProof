# T12: Evidence-pack report (HTML + SARIF) and end-to-end tests

Est. 90 min · Modes: Plan → Agent · Tests: RPT-001..007, GOV-002, GOV-004, E2E-001..003, CLI-002
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T12. Read docs/TECHNICAL_ARCHITECTURE.md sections 9 and 13, docs/EVALUATION_FRAMEWORK.md
sections 1 and 7, docs/DATA_GOVERNANCE_AND_LINEAGE.md section 7, docs/PRIOR_ART.md,
docs/DATA_QUALITY_AND_BIAS.md section 6, and docs/TEST_PLAN.md RPT/E2E rows. Propose the
report's section order and the data each section reads, in at most 20 lines. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer and product designer on SpecProof. AGENTS.md is binding. Test-first. This
page is what judges will open. It must be clear, credible, fast, and 100% traceable.

TASK
T12: render a single self-contained HTML evidence pack plus SARIF, and add the end-to-end
tests.

DELIVERABLES
1. report/templates/report.html.j2 + report/html.py render(state) -> str.
   Hard requirements:
   - Self-contained: inline CSS and JS only; no external fonts, scripts, images or CDNs;
     no fetch() calls. (RPT-002)
   - Theme: CSS variables on :root; dark via @media (prefers-color-scheme: dark); a
     system font stack; readable at 360px width (flex/grid; tables inside overflow-x:auto
     containers).
   - Accessible: semantic landmarks, headings in order, sufficient contrast, keyboard-usable
     filters.
   - No timestamps in the body. The footer shows the manifest's generation time in a
     data-generated attribute, rendered by a tiny inline script. (RPT-007)
   Sections, in order:
   a. Header: "SpecProof: <spec title>", source sha (short), links to the repo and to
      bob_sessions/INDEX.md.
   b. Hero metrics: coverage, grounding, final verified, audited precision (with CI),
      confirmed findings. EVERY value rendered as "a/b (x%)" from metrics.json; null
      values render as "pending - <reason>". (RPT-006)
   c. Loop funnel: attempt 1 -> after retry 1 -> after retry 2 -> final, drawn with plain
      CSS bars; counts per status.
   d. Findings: filter chips by type and severity (vanilla JS). Each card has a title,
      type, severity, review status badge (CANDIDATE / CONFIRMED / REJECTED), and
      evidence blocks: doc = "page N" + the quote in a blockquote; code = file:line +
      snippet. (RPT-003, RPT-004)
   e. Endpoints table: section, method, path, status, attempts, items, grounded, row_ok.
      Sortable by clicking headers (vanilla JS).
   f. Community comparison and client conformance summaries (counts + links to cards).
   g. "How this was built with IBM Bob 2.0": the feature map from architecture section 18,
      read from a small data file docs/bob_feature_map.json that you create now.
   h. Methodology (rules V1-V5 in one short table), Limitations (from DATA_QUALITY
      section 6), Prior art (from PRIOR_ART.md), Lineage (the manifest table: artifact,
      sha short, stage, producer).
2. report/sarif.py: SARIF 2.1.0 for code-kind findings (CLIENT_*): ruleId = type,
   level from severity, message, physicalLocation (artifactLocation.uri relative,
   region.startLine). (RPT-005)
3. CLI report: writes artifacts/report/index.html, artifacts/findings.json (all findings
   merged, sorted), artifacts/findings.sarif, and recomputes metrics.json first.
   Appends manifest records.
4. demo/index.html: a one-screen landing page (same design tokens) with the one-line pitch,
   3 hero numbers read at build time from metrics.json, and buttons "Open evidence pack"
   (./report/index.html), "Code" and "Bob sessions". Add `make site`, which assembles
   dist/site/ = demo/index.html + artifacts/report/.
5. Tests:
   tests/integration/test_report.py (RPT-001..007);
   tests/unit/test_governance.py (add GOV-002 and GOV-004);
   tests/e2e/test_pipeline_synthetic.py (E2E-001..003): the whole pipeline on FX-01 +
   FX-02 in tmp dirs. E2E-002 runs it twice and compares sha256 of every artifact type
   that gets committed, then writes artifacts/determinism.json ({"runs": 2,
   "identical": true|false, "differences": [...]}) when run against real artifacts;
   tests/e2e/test_real_source.py: E2E-R01..R03;
   tests/unit/test_cli.py: CLI-002.

METHOD
Tests first. Then the template. Then run `make pipeline && make eval` on real data and open
the HTML to check it visually: take a screenshot at desktop and at 390px width.

CONSTRAINTS
Every number in the HTML comes from metrics.json or findings.json. No hard-coded values.
Wording about third parties stays neutral (governance section 7).

ACCEPTANCE CRITERIA
make check green (final 5 lines); make test-e2e green, including E2E-R01; `make site`
produces dist/site/index.html; the report file size is printed.

OUTPUT
SESSION SUMMARY.
```

## V: Ask mode
```text
Run `make pipeline && make eval && make test-e2e`. Paste the eval table and the pytest
summary lines verbatim. Then grep the HTML for "http://" and "https://" and paste the
matching lines (there should be none outside plain anchor links in the prior-art section).
```
