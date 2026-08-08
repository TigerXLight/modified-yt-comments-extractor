# Source Adapter Browser Automation Command Writer Runtime

This implementation milestone adds `source_adapter_browser_automation_command_writer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers browser automation command writer rows for operator-copyable launch/capture commands, browser profiles, safe dry-run previews, and explicit approval identifiers.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_BROWSER_AUTOMATION_COMMAND_WRITER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_BROWSER_AUTOMATION_COMMAND_WRITER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_BROWSER_AUTOMATION_COMMAND_WRITER_RUNTIME_ROWS_READY`
