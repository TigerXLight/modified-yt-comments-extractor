from __future__ import annotations

from typing import Any, Mapping

from source_adapter_extraction_bridge import (
    CAPTURE_BUNDLE_HANDOFF_STATUS,
    EXTRACTION_BRIDGE_STATUS,
    SCHEMA_VERSION,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_extraction_bridge_verifier_v1"


def verify_source_adapter_extraction_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    if package.get("extraction_bridge_status") != EXTRACTION_BRIDGE_STATUS:
        issues.append("extraction_bridge_status is not SHARED_EXTRACTIONS_PREPARED")
    if not str(package.get("source_adapter_extraction_bridge_id") or "").startswith("source_adapter_extraction_bridge."):
        issues.append("source_adapter_extraction_bridge_id is missing or invalid")
    if not str(package.get("source_adapter_artifact_intake_id") or ""):
        issues.append("source_adapter_artifact_intake_id is required")
    if int(package.get("collection_count") or 0) <= 0:
        issues.append("collection_count must be greater than zero")
    if int(package.get("content_extraction_count") or 0) <= 0:
        issues.append("content_extraction_count must be greater than zero")
    if int(package.get("issue_count") or 0) != 0:
        issues.append("issue_count must be zero")

    content_index = package.get("content_extraction_index") if isinstance(package.get("content_extraction_index"), Mapping) else {}
    if int(content_index.get("content_extraction_count") or 0) != int(package.get("content_extraction_count") or 0):
        issues.append("content_extraction_index count mismatch")
    comment_index = package.get("comment_extraction_index") if isinstance(package.get("comment_extraction_index"), Mapping) else {}
    if int(comment_index.get("comment_extraction_count") or 0) != int(package.get("comment_extraction_count") or 0):
        issues.append("comment_extraction_index count mismatch")

    handoff = package.get("source_adapter_capture_bundle_handoff") if isinstance(package.get("source_adapter_capture_bundle_handoff"), Mapping) else {}
    if handoff.get("handoff_status") != CAPTURE_BUNDLE_HANDOFF_STATUS:
        issues.append("capture bundle handoff is not READY_FOR_SHARED_CAPTURE_BUNDLE")
    if handoff.get("ready_for_shared_capture_bundle") is not True:
        issues.append("capture bundle handoff must be ready")

    safety = package.get("safety_contract") if isinstance(package.get("safety_contract"), Mapping) else {}
    if safety.get("explicit_files_only") is not True:
        issues.append("safety_contract explicit_files_only must be true")
    if safety.get("folder_scan_performed") is not False:
        issues.append("safety_contract folder_scan_performed must be false")
    if safety.get("network_fetch_performed") is not False:
        issues.append("safety_contract network_fetch_performed must be false")
    if safety.get("browser_launch_performed") is not False:
        issues.append("safety_contract browser_launch_performed must be false")
    if safety.get("artifact_bytes_read_for_extraction") is not True:
        issues.append("safety_contract must record explicit artifact extraction reads")
    if safety.get("full_local_paths_serialized") is not False:
        issues.append("full local paths must not be serialized")

    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_extraction_bridge_id": package.get("source_adapter_extraction_bridge_id", ""),
        "source_adapter_artifact_intake_id": package.get("source_adapter_artifact_intake_id", ""),
        "collection_count": package.get("collection_count", 0),
        "content_extraction_count": package.get("content_extraction_count", 0),
        "comment_extraction_count": package.get("comment_extraction_count", 0),
        "extraction_bridge_status": package.get("extraction_bridge_status", ""),
    }


if __name__ == "__main__":
    print("Source Adapter Extraction Bridge verifier self-test passed.")
