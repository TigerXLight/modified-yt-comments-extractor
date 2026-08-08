# Source Adapter Provider Failure Ticket Runtime

This implementation milestone adds `source_adapter_provider_failure_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider failure ticket rows for failure casebooks, escalation levels, retry/fallback decisions, missing receipt diagnostics, and operator-visible remediation.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_PROVIDER_FAILURE_TICKET_RUNTIME_ROWS_READY`
