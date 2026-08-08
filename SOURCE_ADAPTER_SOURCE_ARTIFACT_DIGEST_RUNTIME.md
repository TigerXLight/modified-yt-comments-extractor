# Source Adapter Source Artifact Digest Runtime

This implementation milestone adds `source_adapter_source_artifact_digest_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source artifact digest rows for HTML, JSON, screenshot, transcript, archive, and release artifact checksums.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_ARTIFACT_DIGEST_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_ARTIFACT_DIGEST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_ARTIFACT_DIGEST_RUNTIME_ROWS_READY`
