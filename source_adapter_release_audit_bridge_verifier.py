from __future__ import annotations

from typing import Any, Mapping

from source_release_audit_verifier import verify_source_release_audit

SCHEMA_VERSION = "source_adapter_release_audit_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_release_audit_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_release_audit_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_release_audit_bridge_v1")
    if pkg.get("release_audit_bridge_status") != "SHARED_RELEASE_AUDITS_BUILT":
        _issue(issues, "release_audit_bridge_status must be SHARED_RELEASE_AUDITS_BUILT")
    if not pkg.get("source_adapter_release_audit_bridge_id"):
        _issue(issues, "source_adapter_release_audit_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified release audit bridge output")

    outputs = pkg.get("release_audit_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "release_audit_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"release_audit_outputs[{index}] must be an object")
                continue
            report = output.get("release_audit_report")
            traceability = output.get("traceability_map")
            archive_handoff = output.get("archive_handoff")
            if not isinstance(report, Mapping):
                _issue(issues, f"release_audit_outputs[{index}] missing release_audit_report")
                continue
            release_audit_id = str(report.get("release_audit_id") or "")
            if release_audit_id in seen:
                _issue(issues, f"duplicate release_audit_id: {release_audit_id}")
            seen.add(release_audit_id)
            verification = verify_source_release_audit(
                report,
                traceability if isinstance(traceability, Mapping) else None,
                archive_handoff if isinstance(archive_handoff, Mapping) else None,
            )
            if not verification.get("verified"):
                _issue(issues, f"release_audit_outputs[{index}] failed shared verification: {verification.get('issues')}")

    batch = pkg.get("source_adapter_release_audit_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_release_audit_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_release_audit_batch_v1":
            _issue(issues, "source_adapter_release_audit_batch schema_version mismatch")
        if batch.get("release_audit_count") != len(outputs or []):
            _issue(issues, "source_adapter_release_audit_batch release_audit_count mismatch")
        if not isinstance(batch.get("release_audit_rows"), list) or not batch.get("release_audit_rows"):
            _issue(issues, "source_adapter_release_audit_batch must include release_audit_rows")

    handoff = pkg.get("source_adapter_archive_handoff_batch_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_archive_handoff_batch_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_archive_handoff_batch_handoff_v1":
            _issue(issues, "source_adapter_archive_handoff_batch_handoff schema_version mismatch")
        if handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_HANDOFF":
            _issue(issues, "archive handoff batch must be READY_FOR_SHARED_ARCHIVE_HANDOFF")
        if handoff.get("ready_for_archive_handoff") is not True:
            _issue(issues, "archive handoff batch must be ready_for_archive_handoff")
        if handoff.get("required_next_stage") != "source_archive_handoff":
            _issue(issues, "archive handoff batch required_next_stage must be source_archive_handoff")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_release_audit_bridge_id": str(pkg.get("source_adapter_release_audit_bridge_id") or ""),
        "source_adapter_release_index_bridge_id": str(pkg.get("source_adapter_release_index_bridge_id") or ""),
        "release_audit_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
