# Source Adapter KEYS Accounts Catalogue Search Runtime

This implementation milestone adds `source_adapter_keys_accounts_catalogue_search_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS catalogue search rows for full-provider search, added-provider search separation, provider tags, and UI-safe metadata.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_CATALOGUE_SEARCH_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_CATALOGUE_SEARCH_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_CATALOGUE_SEARCH_RUNTIME_ROWS_READY`
