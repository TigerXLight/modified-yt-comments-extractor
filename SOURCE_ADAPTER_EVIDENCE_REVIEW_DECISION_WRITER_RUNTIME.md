# Source Adapter Evidence Review Decision Writer Runtime

This implementation milestone adds `source_adapter_evidence_review_decision_writer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence review decision writer rows for accept/reject/needs-review status, operator notes, and receipt-safe state updates.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_REVIEW_DECISION_WRITER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_REVIEW_DECISION_WRITER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_REVIEW_DECISION_WRITER_RUNTIME_ROWS_READY`
