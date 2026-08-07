from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_total_export_package_verifier_v1"


def verify_source_total_export_package(total_export_package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    package = total_export_package if isinstance(total_export_package, Mapping) else {}
    package_id = str(package.get("total_export_package_id") or "")
    capture_bundle_id = str(package.get("capture_bundle_id") or "")

    if package.get("schema_version") != "source_total_export_package_v1":
        issues.append("schema_version must be source_total_export_package_v1")
    if not package_id:
        issues.append("total_export_package_id is required")
    if not capture_bundle_id:
        issues.append("capture_bundle_id is required")
    if not str(package.get("adapter_id") or ""):
        issues.append("adapter_id is required")
    if package.get("export_status") != "READY_FOR_EVIDENCE_QUEUE":
        issues.append("export_status must be READY_FOR_EVIDENCE_QUEUE")

    content = package.get("content")
    if not isinstance(content, Mapping):
        issues.append("content object is required")
    else:
        if not str(content.get("title") or "") and not str(content.get("body_text") or ""):
            issues.append("content must include title or body_text")

    comments = package.get("comments")
    if not isinstance(comments, Mapping):
        issues.append("comments object is required")
    else:
        count = comments.get("comment_count")
        if not isinstance(count, int) or count < 0:
            issues.append("comments.comment_count must be a non-negative integer")

    artifact_index = package.get("artifact_index")
    if not isinstance(artifact_index, list):
        issues.append("artifact_index must be a list")
    else:
        for index, artifact in enumerate(artifact_index):
            if not isinstance(artifact, Mapping):
                issues.append(f"artifact_index[{index}] must be an object")
                continue
            if not str(artifact.get("filename") or ""):
                issues.append(f"artifact_index[{index}].filename is required")
            if any(sep in str(artifact.get("filename") or "") for sep in ("/", "\\")):
                issues.append(f"artifact_index[{index}].filename must be a basename")

    manifest = package.get("total_export_manifest")
    if not isinstance(manifest, Mapping):
        issues.append("total_export_manifest object is required")
    else:
        if manifest.get("schema_version") != "source_total_export_manifest_v1":
            issues.append("total_export_manifest.schema_version mismatch")
        if manifest.get("total_export_package_id") != package_id:
            issues.append("total_export_manifest.total_export_package_id mismatch")
        if manifest.get("capture_bundle_id") != capture_bundle_id:
            issues.append("total_export_manifest.capture_bundle_id mismatch")

    handoff = package.get("evidence_queue_handoff")
    if not isinstance(handoff, Mapping):
        issues.append("evidence_queue_handoff object is required")
    else:
        if handoff.get("schema_version") != "source_total_export_evidence_queue_handoff_v1":
            issues.append("evidence_queue_handoff.schema_version mismatch")
        if handoff.get("total_export_package_id") != package_id:
            issues.append("evidence_queue_handoff.total_export_package_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_EVIDENCE_QUEUE":
            issues.append("evidence_queue_handoff must be READY_FOR_EVIDENCE_QUEUE")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
    }
