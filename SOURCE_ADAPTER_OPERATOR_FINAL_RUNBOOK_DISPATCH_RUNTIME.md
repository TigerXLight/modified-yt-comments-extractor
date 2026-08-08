# Source Adapter Operator Final Runbook Dispatch Runtime

This implementation milestone adds `source_adapter_operator_final_runbook_dispatch_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers final operator runbook dispatch ticket rows connecting capture launch, site selection, approval state, output folders, and receipt import steps.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_OPERATOR_FINAL_RUNBOOK_DISPATCH_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_OPERATOR_FINAL_RUNBOOK_DISPATCH_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_OPERATOR_FINAL_RUNBOOK_DISPATCH_RUNTIME_ROWS_READY`
