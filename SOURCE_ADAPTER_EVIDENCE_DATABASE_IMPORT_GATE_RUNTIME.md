# Source Adapter Evidence Database Import Gate Runtime

This implementation milestone adds `source_adapter_evidence_database_import_gate_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence database import gate rows for required review decisions, taxonomy validation, digest parity, queue writeback, and rollback-safe database commits.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_DATABASE_IMPORT_GATE_RUNTIME_ROWS_READY`
