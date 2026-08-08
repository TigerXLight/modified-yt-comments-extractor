# Source Adapter KEYS Accounts Add Provider Ticket Runtime

This implementation milestone adds `source_adapter_keys_accounts_add_provider_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS add provider ticket rows for creating added-provider records from catalogue results, alias binding, capability defaults, and receipt-safe configuration.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_ADD_PROVIDER_TICKET_RUNTIME_ROWS_READY`
