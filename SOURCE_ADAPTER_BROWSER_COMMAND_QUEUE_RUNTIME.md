# Source Adapter Browser Command Queue Runtime

This implementation milestone adds `source_adapter_browser_command_queue_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers browser command queue rows for operator-copyable browser launches, profile binding, queued capture commands, and dry-run previews.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_BROWSER_COMMAND_QUEUE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_BROWSER_COMMAND_QUEUE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_BROWSER_COMMAND_QUEUE_RUNTIME_ROWS_READY`
