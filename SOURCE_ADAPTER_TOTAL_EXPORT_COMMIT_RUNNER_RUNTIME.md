# Source Adapter Total Export Commit Runner Runtime

This implementation milestone adds `source_adapter_total_export_commit_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export commit runner rows for source sections, receipt indexes, artifact inventories, release manifests, and closeout handoff records.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_COMMIT_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_COMMIT_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_COMMIT_RUNNER_RUNTIME_ROWS_READY`
