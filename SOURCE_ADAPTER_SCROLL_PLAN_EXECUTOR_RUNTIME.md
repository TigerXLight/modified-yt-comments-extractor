# Source Adapter Scroll Plan Executor Runtime

This implementation milestone adds `source_adapter_scroll_plan_executor_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers scroll plan executor rows for page expansion, comment overlays, viewport passes, manual resize notes, and completion receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SCROLL_PLAN_EXECUTOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SCROLL_PLAN_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SCROLL_PLAN_EXECUTOR_RUNTIME_ROWS_READY`
