# Shared Source Adapter Runtime Receipt Review Bridge

`source_adapter_runtime_receipt_review_bridge.py` reviews the runtime action receipts emitted by the shared Adapter Runtime Wiring Bridge.

The bridge validates action-to-receipt coverage for URL fetch/load, browser launch, folder scan, credential lookup, archive submission, release upload, app/registry mutation, and file-library publication surfaces, then emits deterministic review rows, acceptance indexes, handoff metadata, CLI/store/verifier support, and fixture-backed tests. It keeps runtime acceptance reusable across source adapters while preserving explicit operator approval IDs and receipt records.
