# Source Adapter ASR Handoff Source Linker Runtime

This implementation milestone adds `source_adapter_asr_handoff_source_linker_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers ASR handoff source linker rows for local large-v3 Vulkan profile references, cloud ASR candidate receipts, transcript artifacts, and source evidence traceability.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ASR_HANDOFF_SOURCE_LINKER_RUNTIME_ROWS_READY`
