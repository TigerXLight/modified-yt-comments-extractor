# Source Adapter Transcript Profile Runtime

This implementation milestone adds `source_adapter_transcript_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers transcript profile rows for local/cloud ASR source references, term coverage review, transcript artifact digests, and release package linkage.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TRANSCRIPT_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TRANSCRIPT_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TRANSCRIPT_PROFILE_RUNTIME_ROWS_READY`
