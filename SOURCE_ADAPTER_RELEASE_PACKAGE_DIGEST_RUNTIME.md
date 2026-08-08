# Source Adapter Release Package Digest Runtime

This implementation milestone adds `source_adapter_release_package_digest_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers release package digest rows for built package files, manifests, checksums, acceptance receipts, and file-library publish targets.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_RELEASE_PACKAGE_DIGEST_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RELEASE_PACKAGE_DIGEST_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_RELEASE_PACKAGE_DIGEST_RUNTIME_ROWS_READY`
