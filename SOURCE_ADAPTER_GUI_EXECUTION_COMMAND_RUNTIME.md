# Source Adapter GUI Execution Command Runtime

This implementation milestone adds `source_adapter_gui_execution_command_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI execution command rows that expose approval, readiness, runbook command export, and operator state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_EXECUTION_COMMAND_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_EXECUTION_COMMAND_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_EXECUTION_COMMAND_RUNTIME_ROWS_READY`
