# Source Adapter Provider Health Review Runtime

This implementation milestone adds `source_adapter_provider_health_review_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers provider health review rows from healthcheck, retry, failure recovery, and operator dashboard state.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME_ROWS_READY`
