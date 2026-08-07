from __future__ import annotations

from typing import Any, Mapping

VERIFIER_SCHEMA_VERSION = "source_adapter_approved_release_bridge_verifier_v1"


def verify_source_adapter_approved_release_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != "source_adapter_approved_release_bridge_v1":
        issues.append("schema_version must be source_adapter_approved_release_bridge_v1")
    if package.get("approved_release_bridge_status") != "SHARED_APPROVED_RELEASES_BUILT":
        issues.append("approved_release_bridge_status must be SHARED_APPROVED_RELEASES_BUILT")
    outputs = package.get("approved_release_outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.append("approved_release_outputs must be a non-empty list")
    else:
        release_ids: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                issues.append(f"approved_release_outputs[{index}] must be a mapping")
                continue
            release_package = output.get("approved_release_package")
            manifest = output.get("approved_release_manifest")
            handoff = output.get("release_index_handoff")
            if not isinstance(release_package, Mapping):
                issues.append(f"approved_release_outputs[{index}].approved_release_package missing")
                continue
            release_id = str(release_package.get("approved_release_id") or "")
            if not release_id:
                issues.append(f"approved_release_outputs[{index}] missing approved_release_id")
            elif release_id in release_ids:
                issues.append(f"duplicate approved_release_id: {release_id}")
            release_ids.add(release_id)
            if release_package.get("schema_version") != "source_approved_release_v1":
                issues.append(f"approved_release_outputs[{index}].approved_release_package schema mismatch")
            if release_package.get("release_status") != "READY_FOR_RELEASE_INDEX":
                issues.append(f"approved_release_outputs[{index}].approved_release_package release_status mismatch")
            if not isinstance(manifest, Mapping) or manifest.get("schema_version") != "source_approved_release_manifest_v1":
                issues.append(f"approved_release_outputs[{index}].approved_release_manifest schema mismatch")
            if not isinstance(handoff, Mapping) or handoff.get("schema_version") != "source_approved_release_index_handoff_v1":
                issues.append(f"approved_release_outputs[{index}].release_index_handoff schema mismatch")
    batch = package.get("source_adapter_approved_release_batch")
    if not isinstance(batch, Mapping) or batch.get("schema_version") != "source_adapter_approved_release_batch_v1":
        issues.append("source_adapter_approved_release_batch schema mismatch")
    release_index_handoff = package.get("source_adapter_release_index_batch_handoff")
    if not isinstance(release_index_handoff, Mapping) or release_index_handoff.get("schema_version") != "source_adapter_release_index_batch_handoff_v1":
        issues.append("source_adapter_release_index_batch_handoff schema mismatch")
    if package.get("issue_count", 0) != 0:
        issues.append("package contains embedded issues")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_approved_release_bridge_id": package.get("source_adapter_approved_release_bridge_id", ""),
        "source_adapter_evidence_review_bridge_id": package.get("source_adapter_evidence_review_bridge_id", ""),
        "approved_release_count": package.get("approved_release_count", 0),
        "handoff_status": release_index_handoff.get("handoff_status", "") if isinstance(release_index_handoff, Mapping) else "",
    }
