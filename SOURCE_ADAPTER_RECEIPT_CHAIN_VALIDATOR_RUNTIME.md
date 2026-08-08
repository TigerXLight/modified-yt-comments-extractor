# Source Adapter Receipt Chain Validator Runtime

This implementation milestone adds `source_adapter_receipt_chain_validator_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers receipt chain validator rows checking capture, archive, evidence, export, release, and file-library hashes across runtime stages.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_RECEIPT_CHAIN_VALIDATOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RECEIPT_CHAIN_VALIDATOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_RECEIPT_CHAIN_VALIDATOR_RUNTIME_ROWS_READY`
