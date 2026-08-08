# Source Adapter Archive Manual Receipt Validator Runtime

This implementation milestone adds `source_adapter_archive_manual_receipt_validator_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers manual archive receipt validator rows for operator-supplied archive URLs, timestamps, provider status, imported evidence IDs, and receipt hashes.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_ARCHIVE_MANUAL_RECEIPT_VALIDATOR_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_ARCHIVE_MANUAL_RECEIPT_VALIDATOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_ARCHIVE_MANUAL_RECEIPT_VALIDATOR_RUNTIME_ROWS_READY`
