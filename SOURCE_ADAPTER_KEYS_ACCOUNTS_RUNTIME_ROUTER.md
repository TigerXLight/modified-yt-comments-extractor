# Source Adapter KEYS Accounts Runtime Router

This implementation milestone adds `source_adapter_keys_accounts_runtime_router` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS runtime router rows that keep added providers, full catalogue search, provider account binding, and secret reference lookups separated.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_RUNTIME_ROUTER_ROWS_READY`
