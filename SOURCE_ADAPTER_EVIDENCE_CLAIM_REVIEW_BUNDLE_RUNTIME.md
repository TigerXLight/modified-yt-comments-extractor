# Source Adapter Evidence Claim Review Bundle Runtime

This implementation milestone adds `source_adapter_evidence_claim_review_bundle_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence claim review bundle rows for claim IDs, source artifacts, taxonomy compliance, review decisions, and database write readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_CLAIM_REVIEW_BUNDLE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_CLAIM_REVIEW_BUNDLE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_CLAIM_REVIEW_BUNDLE_RUNTIME_ROWS_READY`
