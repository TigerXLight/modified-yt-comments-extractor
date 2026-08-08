# Source Adapter KEYS Accounts Provider Add Flow Runtime

This implementation milestone adds `source_adapter_keys_accounts_provider_add_flow_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS provider add-flow rows for selecting a catalogue provider, creating an added-provider record, alias binding, and receipt-safe configuration.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ADD_FLOW_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ADD_FLOW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_ADD_FLOW_RUNTIME_ROWS_READY`
