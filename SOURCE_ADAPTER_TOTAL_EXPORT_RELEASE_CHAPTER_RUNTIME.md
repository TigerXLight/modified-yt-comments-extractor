# Source Adapter Total Export Release Chapter Runtime

This implementation milestone adds `source_adapter_total_export_release_chapter_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export release chapter rows for release package bridge records, release indexer entries, package digest references, and operator acceptance receipt links.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_CHAPTER_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_CHAPTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_TOTAL_EXPORT_RELEASE_CHAPTER_RUNTIME_ROWS_READY`
