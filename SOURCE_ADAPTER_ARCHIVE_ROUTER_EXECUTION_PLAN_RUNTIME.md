# Source Adapter Archive Router Execution Plan Runtime

This implementation milestone adds `source_adapter_archive_router_execution_plan_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive router execution plan rows for archive.ph, Ghostarchive, Wayback, manual local preservation, and provider fallback routing.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_ARCHIVE_ROUTER_EXECUTION_PLAN_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_ARCHIVE_ROUTER_EXECUTION_PLAN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_ARCHIVE_ROUTER_EXECUTION_PLAN_RUNTIME_ROWS_READY`
