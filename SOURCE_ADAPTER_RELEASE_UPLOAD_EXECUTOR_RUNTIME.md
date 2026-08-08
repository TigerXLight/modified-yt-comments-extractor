# Source Adapter Release Upload Executor Runtime

This implementation milestone adds `source_adapter_release_upload_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers release upload executor rows for release targets, package integrity, upload receipt, and signoff lock.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_RELEASE_UPLOAD_EXECUTOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RELEASE_UPLOAD_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_RELEASE_UPLOAD_EXECUTOR_RUNTIME_ROWS_READY`
