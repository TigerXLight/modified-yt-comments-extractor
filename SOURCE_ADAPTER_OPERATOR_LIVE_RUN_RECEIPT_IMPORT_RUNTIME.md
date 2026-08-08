# Source Adapter Operator Live Run Receipt Import Runtime

This implementation milestone adds `source_adapter_operator_live_run_receipt_import_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator live-run receipt import rows for local/browser/archive/release/file-library receipts, failure receipts, and downstream review gates.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_OPERATOR_LIVE_RUN_RECEIPT_IMPORT_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_OPERATOR_LIVE_RUN_RECEIPT_IMPORT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_OPERATOR_LIVE_RUN_RECEIPT_IMPORT_RUNTIME_ROWS_READY`
