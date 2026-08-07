from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_capture_bundle_bridge_verifier_v1"


def _issue(issues: list[str], condition: bool, message: str) -> None:
    if not condition:
        issues.append(message)


def verify_source_adapter_capture_bundle_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(package, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": ["package must be a JSON object"],
            "source_adapter_capture_bundle_bridge_id": "",
        }

    bridge_id = str(package.get("source_adapter_capture_bundle_bridge_id") or "")
    _issue(issues, package.get("schema_version") == "source_adapter_capture_bundle_bridge_v1", "schema_version mismatch")
    _issue(issues, bool(bridge_id), "source_adapter_capture_bundle_bridge_id is required")
    _issue(issues, package.get("capture_bundle_bridge_status") == "SHARED_CAPTURE_BUNDLES_BUILT", "capture_bundle_bridge_status must be SHARED_CAPTURE_BUNDLES_BUILT")

    outputs = package.get("capture_bundle_outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.append("capture_bundle_outputs must be a non-empty list")
        outputs = []
    bundle_ids: list[str] = []
    for idx, output in enumerate(outputs):
        if not isinstance(output, Mapping):
            issues.append(f"capture_bundle_outputs[{idx}] must be an object")
            continue
        bundle = output.get("capture_bundle")
        manifest = output.get("capture_manifest")
        handoff = output.get("total_export_handoff")
        if not isinstance(bundle, Mapping):
            issues.append(f"capture_bundle_outputs[{idx}].capture_bundle is required")
            continue
        bundle_id = str(bundle.get("capture_bundle_id") or "")
        bundle_ids.append(bundle_id)
        if bundle.get("schema_version") != "source_capture_bundle_v1":
            issues.append(f"capture_bundle_outputs[{idx}].capture_bundle schema mismatch")
        if not bundle_id:
            issues.append(f"capture_bundle_outputs[{idx}].capture_bundle_id is required")
        if not isinstance(manifest, Mapping) or manifest.get("capture_bundle_id") != bundle_id:
            issues.append(f"capture_bundle_outputs[{idx}].capture_manifest mismatch")
        if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_TOTAL_EXPORT_PACKAGE":
            issues.append(f"capture_bundle_outputs[{idx}].total_export_handoff must be READY_FOR_TOTAL_EXPORT_PACKAGE")

    index = package.get("source_adapter_capture_bundle_index")
    if not isinstance(index, Mapping):
        issues.append("source_adapter_capture_bundle_index is required")
    else:
        if index.get("schema_version") != "source_adapter_capture_bundle_index_v1":
            issues.append("source_adapter_capture_bundle_index schema mismatch")
        if int(index.get("capture_bundle_count") or -1) != len(outputs):
            issues.append("source_adapter_capture_bundle_index count mismatch")

    total_handoff = package.get("source_adapter_total_export_handoff")
    if not isinstance(total_handoff, Mapping):
        issues.append("source_adapter_total_export_handoff is required")
    else:
        if total_handoff.get("handoff_status") != "READY_FOR_SHARED_TOTAL_EXPORT_PACKAGE":
            issues.append("source_adapter_total_export_handoff status mismatch")
        listed = [str(item) for item in total_handoff.get("capture_bundle_ids", [])] if isinstance(total_handoff.get("capture_bundle_ids"), list) else []
        if listed != bundle_ids:
            issues.append("source_adapter_total_export_handoff capture_bundle_ids mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_capture_bundle_bridge_id": bridge_id,
        "source_adapter_extraction_bridge_id": str(package.get("source_adapter_extraction_bridge_id") or ""),
        "capture_bundle_count": len(outputs),
    }
