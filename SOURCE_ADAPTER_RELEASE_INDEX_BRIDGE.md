# Shared Source Adapter Release Index Bridge

`source_adapter_release_index_bridge.py` is the adapter-neutral bridge from Adapter Approved Release Bridge batches into the shared `source_release_index` stage.

It consumes `source_adapter_approved_release_bridge_v1`, executes the shared release-index builder for each approved-release output, and emits release-index output batches, release-index row summaries, and a `READY_FOR_SHARED_RELEASE_AUDIT` handoff for `source_release_audit`.

The bridge keeps prior review and approved-release records immutable. Operator approval, browser, archive, upload, and provider behaviour remains routed through the upstream/downstream shared stages that own those actions.

The same bridge supports multi-adapter batches; future source adapters should provide adapter specs and explicit artifacts, then flow through this shared release-index bridge unless a source has a genuinely unique index-shape requirement.
