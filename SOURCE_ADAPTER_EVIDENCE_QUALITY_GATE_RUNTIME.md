# Source Adapter Evidence Quality Gate Runtime

This implementation milestone adds `source_adapter_evidence_quality_gate_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence quality gate rows for taxonomy validity, claim-source linkage, review decision consistency, database writeback, and receipt chain validation.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_QUALITY_GATE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_QUALITY_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_QUALITY_GATE_RUNTIME_ROWS_READY`
