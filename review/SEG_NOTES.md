# T03 segmentation notes

Input: `artifacts/work/pages.jsonl` (pdfplumber 0.11.10, PDF sha256 `d204c8b9…a534`).

## Result on the real PDF

`specproof segment` → **131 sections: 108 endpoint, 15 overview, 8 schema.**

## Why 108 endpoint sections, not 107

VERIFIED_FACTS F4 expected 107 (method, path) pairs, and the community OpenAPI has 107 operations. The segmenter finds 108 endpoint sections, each with exactly one `Request URL:` line and a distinct (method, path) hint. This matches F3, which counted 108 `Request URL` markers.

Diffing our pairs against the community operations (a count diagnostic only; nothing flows into extraction) leaves exactly one section:

- **S-11.7 "Allow Webhook Endpoint Owner to Receive Webhook"** (p179): `Request URL: Your webhook endpoint`, `Method: POST`. This documents the **inbound callback** that UniFi Access sends to the user's own server, not an API endpoint of the product.

It is still classified `endpoint` under the task card's rule (it contains `Request URL:`, a method and a field table). The algorithm was **not** tuned to reach 107.

**True count: 108 endpoint sections = 107 API endpoints + 1 inbound webhook callback without a fixed path.** Metrics and the report must state this, not "107 endpoints".

## Deviations from the task-card algorithm (genuine bugs only)

1. **page_end uses the last non-blank line.** pdfplumber pads the top of each page with blank lines. When the next heading is the first text on a page, the last line before it was a blank on that page, which made S-2.2 on FX-01 span pages 4–6 instead of 4–5 (SEG-005). page_end is now the page of the last non-blank line before the next heading.
2. **Titles are normalized** with `util.text.norm`. Layout extraction kept column spacing inside titles (`User  Registration`).
3. **A path hint must contain `/`.** Otherwise it is `None`. Before this fix, S-11.7 produced the bogus hint `/Your`. V4 path checks must skip sections with a `None` path hint.
