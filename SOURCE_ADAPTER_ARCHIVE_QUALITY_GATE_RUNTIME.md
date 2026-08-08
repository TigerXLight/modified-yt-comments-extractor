# Source Adapter Archive Quality Gate Runtime

This implementation milestone adds `source_adapter_archive_quality_gate_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive quality gate rows for submitted URL parity, provider result status, archive URL verification, proof hashing, and manual fallback paths.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_QUALITY_GATE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_QUALITY_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_QUALITY_GATE_RUNTIME_ROWS_READY`
