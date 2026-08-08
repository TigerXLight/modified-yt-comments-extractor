# Source Adapter Archive Fallback Planner Runtime

This implementation milestone adds `source_adapter_archive_fallback_planner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive fallback planner rows for failed submissions, alternate providers, manual import paths, expected receipts, and operator repair commands.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_FALLBACK_PLANNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_FALLBACK_PLANNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_FALLBACK_PLANNER_RUNTIME_ROWS_READY`
