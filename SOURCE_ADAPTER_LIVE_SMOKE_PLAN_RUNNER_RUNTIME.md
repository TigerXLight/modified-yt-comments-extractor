# Source Adapter Live Smoke Plan Runner Runtime

This implementation milestone adds `source_adapter_live_smoke_plan_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers live smoke plan runner rows for named sites, approved actions, expected receipt sets, dry-run planning, and manual smoke import readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_LIVE_SMOKE_PLAN_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_LIVE_SMOKE_PLAN_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_LIVE_SMOKE_PLAN_RUNNER_RUNTIME_ROWS_READY`
