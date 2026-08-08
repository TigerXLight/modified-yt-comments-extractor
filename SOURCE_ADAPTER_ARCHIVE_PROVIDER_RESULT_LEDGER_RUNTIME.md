# Source Adapter Archive Provider Result Ledger Runtime

This implementation milestone adds `source_adapter_archive_provider_result_ledger_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive provider result ledger rows for archive URLs, provider state, imported evidence, proof hashes, retries, and review status.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_RESULT_LEDGER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_RESULT_LEDGER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_RESULT_LEDGER_RUNTIME_ROWS_READY`
