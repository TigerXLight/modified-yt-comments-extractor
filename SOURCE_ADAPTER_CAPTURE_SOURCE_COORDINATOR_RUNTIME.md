# Source Adapter Capture Source Coordinator Runtime

This implementation milestone adds `source_adapter_capture_source_coordinator_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers coordinated capture source rows that bind named sites, capture recipes, provider capabilities, operator approvals, and receipt imports into one run surface.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_CAPTURE_SOURCE_COORDINATOR_RUNTIME_BUILT`
- `SOURCE_ADAPTER_CAPTURE_SOURCE_COORDINATOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_CAPTURE_SOURCE_COORDINATOR_RUNTIME_ROWS_READY`
