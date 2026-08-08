# Source Adapter YouTube Profile Runtime

This implementation milestone adds `source_adapter_youtube_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers YouTube profile rows for comment/video metadata capture, transcript/ASR linkage, archive fallback records, and Total Export source sections.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_YOUTUBE_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_YOUTUBE_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_YOUTUBE_PROFILE_RUNTIME_ROWS_READY`
