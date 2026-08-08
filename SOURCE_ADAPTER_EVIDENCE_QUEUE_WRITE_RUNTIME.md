# Source Adapter Evidence Queue Write Runtime

This implementation milestone adds `source_adapter_evidence_queue_write_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers evidence queue write rows that materialize source artifacts into evidence item review work.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_EVIDENCE_QUEUE_WRITE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_EVIDENCE_QUEUE_WRITE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_EVIDENCE_QUEUE_WRITE_RUNTIME_ROWS_READY`
