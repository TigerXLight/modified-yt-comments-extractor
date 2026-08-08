# Source Adapter Total Export Source Section Runtime

This implementation milestone adds `source_adapter_total_export_source_section_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export source section rows for captured artifacts, archive receipts, evidence links, and source/release manifest entries.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_SECTION_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_SECTION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_SECTION_RUNTIME_ROWS_READY`
