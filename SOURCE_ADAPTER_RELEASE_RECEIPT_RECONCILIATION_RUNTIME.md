# Source Adapter Release Receipt Reconciliation Runtime

This implementation milestone adds `source_adapter_release_receipt_reconciliation_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers release receipt reconciliation rows for upload receipts, file-library receipts, acceptance receipts, missing receipt diagnostics, and closeout status.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_RELEASE_RECEIPT_RECONCILIATION_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_RELEASE_RECEIPT_RECONCILIATION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_RELEASE_RECEIPT_RECONCILIATION_RUNTIME_ROWS_READY`
