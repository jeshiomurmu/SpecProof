# T14: Deploy, README results, fresh-clone reproducibility

Est. 45 min · Modes: Agent → (Claude Code CC-2 for the reproducibility check)
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check && make eval`

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding.

TASK
T14: make the results public and reproducible.

DELIVERABLES
1. scripts/readme_results.py: reads artifacts/metrics.json and findings.json and replaces
   the Results table in README.md between the markers
   <!-- RESULTS:START --> and <!-- RESULTS:END --> (add the markers around the existing
   table). Rows use the sentence templates in docs/EVALUATION_FRAMEWORK.md section 7.
   Null metrics render as "pending (<reason>)". Idempotent. Add `make readme`.
   Add a unit test that runs it twice on a fixture and asserts identical output.
2. Static deployment, choosing ONE:
   (a) GitHub Pages: .github/workflows/pages.yml that runs `make site` on push to main and
       publishes dist/site with actions/upload-pages-artifact and actions/deploy-pages.
       The committed artifacts are enough; the workflow must NOT run extraction or fetch.
   (b) Vercel static: vercel.json with outputDirectory "dist/site" and buildCommand
       "make site" (only if the human confirms Vercel is preferred).
   Default to (a) unless told otherwise.
3. README.md: add the live URL placeholder <<LIVE_URL>> under the title, and a "Reproduce"
   section: make setup, make fetch, make pipeline, make eval, with the expected runtime.
4. Run `make readme`, `make site`, and `make check`.

CONSTRAINTS
No hand-typed numbers anywhere in README.md. Do not modify artifacts except via the CLI.

ACCEPTANCE CRITERIA
The README results table is generated; dist/site/index.html exists; make check is green.
Paste the generated table verbatim.

OUTPUT
SESSION SUMMARY.
```

## Human
1. Push, enable GitHub Pages (Settings → Pages → Source: GitHub Actions), wait for the deploy, and open the URL on desktop **and** phone.
2. Replace `<<LIVE_URL>>` in the README with the real URL, run `make readme`, and commit.
3. Run **CC-2** (fresh-clone reproducibility) in Claude Code, or do it by hand in a new folder.

Commit: `T14: deploy + generated README results`.
