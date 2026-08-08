# Source Adapter Total Export Assembly Runtime

This implementation milestone adds `source_adapter_total_export_assembly_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export assembly rows that collect receipts, evidence materialization, package manifests, and handoff state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_ASSEMBLY_RUNTIME_ROWS_READY`
