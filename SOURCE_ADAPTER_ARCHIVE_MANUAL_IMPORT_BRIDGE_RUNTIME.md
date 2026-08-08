# Source Adapter Archive Manual Import Bridge Runtime

This implementation milestone adds `source_adapter_archive_manual_import_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive manual import bridge rows for operator-supplied archive.ph, Ghostarchive, Wayback, perma-like, and local preservation receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_MANUAL_IMPORT_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_MANUAL_IMPORT_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_MANUAL_IMPORT_BRIDGE_RUNTIME_ROWS_READY`
