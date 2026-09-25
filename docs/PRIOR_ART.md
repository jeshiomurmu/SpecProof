# Prior art and SpecProof's delta

We name prior art ourselves, before judges find it. Searched 2026-09-25.

| Existing work | What it does | What it does not do |
|---|---|---|
| **SpeCrawler** (arXiv 2402.11625, 2024) | LLM pipeline that generates OpenAPI specs from diverse API documentation | No per-claim citations; no deterministic verification against the document's own samples; no code conformance |
| **Trail of Bits "Spec-to-Code Compliance Checker" skill** | LLM audit checking a codebase against its whitepaper or spec, citing document sections and code lines, with confidence scores | Blockchain-scoped; the LLM itself judges compliance; no machine contract; no sample replay |
| **Community UniFi OpenAPI** (YuDefine, MinerU + Claude) | One-off manual/AI conversion of this exact PDF | Unverified; the authors warn of omissions and errors |
| **OpenAPI diff tools** (oasdiff, openapi-diff) | Diff two machine-readable specs | Require a machine-readable spec to exist |
| **Contract testing** (Pact, Schemathesis, Spring Cloud Contract) | Test against a machine-readable contract | Same requirement |
| **Requirements traceability** (OpenFastTrace, Doorstop, StrictDoc; TraceLLM research) | Link requirements to code | LLM trace links reach roughly 52% precision in published benchmarks, so generated links need verification |

## Delta, in one sentence
SpecProof lets AI read the document, but never lets AI certify the result. Every extracted claim is checked by deterministic code against the document's own text and samples, failures loop back with precise feedback, and what survives is used to test real client code, all running natively inside IBM Bob 2.0.
