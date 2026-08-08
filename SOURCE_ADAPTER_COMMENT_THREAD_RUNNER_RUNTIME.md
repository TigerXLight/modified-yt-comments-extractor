# Source Adapter Comment Thread Runner Runtime

This implementation milestone adds `source_adapter_comment_thread_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers comment thread runner rows for shadow-DOM expansion, comment harvesting, screenshot cadence, manual observation reconciliation, and evidence queue writes.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_COMMENT_THREAD_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_COMMENT_THREAD_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_COMMENT_THREAD_RUNNER_RUNTIME_ROWS_READY`
