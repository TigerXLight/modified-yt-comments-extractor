# Shared Source Adapter Runtime Wiring Bridge

`source_adapter_runtime_wiring_bridge.py` turns the completed Adapter Pipeline Closeout Bridge output into reusable runtime action wiring for source adapters.

The bridge models the real capability surface that later UI/CLI/provider integrations can execute with explicit operator approval: URL fetch/load, browser launch, folder scan, credential lookup, archive submission, release upload, app/registry mutation, and file-library publication. It emits deterministic action records, dry-run or injected-executor receipts, runtime execution handoff metadata, CLI/store/verifier support, and fixture-backed tests so new source adapters can share one implementation path instead of cloning the MSN workflow.
