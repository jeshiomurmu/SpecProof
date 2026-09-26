# T02 spike: default PDF text extractor

Date: 2026-09-25 (BST). Input: `artifacts/work/spec.pdf`, sha256 `d204c8b9…a534` (verified by `specproof fetch`). Script: `review/spike_t02.py`.

Local `pdftotext` is **xpdf 4.00** (Glyph & Cog), not poppler. CI (Ubuntu `poppler-utils`) would run a different program.

## Checks from the task card

| Check | pdftotext -layout (xpdf 4.00) | pdfplumber 0.11 `layout=True` |
|---|---|---|
| p14 line matches `^\s*first_name\s{2,}T\s{2,}String` | yes: `first_name       T         String                                          1689150139  to Get` | yes: `        first_name    T        String First name of the user.` |
| p52 contains `enum reason {Interview,Business,Cooperation,Others}` | yes | yes |
| p56 contains `Interviemw` | yes: `"visit_reason": "Interviemw",` | yes: `"visit_reason": "Interviemw",` |

## Extra observation (decisive)

On p52, `pdftotext -layout` **misaligns the rows of the schema table**: the name column is shifted by two rows against the type/description columns:

```
pdftotext -layout, p52                          pdfplumber, p52
email              String   Visit reason: enum…  visitor_company    String Company of the visitor.
visitor_company    Integer  Start time of the…   visit_reason       String Visit reason: enum reason {…}
visit_reason       Integer  End time of the …    start_time         Integer Start time of the visit.
```

With pdftotext, `visit_reason` reads as `Integer`, which contradicts the document. Row-consistency checks (V2b, V5) would produce false failures. On p14, pdftotext also shifts descriptions by one row.

xpdf `pdftotext -table` keeps rows aligned (`visit_reason   String   Visit reason:  enum    reason   {…}`), but that mode does not exist in poppler, so it is not portable.

## Timing (194 pages, this machine, 4 cores)

| Extractor | Wall time |
|---|---|
| pdftotext -layout, all pages | 4.3 s |
| pdfplumber, sequential | 140.1 s |
| pdfplumber, 8 worker processes | 31.4 s (spike); 78.4 s and 104 s on later runs (machine load varies) |
| pdfplumber, 4 worker processes | 107.5 s |
| `specproof ingest` cache hit | 6.7 s |

## Decision

`auto` = **pdfplumber**, extracting pages in parallel worker processes, with a cache: ingest is skipped when `pages.jsonl` already matches the input sha256, extractor name and version.

Reasons:
1. Correctness: rows stay aligned, and pdftotext mis-assigns types.
2. Reproducibility: pdfplumber is a pinned Python dependency, so it gives the same text on every machine. `pdftotext` differs between xpdf and poppler.

`--extractor pdftotext` stays available for comparison.

## Addendum (T05): layout scale

Checking the verifier against the real PDF showed that pdfplumber's default horizontal scale (`x_density=7.25` points per character) turns the ~10 pt column gaps of most real tables into **one** space. The 2+-space row regex then saw only 4 of the 17 rows in S-4.2. Page 14, used in the spike, happens to have wider gaps.

| x_density | Rows detected on p13, 14, 52, 53, 54, 56 | S-4.2 rows |
|---|---|---|
| 7.25 (default) | 8 | 4 |
| 5 | 18 | 12 |
| 4 | 21 | 15 |
| **3** | **23** | **17 (all)** |

With `x_density=3`, the whole document yields 477 rows, and every endpoint section has at least one detected row (before: 14 had none). The verified facts still hold on the new text: the p52 enum, "Interviemw" on p56 and p63, and the p14 `first_name T String` row.

Follow-on changes:
1. Each page's common left margin is removed during ingest (the 72 pt margin became ~24 spaces).
2. The segmenter matches headings and `Request URL:` / `Method:` on whitespace-collapsed text, because wider spacing had pushed heading lines past the 80-character title limit.
3. `row_tokens` accepts only a real type word in the type column. A wrapped type cell such as "Array of / Strings" otherwise left a description word (`assign`) in the type position, which would cause a false `V2_ROW_MISMATCH`.

Segmentation after these changes is identical to T03's output (same 131 IDs, kinds, page ranges, hints and titles).

Consequences:
- The ingest performance budget (< 20 s, architecture §15) is **not met** on the first run (about 31 s here). Repeat runs hit the cache.
- TEST_PLAN ING-005 and architecture §12 assumed pdftotext as the default. Both are updated to point here.
- VERIFIED_FACTS F6 still holds (the row is on a single line), but it does not guarantee row alignment.
