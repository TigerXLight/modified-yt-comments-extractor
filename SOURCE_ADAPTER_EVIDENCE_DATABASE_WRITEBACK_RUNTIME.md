# Source Adapter Evidence Database Writeback Runtime

This implementation milestone adds concrete callable runtime surfaces to move the shared Source Adapter chain closer to production execution. It keeps `KEYS/ACCOUNTS` as the credential-reference surface, stores only redacted references or hashes in receipts, and makes provider execution state inspectable through deterministic Python APIs, CLI output, store artifacts, verifier checks, and docs tests.

The milestone is part of the post-provider-integration chain. It links real provider configuration, browser-driver binding, archive/release policy, provider receipts, evidence sync, Total Export finalization, GUI operator history, release review acceptance, and operator dashboard state.

Status strings covered by tests:

- `SOURCE_ADAPTER_EVIDENCE_DATABASE_WRITEBACK_RUNTIME_BUILT`
- runtime handoff ready status
- verifier issue count equals zero
