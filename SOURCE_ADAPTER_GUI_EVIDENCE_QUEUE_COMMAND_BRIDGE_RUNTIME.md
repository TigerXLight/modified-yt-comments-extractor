# Source Adapter GUI Evidence Queue Command Bridge Runtime

This implementation milestone adds `source_adapter_gui_evidence_queue_command_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI evidence queue command bridge rows for reviewed source records, queue writes, claim/source links, database commit readiness, and rollback-safe status display.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_EVIDENCE_QUEUE_COMMAND_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_EVIDENCE_QUEUE_COMMAND_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_EVIDENCE_QUEUE_COMMAND_BRIDGE_RUNTIME_ROWS_READY`
