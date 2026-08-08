# Source Adapter Source Package Verifier Runtime

This implementation milestone adds `source_adapter_source_package_verifier_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source package verifier rows for required artifacts, digest checks, source claim links, and release lock readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_PACKAGE_VERIFIER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_PACKAGE_VERIFIER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_PACKAGE_VERIFIER_RUNTIME_ROWS_READY`
