# Source Adapter Source Observation Claim Mapper Runtime

This implementation milestone adds `source_adapter_source_observation_claim_mapper_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers source observation claim mapper rows for screenshots, manual observations, article/comment/media observations, claim IDs, review decisions, and evidence item links.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME_ROWS_READY`
