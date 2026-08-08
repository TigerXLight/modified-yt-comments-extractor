# Source Adapter Live Site Selection Runtime

This implementation milestone adds `source_adapter_live_site_selection_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers live site selection rows for named-site scope, site class, capture intent, provider availability, and operator approval state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_LIVE_SITE_SELECTION_RUNTIME_BUILT`
- `SOURCE_ADAPTER_LIVE_SITE_SELECTION_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_LIVE_SITE_SELECTION_RUNTIME_ROWS_READY`
