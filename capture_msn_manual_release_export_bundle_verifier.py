from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

MSN_MANUAL_RELEASE_EXPORT_BUNDLE_VERIFIER_SCHEMA_VERSION = "msn_manual_release_export_bundle_verifier_v1"


@dataclass(frozen=True)
class MSNManualReleaseExportBundleVerifierReport:
    schema_version: str
    verifier_status: str
    export_bundle_id: str
    issue_count: int
    issues: list[str] = field(default_factory=list)


def verify_msn_manual_release_export_bundle(bundle_report: Mapping[str, Any], store_report: Mapping[str, Any] | None = None) -> MSNManualReleaseExportBundleVerifierReport:
    issues: list[str] = []
    if bundle_report.get("schema_version") != "msn_manual_release_export_bundle_v1":
        issues.append("bundle schema_version mismatch")
    if bundle_report.get("export_bundle_status") != "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY":
        issues.append("bundle status is not ready")
    if bundle_report.get("ready_for_total_export_handoff") is not True:
        issues.append("bundle is not ready_for_total_export_handoff")
    if int(bundle_report.get("issue_count", 0) or 0) != 0:
        issues.append("bundle issue_count is non-zero")
    manifest = bundle_report.get("total_export_handoff_manifest")
    if not isinstance(manifest, Mapping) or manifest.get("handoff_status") != "TOTAL_EXPORT_HANDOFF_READY":
        issues.append("Total Export handoff manifest is not ready")
    queue_update = bundle_report.get("evidence_queue_final_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "TOTAL_EXPORT_HANDOFF_READY":
        issues.append("evidence queue final update is not ready")
    checksum = bundle_report.get("checksum_manifest")
    if not isinstance(checksum, Mapping) or checksum.get("checksum_status") != "CHECKSUMS_READY":
        issues.append("checksum manifest is not ready")
    flags = bundle_report.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for flag in (
            "metadata_only_export_bundle",
            "explicit_release_index_json_only",
            "no_live_http",
            "no_browser_automation",
            "no_archive_submission",
            "no_media_downloads",
            "no_credential_reads",
            "no_folder_scans",
            "no_file_moves",
            "no_full_local_paths",
        ):
            if flags.get(flag) is not True:
                issues.append(f"safety flag not true: {flag}")
    if isinstance(store_report, Mapping):
        if store_report.get("store_status") != "STORED":
            issues.append("store report is not STORED")
        if store_report.get("export_bundle_id") != bundle_report.get("export_bundle_id"):
            issues.append("store export_bundle_id does not match bundle")
        if int(store_report.get("output_file_count", 0) or 0) < 3:
            issues.append("store report missing expected output files")
    status = "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_VERIFIED" if not issues else "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_NEEDS_REVIEW"
    return MSNManualReleaseExportBundleVerifierReport(
        schema_version=MSN_MANUAL_RELEASE_EXPORT_BUNDLE_VERIFIER_SCHEMA_VERSION,
        verifier_status=status,
        export_bundle_id=str(bundle_report.get("export_bundle_id", "")),
        issue_count=len(issues),
        issues=issues,
    )


def msn_manual_release_export_bundle_verifier_report_to_json(report: MSNManualReleaseExportBundleVerifierReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "verifier_status": report.verifier_status,
        "export_bundle_id": report.export_bundle_id,
        "issue_count": report.issue_count,
        "issues": list(report.issues),
    }
