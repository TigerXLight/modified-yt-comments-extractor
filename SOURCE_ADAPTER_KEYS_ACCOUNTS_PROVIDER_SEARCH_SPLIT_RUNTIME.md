# Source Adapter KEYS Accounts Provider Search Split Runtime

This implementation milestone adds `source_adapter_keys_accounts_provider_search_split_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers KEYS/ACCOUNTS search split rows confirming Keys search scans added providers while Add Provider search scans the full catalogue.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_SEARCH_SPLIT_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_SEARCH_SPLIT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_KEYS_ACCOUNTS_PROVIDER_SEARCH_SPLIT_RUNTIME_ROWS_READY`
