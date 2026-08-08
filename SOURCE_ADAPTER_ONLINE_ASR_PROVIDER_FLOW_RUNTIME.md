# Source Adapter Online ASR Provider Flow Runtime

This implementation milestone adds `source_adapter_online_asr_provider_flow_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Online ASR provider flow rows for ElevenLabs Scribe v2 candidate wiring, cloud provider references, keyterms, receipt import, and approval-gated execution.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_ONLINE_ASR_PROVIDER_FLOW_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_ONLINE_ASR_PROVIDER_FLOW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_ONLINE_ASR_PROVIDER_FLOW_RUNTIME_ROWS_READY`
