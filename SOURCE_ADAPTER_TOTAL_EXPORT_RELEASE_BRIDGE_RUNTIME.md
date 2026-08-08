# Source Adapter Total Export Release Bridge Runtime

This implementation milestone adds `source_adapter_total_export_release_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export release bridge rows linking package assembly, release index, upload target, and publish receipt.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_BRIDGE_RUNTIME_ROWS_READY`
