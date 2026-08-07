# Shared Source Release Index

`source_release_index.py` is the adapter-neutral release-index stage for source capture workflows. It consumes an explicit `source_approved_release_v1` package, optional `source_approved_release_manifest_v1`, and optional `source_approved_release_index_handoff_v1` JSON, then writes a deterministic release index record, release inventory, export-bundle handoff, and operator summary.

Only packages with `release_status` set to `READY_FOR_RELEASE_INDEX` enter this stage. The index stage records a release as ready for the shared release export-bundle boundary (`READY_FOR_RELEASE_EXPORT_BUNDLE`) without mutating the approved release package or the original Evidence Queue / Evidence Review records.

The stage performs no URL fetching, browser launching, folder scanning, credential reading, archive submission, online validation, or release upload. Future source adapters should reuse this shared release-index contract and provide only adapter specs, explicit artifacts, and fixtures unless their index identity genuinely requires a new adapter-specific surface.
