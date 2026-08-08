# Source Adapter KEYS Accounts Provider State Store Runtime

This implementation milestone adds `source_adapter_keys_accounts_provider_state_store_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS provider state store rows for added providers, catalogue providers, account aliases, capabilities, and visible state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_STATE_STORE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_STATE_STORE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_STATE_STORE_RUNTIME_ROWS_READY`
