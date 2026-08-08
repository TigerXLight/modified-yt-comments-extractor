# Source Adapter Archive Evidence Normalizer Runtime

This implementation milestone adds `source_adapter_archive_evidence_normalizer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive evidence normalizer rows for Wayback/archive.ph/Ghostarchive/perma style receipt fields and normalized provenance.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_EVIDENCE_NORMALIZER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_EVIDENCE_NORMALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_EVIDENCE_NORMALIZER_RUNTIME_ROWS_READY`
