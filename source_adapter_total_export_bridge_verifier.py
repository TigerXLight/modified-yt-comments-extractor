from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_total_export_bridge_verifier_v1"


def _issue(issues: list[str], condition: bool, message: str) -> None:
    if not condition:
        issues.append(message)


def verify_source_adapter_total_export_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(package, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": ["package must be a JSON object"],
            "source_adapter_total_export_bridge_id": "",
        }

    bridge_id = str(package.get("source_adapter_total_export_bridge_id") or "")
    _issue(issues, package.get("schema_version") == "source_adapter_total_export_bridge_v1", "schema_version mismatch")
    _issue(issues, bool(bridge_id), "source_adapter_total_export_bridge_id is required")
    _issue(issues, package.get("total_export_bridge_status") == "SHARED_TOTAL_EXPORT_PACKAGES_BUILT", "total_export_bridge_status must be SHARED_TOTAL_EXPORT_PACKAGES_BUILT")

    outputs = package.get("total_export_outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.append("total_export_outputs must be a non-empty list")
        outputs = []
    package_ids: list[str] = []
    for idx, output in enumerate(outputs):
        if not isinstance(output, Mapping):
            issues.append(f"total_export_outputs[{idx}] must be an object")
            continue
        total_package = output.get("total_export_package")
        manifest = output.get("total_export_manifest")
        handoff = output.get("evidence_queue_handoff")
        if not isinstance(total_package, Mapping):
            issues.append(f"total_export_outputs[{idx}].total_export_package is required")
            continue
        package_id = str(total_package.get("total_export_package_id") or "")
        package_ids.append(package_id)
        if total_package.get("schema_version") != "source_total_export_package_v1":
            issues.append(f"total_export_outputs[{idx}].total_export_package schema mismatch")
        if not package_id:
            issues.append(f"total_export_outputs[{idx}].total_export_package_id is required")
        if total_package.get("export_status") != "READY_FOR_EVIDENCE_QUEUE":
            issues.append(f"total_export_outputs[{idx}].export_status must be READY_FOR_EVIDENCE_QUEUE")
        if not isinstance(manifest, Mapping) or manifest.get("total_export_package_id") != package_id:
            issues.append(f"total_export_outputs[{idx}].total_export_manifest mismatch")
        if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_EVIDENCE_QUEUE":
            issues.append(f"total_export_outputs[{idx}].evidence_queue_handoff must be READY_FOR_EVIDENCE_QUEUE")

    index = package.get("source_adapter_total_export_package_index")
    if not isinstance(index, Mapping):
        issues.append("source_adapter_total_export_package_index is required")
    else:
        if index.get("schema_version") != "source_adapter_total_export_package_index_v1":
            issues.append("source_adapter_total_export_package_index schema mismatch")
        if int(index.get("total_export_package_count") or -1) != len(outputs):
            issues.append("source_adapter_total_export_package_index count mismatch")

    handoff = package.get("source_adapter_evidence_queue_handoff")
    if not isinstance(handoff, Mapping):
        issues.append("source_adapter_evidence_queue_handoff is required")
    else:
        if handoff.get("handoff_status") != "READY_FOR_SHARED_EVIDENCE_QUEUE":
            issues.append("source_adapter_evidence_queue_handoff status mismatch")
        listed = [str(item) for item in handoff.get("total_export_package_ids", [])] if isinstance(handoff.get("total_export_package_ids"), list) else []
        if listed != package_ids:
            issues.append("source_adapter_evidence_queue_handoff total_export_package_ids mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_total_export_bridge_id": bridge_id,
        "source_adapter_capture_bundle_bridge_id": str(package.get("source_adapter_capture_bundle_bridge_id") or ""),
        "total_export_package_count": len(outputs),
    }
