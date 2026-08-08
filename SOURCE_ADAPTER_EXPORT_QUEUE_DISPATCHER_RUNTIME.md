# Source Adapter Export Queue Dispatcher Runtime

This implementation milestone adds `source_adapter_export_queue_dispatcher_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers export queue dispatcher rows for source packages, delivery targets, retry policy, and receipt ledger integration.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EXPORT_QUEUE_DISPATCHER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EXPORT_QUEUE_DISPATCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EXPORT_QUEUE_DISPATCHER_RUNTIME_ROWS_READY`
