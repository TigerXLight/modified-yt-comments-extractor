# Source Adapter Shadow Root Extraction Plan Runtime

This implementation milestone adds `source_adapter_shadow_root_extraction_plan_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers shadow-root extraction plan rows for web component hosts, inner selectors, overlay containers, flattened comment records, and evidence review handoff.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME_ROWS_READY`
