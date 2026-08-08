# Source Adapter End-to-End Manifest Runtime

This implementation milestone adds `source_adapter_end_to_end_manifest_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers end-to-end manifest rows that combine capture, archive, evidence, Total Export, release delivery, KEYS/ACCOUNTS, GUI, and operator approval state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME_BUILT`
- `SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_END_TO_END_MANIFEST_RUNTIME_ROWS_READY`
