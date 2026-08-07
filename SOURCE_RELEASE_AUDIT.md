# Shared Source Release Audit

`source_release_audit.py` is the adapter-neutral release-audit and traceability stage for source capture workflows. It consumes an explicit `source_release_index_v1` record plus optional `source_release_inventory_v1` and `source_release_export_bundle_handoff_v1` JSON, then writes a deterministic release audit report, traceability map, archive handoff, and operator summary.

Only release index records with `release_index_status` set to `READY_FOR_RELEASE_EXPORT_BUNDLE` enter this stage. The audit marks the package as `READY_FOR_ARCHIVE_HANDOFF` without mutating release-index, approved-release, Evidence Review, Evidence Queue, Total Export, capture bundle, extraction, or artifact collection records.

The stage performs no URL fetching, browser launching, folder scanning, credential reading, archive submission, online validation, or upload. Future source adapters should reuse this shared release-audit contract and provide only adapter specs, explicit artifacts, and fixtures unless their traceability surface genuinely requires adapter-specific code.
