# Source Adapter Media ASR Source Bridge Runtime

This implementation milestone adds `source_adapter_media_asr_source_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers media ASR source bridge rows for local large-v3 Vulkan references, cloud transcript receipts, keyterm notes, and source handoff IDs.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MEDIA_ASR_SOURCE_BRIDGE_RUNTIME_ROWS_READY`
