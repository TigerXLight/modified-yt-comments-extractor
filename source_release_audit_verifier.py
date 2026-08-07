from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_release_audit_verifier_v1"
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")


def _is_safe_filename(value: object) -> bool:
    text = str(value or "")
    return bool(text) and bool(_SAFE_NAME_RE.match(text))


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_release_audit(
    release_audit_report: Mapping[str, Any],
    traceability_map: Mapping[str, Any] | None = None,
    archive_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    report = dict(release_audit_report or {})
    traceability = dict(traceability_map or {})
    handoff = dict(archive_handoff or {})

    if report.get("schema_version") != "source_release_audit_v1":
        _issue(issues, "release audit report schema_version must be source_release_audit_v1")
    if report.get("audit_status") != "READY_FOR_ARCHIVE_HANDOFF":
        _issue(issues, "release audit report must be READY_FOR_ARCHIVE_HANDOFF")
    if not report.get("release_audit_id"):
        _issue(issues, "release audit report must include release_audit_id")
    if not report.get("release_index_id"):
        _issue(issues, "release audit report must include release_index_id")
    if not report.get("approved_release_id"):
        _issue(issues, "release audit report must include approved_release_id")
    if not report.get("queue_item_id"):
        _issue(issues, "release audit report must include queue_item_id")
    if not report.get("total_export_package_id"):
        _issue(issues, "release audit report must include total_export_package_id")
    if not report.get("adapter_id"):
        _issue(issues, "release audit report must include adapter_id")
    if not report.get("source_url"):
        _issue(issues, "release audit report must include source_url")
    if not report.get("audit_fingerprint"):
        _issue(issues, "release audit report must include audit_fingerprint")

    checks = report.get("audit_checks")
    if not isinstance(checks, list) or len(checks) < 3:
        _issue(issues, "release audit report must include audit checks")
    else:
        for index, check in enumerate(checks):
            if not isinstance(check, Mapping):
                _issue(issues, f"audit_checks[{index}] must be an object")
                continue
            if check.get("status") != "PASS":
                _issue(issues, f"audit_checks[{index}] must have PASS status")

    artifacts = report.get("artifact_index")
    if not isinstance(artifacts, list) or not artifacts:
        _issue(issues, "release audit report must include non-empty artifact_index")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, Mapping):
                _issue(issues, f"artifact_index[{index}] must be an object")
                continue
            if not _is_safe_filename(artifact.get("filename")):
                _issue(issues, f"artifact_index[{index}].filename must be a safe basename")
            if "path" in artifact or "absolute_path" in artifact:
                _issue(issues, f"artifact_index[{index}] must not include path or absolute_path")

    if traceability:
        if traceability.get("schema_version") != "source_release_traceability_map_v1":
            _issue(issues, "traceability map schema_version must be source_release_traceability_map_v1")
        if traceability.get("release_audit_id") != report.get("release_audit_id"):
            _issue(issues, "traceability map release_audit_id mismatch")
        if traceability.get("traceability_status") != "READY_FOR_ARCHIVE_HANDOFF":
            _issue(issues, "traceability map must be READY_FOR_ARCHIVE_HANDOFF")
        if not isinstance(traceability.get("traceability_nodes"), list) or not traceability.get("traceability_nodes"):
            _issue(issues, "traceability map must include nodes")
        if not isinstance(traceability.get("traceability_edges"), list) or not traceability.get("traceability_edges"):
            _issue(issues, "traceability map must include edges")

    if handoff:
        if handoff.get("schema_version") != "source_release_archive_handoff_v1":
            _issue(issues, "archive handoff schema_version mismatch")
        if handoff.get("release_audit_id") != report.get("release_audit_id"):
            _issue(issues, "archive handoff release_audit_id mismatch")
        if handoff.get("release_index_id") != report.get("release_index_id"):
            _issue(issues, "archive handoff release_index_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_ARCHIVE_HANDOFF":
            _issue(issues, "archive handoff must be READY_FOR_ARCHIVE_HANDOFF")
        if handoff.get("required_next_stage") != "source_archive_handoff":
            _issue(issues, "archive handoff required_next_stage must be source_archive_handoff")
        if handoff.get("archive_submission_started") is True:
            _issue(issues, "release audit must not start archive submission")

    if report.get("manual_or_live_actions_started") is True:
        _issue(issues, "release audit stage must not mark manual_or_live_actions_started true")
    if report.get("live_network_default") is True:
        _issue(issues, "release audit stage must not enable live_network_default")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "release_audit_id": str(report.get("release_audit_id") or ""),
        "release_index_id": str(report.get("release_index_id") or ""),
        "approved_release_id": str(report.get("approved_release_id") or ""),
        "queue_item_id": str(report.get("queue_item_id") or ""),
        "adapter_id": str(report.get("adapter_id") or ""),
        "source_url": str(report.get("source_url") or ""),
    }
