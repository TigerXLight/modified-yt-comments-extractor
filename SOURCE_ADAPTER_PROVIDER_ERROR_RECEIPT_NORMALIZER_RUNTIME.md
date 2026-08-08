# Source Adapter Provider Error Receipt Normalizer Runtime

This implementation milestone adds `source_adapter_provider_error_receipt_normalizer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider error receipt normalizer rows for failed live/archive/release actions, retry hints, redacted diagnostics, and evidence-safe failure receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_ERROR_RECEIPT_NORMALIZER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_ERROR_RECEIPT_NORMALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_ERROR_RECEIPT_NORMALIZER_RUNTIME_ROWS_READY`
