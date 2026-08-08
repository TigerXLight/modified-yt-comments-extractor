# Source Adapter Release Package Integrity Runtime

This implementation milestone adds release package integrity rows validating files, manifests, receipts, and hashes.

It keeps the runtime implementation chain executable through deterministic Python APIs, CLI output, store artifacts, verifier checks, and docs tests. It preserves the `KEYS/ACCOUNTS` label, stores redacted credential references rather than secret material, and keeps live/provider execution represented as operator-approved runtime records with receipts.

Core status strings:

- `SOURCE_ADAPTER_RELEASE_PACKAGE_INTEGRITY_RUNTIME_BUILT`
- `SOURCE_ADAPTER_RELEASE_PACKAGE_INTEGRITY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE`
- `SOURCE_ADAPTER_RELEASE_PACKAGE_INTEGRITY_READY`
