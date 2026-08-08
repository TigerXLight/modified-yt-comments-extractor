# Source Adapter Browser Context Launcher Runtime

This implementation milestone adds `source_adapter_browser_context_launcher_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers browser context launcher rows for viewport, user-agent, profile isolation, capture directory, and operator-visible launch receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME_ROWS_READY`
