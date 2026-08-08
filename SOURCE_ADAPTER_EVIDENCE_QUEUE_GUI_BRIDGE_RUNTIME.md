# Source Adapter Evidence Queue GUI Bridge Runtime

This implementation milestone adds `source_adapter_evidence_queue_gui_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence queue GUI bridge rows for visible queue state, review commands, imported receipts, and source-to-evidence transitions.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_QUEUE_GUI_BRIDGE_RUNTIME_ROWS_READY`
