# T13: Blind audit, finding confirmation, manual baseline (you are the judge here)

Est. 60–75 min · Mostly human; Bob in Ask mode for bookkeeping; Claude Code as optional second auditor

## Step 1: Draw the sample (terminal)
```bash
specproof audit-sample --n 40 --seed 20260926
```
Never re-draw. The seed was fixed before extraction.

## Step 2: Judge 40 items (you)
Open `eval/audit/audit_sample.csv` and `artifacts/work/spec.pdf` side by side. For each row, go to `page` and set:
- `verdict` = `correct` if name, required, type and enum all match the document, else `incorrect`
- `reason` = a short note for any incorrect item (e.g. "required is F in the row")
- `missed_neighbor` = the name of any row in the same table the contract missed (if you notice one)

Do not look at `artifacts/verification/` while judging.

## Step 3 (optional): Second auditor
Run prompt **CC-3** from `CC-claude-code.md` in Claude Code on a copy of the sheet (`audit_sample_cc.csv`). Then:
```bash
python - <<'PY'
import csv
a={r['item_id']:r['verdict'] for r in csv.DictReader(open('eval/audit/audit_sample.csv'))}
b={r['item_id']:r['verdict'] for r in csv.DictReader(open('eval/audit/audit_sample_cc.csv'))}
agree=sum(a[k]==b.get(k) for k in a); print(f"agreement {agree}/{len(a)}")
print("disagreements:",[k for k in a if a[k]!=b.get(k)])
PY
```
Re-check every disagreement against the PDF yourself. Your verdict is final; record both in the report.

## Step 4: Confirm findings (you)
For every finding in `artifacts/findings.json`:
- **SPEC_***: open both cited pages and check that the quotes say what the finding claims.
- **COMMUNITY_***: open the PDF citation AND the community spec pointer.
- **CLIENT_SAMPLE_REJECTED**: re-run the generated replay test and see it fail yourself.

Write `eval/audit/findings_review.csv` with the columns `finding_id,status,reviewer,note`, where status is CONFIRMED or REJECTED.

## Step 5: Manual baseline (you)
If not already done, time yourself transcribing §3.8, §3.2 and §4.2 by hand (EVALUATION §5). Write `eval/audit/manual_baseline.csv` (`section_id,minutes,notes`). Disclose it in the report if this was done after seeing SpecProof output.

## Step 6: Bob, Ask mode (score and summarize)
```text
Run `specproof audit-score`, then `specproof report`, then `make eval`.
Paste verbatim: the audited_precision entry from metrics.json (numerator, denominator,
value, Wilson CI), verifier_false_accept, the confirmed/rejected counts per finding type,
and the full eval table. No commentary.
```

Commit: `T13: blind audit + finding confirmations + manual baseline`.
