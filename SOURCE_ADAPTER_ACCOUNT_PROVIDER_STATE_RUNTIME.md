# Source Adapter Account Provider State Runtime

This implementation milestone adds `source_adapter_account_provider_state_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers account/provider state rows for configured providers only, capability surfaces, operator-visible account metadata, and provider readiness states.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ACCOUNT_PROVIDER_STATE_RUNTIME_ROWS_READY`
