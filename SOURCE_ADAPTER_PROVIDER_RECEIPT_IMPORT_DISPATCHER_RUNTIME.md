# Source Adapter Provider Receipt Import Dispatcher Runtime

This implementation milestone adds `source_adapter_provider_receipt_import_dispatcher_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider receipt import dispatcher rows for browser/archive/release/file-library receipts, failure receipts, and downstream acceptance.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_RECEIPT_IMPORT_DISPATCHER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_RECEIPT_IMPORT_DISPATCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_RECEIPT_IMPORT_DISPATCHER_RUNTIME_ROWS_READY`
