# Source Adapter Capture Comment Receipt Mapper Runtime

This implementation milestone adds `source_adapter_capture_comment_receipt_mapper_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers comment receipt mapper rows for comment tree exports, reply chains, operator observations, source positions, and evidence queue handoff.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_CAPTURE_COMMENT_RECEIPT_MAPPER_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_CAPTURE_COMMENT_RECEIPT_MAPPER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_CAPTURE_COMMENT_RECEIPT_MAPPER_RUNTIME_ROWS_READY`
