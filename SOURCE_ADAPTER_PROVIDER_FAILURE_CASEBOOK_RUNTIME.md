# Source Adapter Provider Failure Casebook Runtime

This implementation milestone adds `source_adapter_provider_failure_casebook_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider failure casebook rows for retry decisions, alternate providers, manual repair actions, and operator-facing diagnostic messages.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_CASEBOOK_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_CASEBOOK_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_CASEBOOK_RUNTIME_ROWS_READY`
