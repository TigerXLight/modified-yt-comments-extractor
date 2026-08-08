# Source Adapter Source To Evidence Commit Bridge Runtime

This implementation milestone adds `source_adapter_source_to_evidence_commit_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source-to-evidence commit bridge rows for evidence database import gates, queue dispatch, rollback-safe writes, and audit receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_SOURCE_TO_EVIDENCE_COMMIT_BRIDGE_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_SOURCE_TO_EVIDENCE_COMMIT_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_SOURCE_TO_EVIDENCE_COMMIT_BRIDGE_RUNTIME_ROWS_READY`
