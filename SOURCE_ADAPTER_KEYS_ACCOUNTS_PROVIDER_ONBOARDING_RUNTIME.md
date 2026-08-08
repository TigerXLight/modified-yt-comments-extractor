# Source Adapter KEYS Accounts Provider Onboarding Runtime

This implementation milestone adds `source_adapter_keys_accounts_provider_onboarding_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS provider onboarding rows for full catalogue selection, added-provider registry writes, provider capability defaults, and credential reference requirements.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ONBOARDING_RUNTIME_BUILT`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ONBOARDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ONBOARDING_RUNTIME_ROWS_READY`
