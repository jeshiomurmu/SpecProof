# Findings pre-read (advisory, by Claude Code)

These notes help the human reviewer in T13. They are **not** confirmations: every finding stays a candidate until the human records a verdict in `eval/audit/findings_review.csv`. Claude Code built the engine that produced these findings, so this is not an independent opinion. Check each one against the cited PDF page.

Legend: **likely real** = the document looks wrong or self-contradictory; **likely reject** = an artefact of how the contract or the comparison models the section; **check** = unsure.

## Spec findings (30)

| ID | Section | Type | Pre-read |
|---|---|---|---|
| F-2518a1ed | S-4.2 | enum `visit_reason` | likely real: sample sends `"Interviemw"` |
| F-a96f5336 | S-4.5 | enum `visit_reason` | likely real: same typo |
| F-13962a9e | S-3.4 | malformed sample | likely real |
| F-c704b394 | S-3.24 | malformed sample | likely real |
| F-64374118 | S-5.9 | malformed sample | likely real |
| F-d0f1ee66 | S-6.15 | malformed sample | likely real |
| F-93d0b6a1 | S-10.1 | malformed sample | likely real |
| F-2d465646 | S-11.4 | malformed sample | likely real |
| F-0156e6d0 | S-11.5 | malformed sample | likely real |
| F-41067aa7 | S-3.5 | type `touch_pass` | likely real |
| F-959533e6 | S-5.16 | missing `week_schedule` | likely real |
| F-f718c698 | S-5.15 | missing `id` | likely real |
| F-895887db, F-623698f4, F-0f3b02b5 | S-7.2, S-7.3, S-7.4 | type `resources` (documented String) | likely real |
| F-72ea066d, F-4406a47e | S-7.7, S-7.8 | type `is_bind_hub` | likely real: table says String, sample sends a boolean |
| F-318d603b | S-8.1 | sample type | check: the sample nests device groups one level deeper than documented |
| F-b2274bf9 | S-9.2 | missing `msg` | check |
| F-4896b535, F-57e3eddb | S-9.2 | missing `actor`, `event` | likely reject: these sit under `data.hits[]._source`, which the contract models flat |
| F-9ee3d244, F-37cb6094, F-103cd2b4 | S-10.2 | missing `id`, `name`, `deleted` | likely reject: `data` is keyed by resource type, not a flat object |
| F-3202ab46, F-90f85c70, F-88db75e8 | S-10.4 | same | likely reject: same reason |
| F-2ce06a9c, F-ee160a81, F-040d4cd9 | S-10.6 | same | likely reject: same reason |

## Community discrepancies (30)

| ID(s) | Section | Pre-read |
|---|---|---|
| F-b3aac90a, F-c0e391d0 | S-9.3, S-9.2 | likely real: community enum for `topic` adds `all` |
| F-47123097 | S-8.4 | likely real: community makes `room_name` required; the PDF says optional |
| F-317997a8 plus the 10 S-8.3 missing-field rows | S-8.3 | check: the community spec nests the credential flags under `access_methods`; count this as one structural difference, not eleven |
| F-7926672f, F-cea82680, F-661399aa, F-7c094e3d | S-5.2, S-5.3 | check: `resource` (PDF) vs `resources` (community) |
| F-0e257d8c, F-2a2ebe0e, F-8ae38c53, F-9d686227, F-0bb8a784, F-ca1d797f, F-6546c17f, F-acc5c7d6 | various | likely reject: `Id`/`id`/`path` are path parameters that the PDF lists in its request-body table |
| F-af2adf84, F-fcda0304, F-933cc645, F-fd1c6e5e | S-3.30, S-6.19, S-12.1 | check: multipart upload fields (`file`, `cert`, `key`), which the community spec may model outside the JSON body |

## Client conformance (3)

| ID | Pre-read |
|---|---|
| F-1f37a3fc | check: `User.pin_code` is a string in the client; the PDF says Object |
| F-b21d3b42 | likely reject as a client bug: the client's boolean matches the PDF's own sample, so the table is what is wrong (see the S-7.7/S-7.8 spec findings) |
| F-c73ffe14 | likely reject: the PDF names the field `Id`, and the mapping compares names case-sensitively |
