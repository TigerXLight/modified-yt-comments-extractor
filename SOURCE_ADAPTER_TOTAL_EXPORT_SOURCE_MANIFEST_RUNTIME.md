# Source Adapter Total Export Source Manifest Runtime

This implementation milestone adds `source_adapter_total_export_source_manifest_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export source manifest rows for article/comment/media/archive source sections, digests, evidence claims, and appendix references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_MANIFEST_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_MANIFEST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_MANIFEST_RUNTIME_ROWS_READY`
