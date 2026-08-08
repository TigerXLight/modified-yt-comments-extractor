# Source Adapter Local ASR Benchmark Lock Ticket Runtime

This implementation milestone adds `source_adapter_local_asr_benchmark_lock_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers local ASR benchmark lock ticket rows preserving whisper.cpp large-v3 Vulkan on AMD RX 5700 as the benchmark-backed recommended local profile.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_LOCAL_ASR_BENCHMARK_LOCK_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_LOCAL_ASR_BENCHMARK_LOCK_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_LOCAL_ASR_BENCHMARK_LOCK_TICKET_RUNTIME_ROWS_READY`
