# Source Adapter Transcript Evidence Normalizer Runtime

This implementation milestone adds `source_adapter_transcript_evidence_normalizer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers transcript evidence normalizer rows for timestamps, source language, ASR profile, term review, and release/package digests.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME_ROWS_READY`
