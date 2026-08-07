# Shared Source Evidence Review

`source_evidence_review.py` is the adapter-neutral Evidence Review stage for source capture workflows. It consumes an explicit `source_evidence_queue_v1` item and optional `source_evidence_review_handoff_v1` JSON, then writes a deterministic review package, checklist, decision record, approved-release handoff, and operator summary.

The stage supports `APPROVED`, `REJECTED`, and `REVISION_REQUESTED` decisions without mutating the original queue item. It performs no URL fetching, browser launching, folder scanning, credential reading, archive submission, or online validation.

Future source adapters should reuse this shared review contract and provide only adapter specs, explicit artifacts, and fixtures unless their review identity genuinely requires a new adapter-specific surface.
