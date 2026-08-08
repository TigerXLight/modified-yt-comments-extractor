# Source Adapter Evidence Export Runtime Bridge

Status: `SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_BUILT`

This implementation consumes accepted smoke receipt review integration output and materializes the next runtime artifacts used by Source Evidence, Total Export, release indexing, and archive handoff delivery.

Implemented artifacts:

- `SOURCE_ADAPTER_EVIDENCE_EXPORT_QUEUE_READY` with five source evidence queue rows.
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_PACKAGE_READY` with five Total Export source rows and a manifest hash.
- `SOURCE_ADAPTER_RELEASE_INDEX_RUNTIME_PACKAGE_READY` with five release index rows.
- `SOURCE_ADAPTER_ARCHIVE_HANDOFF_RUNTIME_PACKAGE_READY` with five archive handoff rows.
- `SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_READY_FOR_RELEASE_ARCHIVE_DELIVERY` handoff status.

The bridge preserves `KEYS/ACCOUNTS` as the credential-reference surface and carries only redacted credential-reference metadata from reviewed receipts into release/export artifacts.

This is implementation wiring, not a planning-only document: the Python module builds concrete queue/export/index/handoff data structures, the store writes them atomically as JSON artifacts, and the verifier enforces row counts and status contracts.
