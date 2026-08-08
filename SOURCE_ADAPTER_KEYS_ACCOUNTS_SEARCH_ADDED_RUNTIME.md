# Source Adapter KEYS Accounts Search Added Runtime

This implementation milestone adds `source_adapter_keys_accounts_search_added_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS added-provider search rows that search configured providers only and preserve added-provider separation.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_SEARCH_ADDED_RUNTIME_ROWS_READY`
