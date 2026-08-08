# Source Adapter Release Index Publish Runtime

This implementation milestone adds `source_adapter_release_index_publish_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers release index publish rows that finalize package index, publish receipts, upload targets, and release locks.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME_ROWS_READY`
