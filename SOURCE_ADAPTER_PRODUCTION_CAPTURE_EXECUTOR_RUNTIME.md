# Source Adapter Production Capture Executor Runtime

This implementation milestone adds `source_adapter_production_capture_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers production capture executor rows for approved source runs, selected profile recipes, capture artifacts, archive requests, evidence commits, and release linkage.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PRODUCTION_CAPTURE_EXECUTOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PRODUCTION_CAPTURE_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PRODUCTION_CAPTURE_EXECUTOR_RUNTIME_ROWS_READY`
