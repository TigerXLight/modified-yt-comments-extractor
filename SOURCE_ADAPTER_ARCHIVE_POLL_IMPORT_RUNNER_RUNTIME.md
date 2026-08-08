# Source Adapter Archive Poll Import Runner Runtime

This implementation milestone adds `source_adapter_archive_poll_import_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive poll/import runner rows for delayed provider receipts, retries, imported archive URLs, proof hashes, and review-ready evidence records.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_POLL_IMPORT_RUNNER_RUNTIME_ROWS_READY`
