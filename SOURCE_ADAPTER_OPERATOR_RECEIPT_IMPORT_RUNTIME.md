# Source Adapter Operator Receipt Import Runtime

This implementation milestone adds `source_adapter_operator_receipt_import_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator receipt import rows for manual/live smoke observations, browser receipts, archive receipts, and release receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_OPERATOR_RECEIPT_IMPORT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_RECEIPT_IMPORT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_OPERATOR_RECEIPT_IMPORT_RUNTIME_ROWS_READY`
