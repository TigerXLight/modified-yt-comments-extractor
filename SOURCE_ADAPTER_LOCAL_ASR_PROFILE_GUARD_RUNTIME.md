# Source Adapter Local ASR Profile Guard Runtime

This implementation milestone adds `source_adapter_local_asr_profile_guard_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers local ASR profile guard rows preserving large-v3 whisper.cpp Vulkan on AMD RX 5700 as the benchmark-backed local recommendation.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_LOCAL_ASR_PROFILE_GUARD_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_LOCAL_ASR_PROFILE_GUARD_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_LOCAL_ASR_PROFILE_GUARD_RUNTIME_ROWS_READY`
