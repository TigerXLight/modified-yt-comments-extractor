# Source Adapter Article Comment Profile Executor Runtime

This implementation milestone adds `source_adapter_article_comment_profile_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers article/comment profile executor rows for web article snapshots, embedded comment capture, archive receipts, and evidence/source claim linkage.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_ARTICLE_COMMENT_PROFILE_EXECUTOR_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_ARTICLE_COMMENT_PROFILE_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_ARTICLE_COMMENT_PROFILE_EXECUTOR_RUNTIME_ROWS_READY`
