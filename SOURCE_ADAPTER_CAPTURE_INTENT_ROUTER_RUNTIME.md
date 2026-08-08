# Source Adapter Capture Intent Router Runtime

This implementation milestone adds `source_adapter_capture_intent_router_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers capture intent routing rows for article, comment, media, archive, release, and mixed source workflows.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_CAPTURE_INTENT_ROUTER_RUNTIME_ROWS_READY`
