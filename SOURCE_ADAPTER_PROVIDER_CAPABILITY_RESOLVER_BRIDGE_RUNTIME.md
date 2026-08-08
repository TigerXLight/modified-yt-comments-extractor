# Source Adapter Provider Capability Resolver Bridge Runtime

This implementation milestone adds `source_adapter_provider_capability_resolver_bridge_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider capability resolver bridge rows for requested action, configured provider, declared capability, unavailable fallback, and operator-visible reason codes.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_CAPABILITY_RESOLVER_BRIDGE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_CAPABILITY_RESOLVER_BRIDGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_CAPABILITY_RESOLVER_BRIDGE_RUNTIME_ROWS_READY`
