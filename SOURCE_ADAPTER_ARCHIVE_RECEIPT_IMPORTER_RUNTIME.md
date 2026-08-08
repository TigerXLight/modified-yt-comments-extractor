# Source Adapter Archive Receipt Importer Runtime

This implementation milestone adds `source_adapter_archive_receipt_importer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive receipt importer rows for external archive URLs, proof fields, provider status, hashes, and evidence package references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_RECEIPT_IMPORTER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_RECEIPT_IMPORTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_RECEIPT_IMPORTER_RUNTIME_ROWS_READY`
