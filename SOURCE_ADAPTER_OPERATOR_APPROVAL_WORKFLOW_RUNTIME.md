# Source Adapter Operator Approval Workflow Runtime

This implementation milestone adds `source_adapter_operator_approval_workflow_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator approval workflow rows for named-site selection, command generation, approval IDs, and receipt imports.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_OPERATOR_APPROVAL_WORKFLOW_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_APPROVAL_WORKFLOW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_OPERATOR_APPROVAL_WORKFLOW_RUNTIME_ROWS_READY`
