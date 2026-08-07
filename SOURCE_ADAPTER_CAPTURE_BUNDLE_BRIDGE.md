# Source Adapter Capture Bundle Bridge

Builds shared `source_capture_bundle` outputs from Adapter Extraction Bridge packages.

This section bridges validated adapter extraction outputs into the shared Total Export package path. It consumes explicit extraction bridge JSON, builds capture bundles through the existing shared `source_capture_bundle` contract, writes bundle indexes and Total Export handoff metadata, and keeps the workflow adapter-neutral unless a source genuinely needs adapter-specific extraction logic.
