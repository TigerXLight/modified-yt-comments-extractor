# Source Adapter Provider Failure Recovery Runtime

This implementation milestone adds failure recovery rows for operator retry, skip, requeue, and evidence review.

It keeps the runtime implementation chain executable through deterministic Python APIs, CLI output, store artifacts, verifier checks, and docs tests. It preserves the `KEYS/ACCOUNTS` label, stores redacted credential references rather than secret material, and keeps live/provider execution represented as operator-approved runtime records with receipts.

Core status strings:

- `SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE`
- `SOURCE_ADAPTER_PROVIDER_FAILURE_RECOVERY_READY`
