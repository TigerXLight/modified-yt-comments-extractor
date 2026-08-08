# Source Adapter Media Capture Runner Runtime

This implementation milestone adds `source_adapter_media_capture_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers media capture runner rows for media metadata, transcript source binding, local/cloud ASR handoff references, and release package evidence links.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MEDIA_CAPTURE_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MEDIA_CAPTURE_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MEDIA_CAPTURE_RUNNER_RUNTIME_ROWS_READY`
