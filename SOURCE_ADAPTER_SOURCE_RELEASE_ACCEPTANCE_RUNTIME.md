# Source Adapter Source Release Acceptance Runtime

This implementation milestone adds `source_adapter_source_release_acceptance_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source release acceptance rows for evidence/release parity, operator signoff, proof chains, manifest lock, and package readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_RELEASE_ACCEPTANCE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_RELEASE_ACCEPTANCE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_RELEASE_ACCEPTANCE_RUNTIME_ROWS_READY`
