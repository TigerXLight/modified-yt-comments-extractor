# Source Adapter Comments Expansion Plan Runtime

This implementation milestone adds `source_adapter_comments_expansion_plan_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers comments expansion plan rows for load-more cycles, nested thread expansion, screenshot cadence, manual repair receipts, and extraction completeness checks.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_COMMENTS_EXPANSION_PLAN_RUNTIME_BUILT`
- `SOURCE_ADAPTER_COMMENTS_EXPANSION_PLAN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_COMMENTS_EXPANSION_PLAN_RUNTIME_ROWS_READY`
