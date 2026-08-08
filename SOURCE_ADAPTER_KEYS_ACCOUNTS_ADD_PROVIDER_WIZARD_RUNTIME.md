# Source Adapter KEYS Accounts Add Provider Wizard Runtime

This implementation milestone adds `source_adapter_keys_accounts_add_provider_wizard_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS add-provider wizard rows for searchable full catalogue, provider metadata, account references, and no raw secret logging.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_WIZARD_RUNTIME_ROWS_READY`
