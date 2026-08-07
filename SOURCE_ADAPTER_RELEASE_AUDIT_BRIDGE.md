# Adapter Release Audit Bridge

`source_adapter_release_audit_bridge_v1` is the shared bridge from Adapter Release Index batches into the adapter-neutral `source_release_audit` stage.

The bridge consumes `source_adapter_release_index_bridge_v1`, calls `source_release_audit` for each release-index output, and emits release-audit output batches, release-audit row summaries, and `READY_FOR_SHARED_ARCHIVE_HANDOFF` metadata for `source_archive_handoff`.

It supports multi-adapter batches and keeps the implementation pattern as adapter metadata plus shared-stage execution, so new source adapters reuse the same audit bridge unless their audit surface genuinely needs separate mapping code.
