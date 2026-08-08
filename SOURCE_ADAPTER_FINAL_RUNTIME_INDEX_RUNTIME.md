# Source Adapter Final Runtime Index Runtime

This implementation milestone adds `source_adapter_final_runtime_index_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers final runtime index rows listing implemented Source Adapter runtime surfaces, stores, CLIs, verifiers, docs, tests, and downstream integration points.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_FINAL_RUNTIME_INDEX_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_FINAL_RUNTIME_INDEX_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_FINAL_RUNTIME_INDEX_RUNTIME_ROWS_READY`
