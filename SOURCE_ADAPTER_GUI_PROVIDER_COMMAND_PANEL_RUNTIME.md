# Source Adapter GUI Provider Command Panel Runtime

This implementation milestone adds `source_adapter_gui_provider_command_panel_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI provider command panel rows for provider choice, capability display, command staging, approval state, and run status visibility.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_PROVIDER_COMMAND_PANEL_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_PROVIDER_COMMAND_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_PROVIDER_COMMAND_PANEL_RUNTIME_ROWS_READY`
