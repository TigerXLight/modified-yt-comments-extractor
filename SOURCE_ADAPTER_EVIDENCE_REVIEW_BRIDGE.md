# Source Adapter Evidence Review Bridge

Shared bridge from Adapter Evidence Queue batches into the existing `source_evidence_review` implementation.

- Consumes `source_adapter_evidence_queue_bridge_v1` packages with `READY_FOR_SHARED_EVIDENCE_REVIEW` handoffs.
- Builds batch Evidence Review packages, checklists, decisions, release handoffs, approved-release batch handoff metadata, and operator summaries.
- Supports shared reviewer decisions plus per-queue-item decisions for multi-adapter batches.
- Carries pending, approved, rejected, and revision-requested review outcomes explicitly into the next stage.
- Keeps adapter work on the shared review contract unless a source requires a genuinely distinct review or release shape.
