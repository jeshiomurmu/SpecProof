# START HERE: Step-by-step guide from zero to submission

All times are Bangladesh Standard Time (BST). Kickoff: **Fri 25 Sep, 21:00**. Internal submit target: **Sun 27 Sep, 18:00**. Hard deadline: 21:00.

> **The two rules that decide whether this wins:**
> 1. **IBM Bob 2.0 builds the product.** Judges score "clear application of IBM Bob 2.0", and the submission requires Bob session screenshots. Claude Code is only the reviewer (see Step 3).
> 2. **No number without evidence.** Every claim comes from `artifacts/metrics.json` or a confirmed finding.

---

## Step 0: Before kickoff (now → 21:00)

### 0.1 Install tools
| Tool | Install | Verify |
|---|---|---|
| Python 3.11+ | python.org or your package manager | `python3 --version` |
| git | git-scm.com | `git --version` |
| IBM Bob IDE | bob.ibm.com/download; sign in with your IBMid | Bob opens; the chat panel is visible |
| poppler (optional, recommended) | macOS `brew install poppler` · Ubuntu `sudo apt install poppler-utils` · Windows: poppler release zip, added to PATH | `pdftotext -v` |
| gitleaks | macOS `brew install gitleaks` · others: GitHub releases | `gitleaks version` |
| Claude Code (optional) | macOS/Linux `curl -fsSL https://claude.ai/install.sh \| bash` · Windows PowerShell `irm https://claude.ai/install.ps1 \| iex` (npm install is deprecated) | `claude --version` |

### 0.2 Create the repo and commit the kit
```bash
mkdir specproof && cd specproof && git init -b main
# copy every file from this kit into the folder (keep the .bob/ directory and dotfiles)
cat > .gitignore <<'GI'
artifacts/work/
.venv/
__pycache__/
.mypy_cache/
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage
.specproof_task_base
GI
git add -A && git commit -m "T00: planning kit (pre-event, docs + Bob config only, no product code)"
# create a PUBLIC GitHub repo named specproof, then:
git remote add origin https://github.com/<you>/specproof.git && git push -u origin main
```
The pre-kickoff commit timestamp honestly documents that only planning existed before the event.

### 0.3 Read these, in order (≈ 25 min)
1. `docs/VERIFIED_FACTS.md`: what's proven and what isn't
2. `docs/IMPLEMENTATION_PLAN.md` §1–3: timeline and task cards
3. `docs/TECHNICAL_ARCHITECTURE.md` §5–7: data contracts, rules, state machine
4. `docs/LOOP_ENGINEERING.md`: how every task runs

### 0.4 Prepare the manual baseline (15 min, recommended now)
Time yourself transcribing **one** endpoint by hand (EVALUATION_FRAMEWORK §5). Doing it before you see any SpecProof output keeps the baseline honest. Do the other two on Saturday night.

---

## Step 1: Kickoff (21:00–22:30)

| Time | Event | What you do |
|---|---|---|
| 21:00 | Kickoff | Watch the Twitch stream |
| 21:35 | Hackathon guide | **Write down:** Bobcoin allowance (U1), how access is delivered, the session-export format, and any rules on other AI tools and pre-event preparation (U5) |
| 22:00 | Discord Q&A | Ask: *"Is it OK to use Claude Code for review alongside Bob if Bob does the building and all sessions are exported? Are planning docs written before kickoff fine?"* |

Update `docs/VERIFIED_FACTS.md` (move U1 and U5 to verified) and adjust `docs/IMPLEMENTATION_PLAN.md` §2 (Bobcoin tiers). Commit.

**If the answers change anything** (for example, other AI tools are banned), drop Claude Code entirely; nothing in the plan depends on it.

---

## Step 2: Set up Bob on the repo (22:30–22:50)

1. **Open the folder in Bob IDE:** File → Open Folder → `specproof`.
2. **Confirm Bob loaded the instructions.** In **Ask** mode, send:
   `Summarize the rules from AGENTS.md and .bob/rules that you must follow in this project, in 5 bullets.`
   You should see: AI proposes/code decides, never fabricate, tests first, protected paths, and session evidence. If not, check that `AGENTS.md` sits at the repo root.
3. **Do not run `/init`.** It would overwrite our AGENTS.md. If Bob suggests it, decline.
4. **Confirm the custom mode.** Open the mode selector and look for **Spec Auditor**. If it's missing, reload the window. If it's still missing, create it via the UI: mode selector → gear → **+**, with these values:

   | Field | Value |
   |---|---|
   | Slug | `spec-auditor` |
   | Name | `Spec Auditor` |
   | Description | Extracts cited, verifiable API contracts from document-only specs and drives the SpecProof verification loop. |
   | Scope | Project |
   | Role definition | copy `roleDefinition` from `.bob/custom_modes.yaml` |
   | When to use | copy `whenToUse` |
   | Custom instructions | copy `customInstructions` |
   | Tools | Read files, Edit files, Run commands |

5. **Confirm the skill and commands.** Type `/` in the chat: you should see `sp-extract`, `sp-verify`, `sp-loop` and `sp-report`. In Ask mode, ask: `Which skills are available in this project?` You should see `specproof-extract`.
6. Enable **checkpoints** in Bob settings, if they're not on by default.
7. Record the results in `docs/VERIFIED_FACTS.md` (U2, U3). Commit.

