# Source Adapter Runbook Script Materialization Runtime

This implementation milestone adds `source_adapter_runbook_script_materialization_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers runbook script materialization rows that emit copyable operator commands with receipt and approval references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_RUNBOOK_SCRIPT_MATERIALIZATION_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RUNBOOK_SCRIPT_MATERIALIZATION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_RUNBOOK_SCRIPT_MATERIALIZATION_RUNTIME_ROWS_READY`
