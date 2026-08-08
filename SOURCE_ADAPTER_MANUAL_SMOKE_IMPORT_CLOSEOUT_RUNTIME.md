# Source Adapter Manual Smoke Import Closeout Runtime

This implementation milestone adds `source_adapter_manual_smoke_import_closeout_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers manual smoke import closeout rows for operator-supplied observations, archive receipts, evidence review, and release audit handoff.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME_ROWS_READY`
