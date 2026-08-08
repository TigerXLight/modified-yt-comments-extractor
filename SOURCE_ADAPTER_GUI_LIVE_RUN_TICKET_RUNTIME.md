# Source Adapter GUI Live Run Ticket Runtime

This implementation milestone adds `source_adapter_gui_live_run_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI live run ticket rows for live capture wizards, status panels, command bars, approval state, receipt review, and no-secret display.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_GUI_LIVE_RUN_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_GUI_LIVE_RUN_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_GUI_LIVE_RUN_TICKET_RUNTIME_ROWS_READY`
