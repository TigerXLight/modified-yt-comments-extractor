# Source Adapter Live Smoke Receipt Runtime

This implementation milestone adds `source_adapter_live_smoke_receipt_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers live smoke receipt rows linking readiness, permission, named site profile, provider action receipts, and review outcome.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_RUNTIME_ROWS_READY`
