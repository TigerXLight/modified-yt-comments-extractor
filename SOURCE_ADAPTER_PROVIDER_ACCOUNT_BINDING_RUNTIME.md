# Source Adapter Provider Account Binding Runtime

This implementation milestone adds `source_adapter_provider_account_binding_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider account binding rows connecting providers, capabilities, KEYS/ACCOUNTS references, redacted hashes, and execution surfaces.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_ACCOUNT_BINDING_RUNTIME_ROWS_READY`
