# Source Adapter Manual Live Smoke Closeout Runtime

This implementation milestone adds `source_adapter_manual_live_smoke_closeout_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers manual/live smoke closeout rows covering named-site receipts, review decisions, evidence sync, and release readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_CLOSEOUT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_CLOSEOUT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_CLOSEOUT_RUNTIME_ROWS_READY`
