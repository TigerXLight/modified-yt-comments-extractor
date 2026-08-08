# Source Adapter Evidence Taxonomy Enforcement Runtime

This implementation milestone adds `source_adapter_evidence_taxonomy_enforcement_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence taxonomy enforcement rows applying source kind, capture method, preservation status, and review decision categories.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_TAXONOMY_ENFORCEMENT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_TAXONOMY_ENFORCEMENT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_TAXONOMY_ENFORCEMENT_RUNTIME_ROWS_READY`
