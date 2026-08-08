# Source Adapter Provider Execution Dispatcher Runtime

This implementation milestone adds `source_adapter_provider_execution_dispatcher_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider execution dispatcher rows for approved action routing, capability checks, local/dry-run commands, and live execution gates.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_EXECUTION_DISPATCHER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_EXECUTION_DISPATCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_EXECUTION_DISPATCHER_RUNTIME_ROWS_READY`
