# Source Adapter Manual Observation Importer Runtime

This implementation milestone adds `source_adapter_manual_observation_importer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers manual observation importer rows for browser notes, screenshots, archive URLs, and evidence queue writeback.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MANUAL_OBSERVATION_IMPORTER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MANUAL_OBSERVATION_IMPORTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MANUAL_OBSERVATION_IMPORTER_RUNTIME_ROWS_READY`
