from __future__ import annotations

from typing import Any, Mapping

from capture_msn_manual_release_audit_report import (
    AUDIT_STATUS_READY,
    SCHEMA_VERSION,
    inspect_msn_manual_release_audit_report_safety,
)

VERIFY_SCHEMA_VERSION = "msn_manual_release_audit_report_verifier_v1"


def verify_msn_manual_release_audit_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if packet.get("schema_version") != SCHEMA_VERSION:
        issues.append("unexpected_schema_version")
    if not packet.get("audit_report_id"):
        issues.append("missing_audit_report_id")
    if packet.get("audit_status") != AUDIT_STATUS_READY:
        issues.append("audit_not_ready")
    if not packet.get("queue_item_id"):
        issues.append("missing_queue_item_id")
    if not packet.get("release_id"):
        issues.append("missing_release_id")
    if not packet.get("pipeline_closeout_id"):
        issues.append("missing_pipeline_closeout_id")
    if packet.get("readiness_issues"):
        issues.append("readiness_issues_present")
    if packet.get("missing_stages"):
        issues.append("missing_stage_coverage")

    artifact_quality = packet.get("artifact_quality") or {}
    if not artifact_quality.get("artifact_quality_passed"):
        issues.append("artifact_quality_failed")
    if int(artifact_quality.get("artifact_count", 0) or 0) <= 0:
        issues.append("missing_artifact_ledger")

    transition_map = packet.get("transition_map") or {}
    if transition_map.get("to_status") != "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL":
        issues.append("unexpected_transition_target")

    safety = inspect_msn_manual_release_audit_report_safety(packet)
    issues.extend(str(issue) for issue in safety.get("issues", []))

    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "verified": not issues,
        "audit_report_id": packet.get("audit_report_id"),
        "queue_item_id": packet.get("queue_item_id"),
        "release_id": packet.get("release_id"),
        "issue_count": len(issues),
        "issues": issues,
    }


if __name__ == "__main__":
    from capture_msn_manual_release_audit_report import build_msn_manual_release_audit_report, _REQUIRED_STAGE_KEYS

    packet = build_msn_manual_release_audit_report(
        {
            "schema_version": "msn_manual_release_pipeline_closeout_v1",
            "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
            "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
            "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
            "stored_files": [
                {"filename": "artifact.json", "role": "artifact", "sha256": "a" * 64, "byte_count": 100},
            ],
        }
    )
    assert verify_msn_manual_release_audit_report(packet)["verified"] is True
    print("MSN manual release audit report verifier self-test passed.")
