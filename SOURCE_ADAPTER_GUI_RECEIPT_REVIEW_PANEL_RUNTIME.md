# Source Adapter GUI Receipt Review Panel Runtime

This implementation milestone adds `source_adapter_gui_receipt_review_panel_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI receipt review panel rows for imported archive/capture/release receipts, operator decisions, and evidence writeback status.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_RECEIPT_REVIEW_PANEL_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_RECEIPT_REVIEW_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_RECEIPT_REVIEW_PANEL_RUNTIME_ROWS_READY`
