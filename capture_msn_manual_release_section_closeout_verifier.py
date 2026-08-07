from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_VERIFIER_SCHEMA_VERSION = "msn_manual_release_section_closeout_verifier_v1"


@dataclass(frozen=True)
class MSNManualReleaseSectionCloseoutVerifierReport:
    schema_version: str
    verifier_status: str
    closeout_id: str
    issue_count: int
    issues: list[str] = field(default_factory=list)


def _read_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def verify_msn_manual_release_section_closeout(closeout_report: Mapping[str, Any], store_report: Mapping[str, Any] | None = None) -> MSNManualReleaseSectionCloseoutVerifierReport:
    issues: list[str] = []
    if closeout_report.get("schema_version") != "msn_manual_release_section_closeout_v1":
        issues.append("closeout schema_version mismatch")
    if closeout_report.get("closeout_status") != "MSN_MANUAL_RELEASE_SECTION_CLOSED":
        issues.append("closeout status is not MSN_MANUAL_RELEASE_SECTION_CLOSED")
    if closeout_report.get("ready_for_section_closeout") is not True:
        issues.append("closeout is not ready_for_section_closeout")
    if closeout_report.get("ready_for_total_export_release_record") is not True:
        issues.append("closeout is not ready_for_total_export_release_record")
    if _read_int(closeout_report.get("issue_count", 0)) != 0:
        issues.append("closeout issue_count is non-zero")
    checklist = closeout_report.get("final_release_checklist")
    if not isinstance(checklist, Mapping) or not checklist or not all(value is True for value in checklist.values()):
        issues.append("final release checklist is not fully true")
    release_record = closeout_report.get("total_export_release_record")
    if not isinstance(release_record, Mapping) or release_record.get("release_record_status") != "TOTAL_EXPORT_RELEASE_RECORD_READY":
        issues.append("Total Export release record is not ready")
    queue_update = closeout_report.get("evidence_queue_closeout_update")
    if not isinstance(queue_update, Mapping) or queue_update.get("queue_status") != "TOTAL_EXPORT_RELEASE_CLOSED":
        issues.append("evidence queue closeout update is not TOTAL_EXPORT_RELEASE_CLOSED")
    flags = closeout_report.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for flag in (
            "metadata_only_release_closeout",
            "explicit_release_export_bundle_json_only",
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
        if store_report.get("closeout_id") != closeout_report.get("closeout_id"):
            issues.append("store closeout_id does not match closeout")
        if _read_int(store_report.get("output_file_count", 0)) < 4:
            issues.append("store report missing expected output files")
    status = "MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_VERIFIED" if not issues else "MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_NEEDS_REVIEW"
    return MSNManualReleaseSectionCloseoutVerifierReport(
        schema_version=MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_VERIFIER_SCHEMA_VERSION,
        verifier_status=status,
        closeout_id=str(closeout_report.get("closeout_id", "")),
        issue_count=len(issues),
        issues=issues,
    )


def msn_manual_release_section_closeout_verifier_report_to_json(report: MSNManualReleaseSectionCloseoutVerifierReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "verifier_status": report.verifier_status,
        "closeout_id": report.closeout_id,
        "issue_count": report.issue_count,
        "issues": list(report.issues),
    }
