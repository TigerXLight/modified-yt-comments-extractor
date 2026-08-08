# Source Adapter External Archive Provider Adapter Runtime

This implementation milestone adds `source_adapter_external_archive_provider_adapter_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers external archive provider adapter rows for submit/poll/import/verify action contracts and operator-approved execution.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EXTERNAL_ARCHIVE_PROVIDER_ADAPTER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EXTERNAL_ARCHIVE_PROVIDER_ADAPTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EXTERNAL_ARCHIVE_PROVIDER_ADAPTER_RUNTIME_ROWS_READY`
