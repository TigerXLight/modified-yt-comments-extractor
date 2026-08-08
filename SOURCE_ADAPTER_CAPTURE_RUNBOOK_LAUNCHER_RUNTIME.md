# Source Adapter Capture Runbook Launcher Runtime

This implementation milestone adds `source_adapter_capture_runbook_launcher_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator-copyable runbook launch rows for named-site capture profiles, browser command queues, receipt output folders, and no-auto-live approval gates.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_CAPTURE_RUNBOOK_LAUNCHER_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_CAPTURE_RUNBOOK_LAUNCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_CAPTURE_RUNBOOK_LAUNCHER_RUNTIME_ROWS_READY`
