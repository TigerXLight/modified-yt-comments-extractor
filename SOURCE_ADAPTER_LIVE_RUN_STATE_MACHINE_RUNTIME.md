# Source Adapter Live Run State Machine Runtime

This implementation milestone adds `source_adapter_live_run_state_machine_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers live run state machine rows for requested, approved, running, receipt-imported, reviewed, failed, retry, and closed states.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_LIVE_RUN_STATE_MACHINE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_LIVE_RUN_STATE_MACHINE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_LIVE_RUN_STATE_MACHINE_RUNTIME_ROWS_READY`
