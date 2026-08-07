from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_approved_release_verifier_v1"


def verify_source_approved_release(
    approved_release_package: Mapping[str, Any],
    approved_release_manifest: Mapping[str, Any] | None = None,
    release_index_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    package = approved_release_package if isinstance(approved_release_package, Mapping) else {}
    manifest = approved_release_manifest if isinstance(approved_release_manifest, Mapping) else {}
    handoff = release_index_handoff if isinstance(release_index_handoff, Mapping) else {}

    approved_release_id = str(package.get("approved_release_id") or "")
    review_package_id = str(package.get("evidence_review_package_id") or "")
    queue_item_id = str(package.get("queue_item_id") or "")

    if package.get("schema_version") != "source_approved_release_v1":
        issues.append("approved_release_package.schema_version must be source_approved_release_v1")
    if not approved_release_id:
        issues.append("approved_release_id is required")
    if not review_package_id:
        issues.append("evidence_review_package_id is required")
    if not queue_item_id:
        issues.append("queue_item_id is required")
    if not str(package.get("total_export_package_id") or ""):
        issues.append("total_export_package_id is required")
    if not str(package.get("capture_bundle_id") or ""):
        issues.append("capture_bundle_id is required")
    if not str(package.get("adapter_id") or ""):
        issues.append("adapter_id is required")
    if package.get("release_status") != "READY_FOR_RELEASE_INDEX":
        issues.append("release_status must be READY_FOR_RELEASE_INDEX")
    if package.get("approved_by_review_decision") is not True:
        issues.append("approved_by_review_decision must be true")

    artifact_index = package.get("artifact_index")
    if not isinstance(artifact_index, list) or not artifact_index:
        issues.append("artifact_index must be a non-empty list")
    elif int(package.get("artifact_count") or -1) != len(artifact_index):
        issues.append("artifact_count must match artifact_index length")
    else:
        for index, artifact in enumerate(artifact_index):
            if not isinstance(artifact, Mapping):
                issues.append(f"artifact_index[{index}] must be an object")
                continue
            filename = str(artifact.get("filename") or "")
            if any(sep in filename for sep in ("/", "\\")) or (len(filename) > 1 and filename[1] == ":"):
                issues.append(f"artifact_index[{index}].filename must be a basename")

    if manifest:
        if manifest.get("schema_version") != "source_approved_release_manifest_v1":
            issues.append("approved_release_manifest.schema_version must be source_approved_release_manifest_v1")
        if str(manifest.get("approved_release_id") or "") != approved_release_id:
            issues.append("approved_release_manifest.approved_release_id mismatch")
        if manifest.get("manifest_status") != "READY_FOR_RELEASE_INDEX":
            issues.append("approved_release_manifest.manifest_status must be READY_FOR_RELEASE_INDEX")
        if str(manifest.get("release_fingerprint") or "") != str(package.get("release_fingerprint") or ""):
            issues.append("approved_release_manifest.release_fingerprint mismatch")

    if handoff:
        if handoff.get("schema_version") != "source_approved_release_index_handoff_v1":
            issues.append("release_index_handoff.schema_version must be source_approved_release_index_handoff_v1")
        if str(handoff.get("approved_release_id") or "") != approved_release_id:
            issues.append("release_index_handoff.approved_release_id mismatch")
        if str(handoff.get("evidence_review_package_id") or "") != review_package_id:
            issues.append("release_index_handoff.evidence_review_package_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_RELEASE_INDEX":
            issues.append("release_index_handoff.handoff_status must be READY_FOR_RELEASE_INDEX")
        if handoff.get("required_next_stage") != "source_release_index":
            issues.append("release_index_handoff.required_next_stage must be source_release_index")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
    }
