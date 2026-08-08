# Source Adapter Provider Failure Escalation Runtime

This implementation milestone adds `source_adapter_provider_failure_escalation_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider failure escalation rows for retryable errors, manual repair paths, alternate providers, and operator-visible diagnostics.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_FAILURE_ESCALATION_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_FAILURE_ESCALATION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_FAILURE_ESCALATION_RUNTIME_ROWS_READY`
