# Source Adapter Archive Polling Scheduler Runtime

This implementation milestone adds `source_adapter_archive_polling_scheduler_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive polling scheduler rows for queued archive jobs, backoff attempts, result import waits, and operator-visible retry receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_POLLING_SCHEDULER_RUNTIME_ROWS_READY`
