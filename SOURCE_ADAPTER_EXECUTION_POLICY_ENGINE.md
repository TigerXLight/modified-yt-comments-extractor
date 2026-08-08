# Source Adapter Execution Policy Engine

This implementation milestone adds runtime policy rules that decide provider execution, review, and signoff readiness.

It keeps the runtime implementation chain executable through deterministic Python APIs, CLI output, store artifacts, verifier checks, and docs tests. It preserves the `KEYS/ACCOUNTS` label, stores redacted credential references rather than secret material, and keeps live/provider execution represented as operator-approved runtime records with receipts.

Core status strings:

- `SOURCE_ADAPTER_EXECUTION_POLICY_ENGINE_BUILT`
- `SOURCE_ADAPTER_EXECUTION_POLICY_ENGINE_READY_FOR_NEXT_IMPLEMENTATION_STAGE`
- `SOURCE_ADAPTER_EXECUTION_POLICY_RULES_READY`
