# Source Adapter GUI Live Capture Wizard State Runtime

This implementation milestone adds `source_adapter_gui_live_capture_wizard_state_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI live capture wizard state rows for source selection, profile selection, approval form state, receipt panels, and completion indicators.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_WIZARD_STATE_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_WIZARD_STATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_GUI_LIVE_CAPTURE_WIZARD_STATE_RUNTIME_ROWS_READY`
