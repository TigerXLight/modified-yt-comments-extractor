# Source Adapter ASR Result Source Binding Runtime

This implementation milestone adds `source_adapter_asr_result_source_binding_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers ASR result source binding rows linking transcript outputs, source media, ASR profiles, evidence claims, and Total Export source appendices.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_ASR_RESULT_SOURCE_BINDING_RUNTIME_ROWS_READY`
