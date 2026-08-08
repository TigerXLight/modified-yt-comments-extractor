# Source Adapter Provider Backend Contract Matrix Runtime

This implementation milestone adds `source_adapter_provider_backend_contract_matrix_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider backend contract matrix rows for capture/archive/release/file-library/ASR provider capabilities, dispatchers, receipts, and failure escalation.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_PROVIDER_BACKEND_CONTRACT_MATRIX_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_PROVIDER_BACKEND_CONTRACT_MATRIX_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_PROVIDER_BACKEND_CONTRACT_MATRIX_RUNTIME_ROWS_READY`