---

## Step 3: Claude Code inside Bob (optional, 5 min)

Bob's IDE has an integrated terminal. Open it (Terminal → New Terminal), `cd` to the repo, and run `claude`. Authenticate with your own Claude plan the first time. Claude Code reads `CLAUDE.md`, which imports `AGENTS.md` and restricts it to the **reviewer / red-team** role.

**Use it only for:**
- `Review the diff of the last commit against CLAUDE.md's checklist; write review/REVIEW_T05.md.` Use this after T05, T06 and T10.
- A second independent vote on the blind audit sheet (T13).
- A fresh-clone reproducibility check (T14).

Log every use in `docs/AI_USAGE_LOG.md`. **Never** let it implement task cards. That would shrink the Bob evidence the judges score.

---

## Step 4: Build the engine (Fri 22:50 → Sat 12:30): tasks T01–T06

For **every** task, use the production prompts in **`prompts/`** (read `prompts/README.md` once). Each task file has Plan (P), Agent (A) and Ask (V) blocks to paste in order. The ritual (from LOOP_ENGINEERING, Loop A):

```text
1. Terminal:   git rev-parse HEAD > .specproof_task_base
2. Bob (new task) → Ask mode: paste prompts/00-session-bootstrap.md
   Bob → Plan mode:  paste block P from prompts/T0X-*.md
3. Bob → Agent mode: paste block A from prompts/T0X-*.md (then block V in Ask mode)
4. Watch; if an attempt goes sideways → roll back to the checkpoint and restate
5. Terminal:   make check && specproof guard   (both green)
6. Terminal:   git add -A && git commit -m "T0X: <summary>"
7. Bob:        export the task history → bob_sessions/exports/T0X.md
               screenshot the consumption summary → bob_sessions/screenshots/T0X.png
               add a row to bob_sessions/INDEX.md
```

**Milestones:**
- By **02:00 Sat**, T03 is done: the real PDF is segmented and `sections_index.json` is committed with ≥ 107 endpoint sections.
- By **12:30 Sat**, T06 is done: the verifier and loop are green on the synthetic PDF, including the mutation matrix (ENG-004).

**If you're stuck** (3 failed attempts): Bob writes `review/BLOCKED.md`. Read it. Then choose one: simplify the requirement, cut per IMPLEMENTATION_PLAN §4, or ask Claude Code for a review of the blocker, and hand its suggestion back to Bob as a new prompt.

---

## Step 5: Extraction (Sat 12:30 → 18:30): T07 pilot, then T08

1. **Pilot (T07).** Follow `prompts/T07-extraction-pilot.md` (it includes `touch .specproof_extraction_task`, which turns on the guard). Check:
   - S-3.2 → VERIFIED
   - S-4.2 → VERIFIED_WITH_SPEC_FINDINGS, with the `visit_reason` finding citing pages 52 and 56

   If it fails, improve the skill wording, bump `prompt_version` to `extract-v2`, and re-pilot. **Don't scale a broken prompt.**
2. **Full run (T08).**
   - Follow `prompts/T08-extraction-full.md`: orchestrator O1 per chapter (4 first, then 3, then the rest), started as parallel/background tasks, with the embedded subagent brief.
   - **Screenshot the subagent fan-out and the parallel tasks.** Those images are key judge evidence.
   - Run `/sp-loop`, then `/sp-loop` again, then `specproof classify`.
   - Finally run `specproof guard`, then commit.
3. Watch your Bobcoins. If you're under budget, follow the fallback in IMPLEMENTATION_PLAN §2.

---

## Step 6: Compare, conform, measure (Sat 18:30 → 23:30): T09–T11
Follow the task cards. After T11, run `make pipeline && make eval`. If the gate fails, follow Loop C (diagnose, route to Loop A or B, **never** edit thresholds).

---

## Step 7: Report, audit, confirm (Sun 05:30 → 10:30): T12–T13
- T12 builds the HTML evidence pack.
- T13 is yours:
  - the blind audit of 40 items;
  - confirming or rejecting every finding against the PDF and the code;
  - finishing the manual baseline.

**Only CONFIRMED findings go in the pitch.**

---

## Step 8: Ship (Sun 10:30 → 18:00): T14–T15
1. Deploy the static site (T14). Generate the README results table from `metrics.json`. Run the fresh-clone test.
2. Record the video and build the slides, following `docs/DEMO_AND_SUBMISSION.md` §1–3.
3. Curate `bob_sessions` (§5), run the final QA checklist (§6), and **submit by 18:00**.
4. After the event, fill in the feedback form (it qualifies you for the participant rewards).

---

## Emergency playbook

| Situation | Action |
|---|---|
| Bob access delayed at kickoff | Do the manual baseline, the spike on pdftotext vs pdfplumber, and fixture design by hand; start T01 the moment access lands |
| Bobcoins nearly gone | Stop extraction at ≥ 0.90 coverage; spend what's left only on the loop for sections that are almost passing |
| Real PDF segmentation count ≠ 107 | Don't force it. Document why in `review/SEG_NOTES.md`; the report states the true count |
| A finding turns out wrong in T13 | Mark it REJECTED and keep it out of the pitch. A rejected finding listed in the report shows rigor |
| Behind schedule on Sunday | Cut-list order (IMPLEMENTATION_PLAN §4). Submit a smaller true thing, never a bigger false one |
