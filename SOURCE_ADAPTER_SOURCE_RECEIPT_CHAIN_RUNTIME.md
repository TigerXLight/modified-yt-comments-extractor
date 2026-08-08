# Source Adapter Source Receipt Chain Runtime

This implementation milestone adds `source_adapter_source_receipt_chain_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source receipt chain rows linking capture artifact, archive result, evidence item, export package, and release receipt hashes.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_RECEIPT_CHAIN_RUNTIME_ROWS_READY`
