# Source Adapter Operator Session Acceptance Runtime

This implementation milestone adds `source_adapter_operator_session_acceptance_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator session acceptance rows for run session IDs, approved actions, imported outputs, required receipts, and signoff readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_OPERATOR_SESSION_ACCEPTANCE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_SESSION_ACCEPTANCE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_OPERATOR_SESSION_ACCEPTANCE_RUNTIME_ROWS_READY`
