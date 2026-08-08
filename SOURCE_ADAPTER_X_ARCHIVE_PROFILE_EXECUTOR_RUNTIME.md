# Source Adapter X Archive Profile Executor Runtime

This implementation milestone adds `source_adapter_x_archive_profile_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers X/Twitter archive profile executor rows for public URL capture, archive fallback ordering, Ghostarchive/archive.ph receipts, and manual result import.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_X_ARCHIVE_PROFILE_EXECUTOR_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_X_ARCHIVE_PROFILE_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_X_ARCHIVE_PROFILE_EXECUTOR_RUNTIME_ROWS_READY`
