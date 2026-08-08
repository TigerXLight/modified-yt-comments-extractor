# Source Adapter Evidence Release Acceptance Matrix Runtime

This implementation milestone adds `source_adapter_evidence_release_acceptance_matrix_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence-release acceptance matrix rows mapping named-site captures to evidence database imports, Total Export appendices, release packages, and published receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME_ROWS_READY`
