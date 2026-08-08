# Source Adapter GUI Source Capture Command Bar Runtime

This implementation milestone adds `source_adapter_gui_source_capture_command_bar_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI source capture command bar rows for profile selection, capture action staging, approval status, command generation, and imported receipt states.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_SOURCE_CAPTURE_COMMAND_BAR_RUNTIME_ROWS_READY`
