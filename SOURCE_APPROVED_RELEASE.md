# Shared Source Approved Release

`source_approved_release.py` is the adapter-neutral approved-release stage for source capture workflows. It consumes an explicit `source_evidence_review_v1` package, `source_evidence_review_decision_v1` decision, and optional `source_evidence_review_release_handoff_v1` JSON, then writes a deterministic approved release package, release manifest, release-index handoff, and operator summary.

Only `APPROVED` Evidence Review decisions can enter this stage. `REJECTED`, `REVISION_REQUESTED`, and pending decisions remain in Evidence Review and do not create release-ready outputs.

The stage performs no URL fetching, browser launching, folder scanning, credential reading, archive submission, or online validation. Future source adapters should reuse this shared release contract and provide only adapter specs, explicit artifacts, and fixtures unless their release identity genuinely requires a new adapter-specific surface.
