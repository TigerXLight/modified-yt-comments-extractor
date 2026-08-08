# Source Adapter GUI Live Capture Panel Runtime

This implementation milestone adds `source_adapter_gui_live_capture_panel_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI live capture panel rows for named-site selection, capture intent, approval state, command staging, and receipt imports.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_PANEL_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_PANEL_RUNTIME_ROWS_READY`
