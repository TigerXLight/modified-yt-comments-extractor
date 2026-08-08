# Source Adapter Scroll Capture Controller Runtime

This implementation milestone adds `source_adapter_scroll_capture_controller_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers scroll capture controller rows for bounded page scroll, comment expansion, screenshot cadence, and capture receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SCROLL_CAPTURE_CONTROLLER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SCROLL_CAPTURE_CONTROLLER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SCROLL_CAPTURE_CONTROLLER_RUNTIME_ROWS_READY`
