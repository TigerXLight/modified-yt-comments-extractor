# Source Adapter Failure Retry Executor Runtime

This implementation milestone adds `source_adapter_failure_retry_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers failure retry executor rows for retry, skip, requeue, receipt replay, and operator audit trail.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_FAILURE_RETRY_EXECUTOR_RUNTIME_ROWS_READY`
