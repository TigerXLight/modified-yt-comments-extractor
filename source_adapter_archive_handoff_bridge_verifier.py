from __future__ import annotations

from typing import Any, Mapping

from source_archive_handoff_verifier import verify_source_archive_handoff

SCHEMA_VERSION = "source_adapter_archive_handoff_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_archive_handoff_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_archive_handoff_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_archive_handoff_bridge_v1")
    if pkg.get("archive_handoff_bridge_status") != "SHARED_ARCHIVE_HANDOFFS_BUILT":
        _issue(issues, "archive_handoff_bridge_status must be SHARED_ARCHIVE_HANDOFFS_BUILT")
    if not pkg.get("source_adapter_archive_handoff_bridge_id"):
        _issue(issues, "source_adapter_archive_handoff_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified archive handoff bridge output")

    outputs = pkg.get("archive_handoff_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "archive_handoff_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"archive_handoff_outputs[{index}] must be an object")
                continue
            archive_package = output.get("archive_handoff_package")
            provider_tasks = output.get("provider_tasks")
            result_templates = output.get("result_templates")
            result_intake = output.get("result_intake_handoff")
            if not isinstance(archive_package, Mapping):
                _issue(issues, f"archive_handoff_outputs[{index}] missing archive_handoff_package")
                continue
            archive_handoff_id = str(archive_package.get("archive_handoff_id") or "")
            if archive_handoff_id in seen:
                _issue(issues, f"duplicate archive_handoff_id: {archive_handoff_id}")
            seen.add(archive_handoff_id)
            verification = verify_source_archive_handoff(
                archive_package,
                provider_tasks if isinstance(provider_tasks, Mapping) else None,
                result_templates if isinstance(result_templates, Mapping) else None,
                result_intake if isinstance(result_intake, Mapping) else None,
            )
            if not verification.get("verified"):
                _issue(issues, f"archive_handoff_outputs[{index}] failed shared verification: {verification.get('issues')}")

    batch = pkg.get("source_adapter_archive_handoff_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_archive_handoff_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_archive_handoff_batch_v1":
            _issue(issues, "source_adapter_archive_handoff_batch schema_version mismatch")
        if batch.get("archive_handoff_count") != len(outputs or []):
            _issue(issues, "source_adapter_archive_handoff_batch archive_handoff_count mismatch")
        if not isinstance(batch.get("archive_handoff_rows"), list) or not batch.get("archive_handoff_rows"):
            _issue(issues, "source_adapter_archive_handoff_batch must include archive_handoff_rows")

    handoff = pkg.get("source_adapter_archive_result_intake_batch_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_archive_result_intake_batch_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_archive_result_intake_batch_handoff_v1":
            _issue(issues, "source_adapter_archive_result_intake_batch_handoff schema_version mismatch")
        if handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE":
            _issue(issues, "archive result intake batch must be READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE")
        if handoff.get("ready_for_archive_result_intake") is not True:
            _issue(issues, "archive result intake batch must be ready_for_archive_result_intake")
        if handoff.get("required_next_stage") != "source_archive_result_intake":
            _issue(issues, "archive result intake batch required_next_stage must be source_archive_result_intake")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_archive_handoff_bridge_id": str(pkg.get("source_adapter_archive_handoff_bridge_id") or ""),
        "source_adapter_release_audit_bridge_id": str(pkg.get("source_adapter_release_audit_bridge_id") or ""),
        "archive_handoff_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
