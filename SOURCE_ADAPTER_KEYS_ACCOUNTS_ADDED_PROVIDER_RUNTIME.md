# Source Adapter KEYS Accounts Added Provider Runtime

This implementation milestone adds `source_adapter_keys_accounts_added_provider_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS added-provider rows separating configured providers from searchable catalogue providers.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADDED_PROVIDER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADDED_PROVIDER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADDED_PROVIDER_RUNTIME_ROWS_READY`
