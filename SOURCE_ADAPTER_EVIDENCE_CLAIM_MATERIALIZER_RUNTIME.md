# Source Adapter Evidence Claim Materializer Runtime

This implementation milestone adds `source_adapter_evidence_claim_materializer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence claim materializer rows mapping source artifacts to claim records, review state, taxonomy, and citations.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_CLAIM_MATERIALIZER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_CLAIM_MATERIALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_CLAIM_MATERIALIZER_RUNTIME_ROWS_READY`
