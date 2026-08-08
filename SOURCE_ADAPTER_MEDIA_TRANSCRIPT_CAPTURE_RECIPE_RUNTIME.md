# Source Adapter Media Transcript Capture Recipe Runtime

This implementation milestone adds `source_adapter_media_transcript_capture_recipe_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers media/transcript capture recipe rows for audio/video metadata, transcript sources, term coverage, and package references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MEDIA_TRANSCRIPT_CAPTURE_RECIPE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MEDIA_TRANSCRIPT_CAPTURE_RECIPE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MEDIA_TRANSCRIPT_CAPTURE_RECIPE_RUNTIME_ROWS_READY`
