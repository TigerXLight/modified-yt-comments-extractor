# Source Adapter Manual Observation Review Runtime

This implementation milestone adds `source_adapter_manual_observation_review_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers manual observation review rows for operator-supplied screenshots, notes, archive URLs, claim links, review status, and source package inclusion.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MANUAL_OBSERVATION_REVIEW_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MANUAL_OBSERVATION_REVIEW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MANUAL_OBSERVATION_REVIEW_RUNTIME_ROWS_READY`
