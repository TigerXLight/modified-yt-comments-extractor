# Source Adapter Total Export Package Audit Runtime

This implementation milestone adds `source_adapter_total_export_package_audit_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export package audit rows for manifest completeness, archive appendix consistency, evidence claim coverage, file inventory, and release package verification.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_AUDIT_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_AUDIT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_AUDIT_RUNTIME_ROWS_READY`
