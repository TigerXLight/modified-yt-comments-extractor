# Shared source Adapter Evidence Queue Bridge

This section turns Adapter Total Export Bridge batches into shared Evidence Queue items.

It consumes `source_adapter_total_export_bridge_v1`, executes `source_evidence_queue` for each Total Export package, writes batch/index/handoff/operator artifacts, and forwards ready items to shared evidence review.

Implementation scope: full shared-section wiring with deterministic IDs, CLI/store/verifier/docs/tests, approval-friendly operator metadata, and reusable multi-adapter batch behavior.
