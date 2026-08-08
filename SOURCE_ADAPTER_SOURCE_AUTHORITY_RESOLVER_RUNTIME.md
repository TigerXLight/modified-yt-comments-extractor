# Source Adapter Source Authority Resolver Runtime

This implementation milestone adds `source_adapter_source_authority_resolver_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source authority resolution rows that bind source URL, citation strength, archive candidate, and evidence priority.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_AUTHORITY_RESOLVER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_AUTHORITY_RESOLVER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_AUTHORITY_RESOLVER_RUNTIME_ROWS_READY`
