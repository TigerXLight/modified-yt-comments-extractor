from __future__ import annotations

from typing import Any, Mapping

from source_adapter_artifact_intake import ARTIFACT_INTAKE_STATUS, COLLECTION_HANDOFF_STATUS, SCHEMA_VERSION

VERIFIER_SCHEMA_VERSION = "source_adapter_artifact_intake_verifier_v1"


def verify_source_adapter_artifact_intake(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    if package.get("artifact_intake_status") != ARTIFACT_INTAKE_STATUS:
        issues.append("artifact_intake_status is not ARTIFACT_FILES_VALIDATED")
    if not str(package.get("source_adapter_artifact_intake_id") or "").startswith("source_adapter_artifact_intake."):
        issues.append("source_adapter_artifact_intake_id is missing or invalid")
    if int(package.get("receipt_count") or 0) <= 0:
        issues.append("receipt_count must be greater than zero")
    if int(package.get("artifact_file_count") or 0) != int(package.get("receipt_count") or 0):
        issues.append("artifact_file_count must equal receipt_count")
    if int(package.get("collection_count") or 0) <= 0:
        issues.append("collection_count must be greater than zero")

    report = package.get("validation_report") if isinstance(package.get("validation_report"), Mapping) else {}
    if report.get("validation_status") != "PASSED":
        issues.append("validation_report must be PASSED")
    if int(report.get("issue_count") or 0) != 0:
        issues.append("validation_report issue_count must be zero")

    handoff = package.get("source_artifact_collection_handoff") if isinstance(package.get("source_artifact_collection_handoff"), Mapping) else {}
    if handoff.get("handoff_status") != COLLECTION_HANDOFF_STATUS:
        issues.append("handoff_status is not READY_FOR_SHARED_EXTRACTION")
    if handoff.get("uses_shared_source_artifact_collection") is not True:
        issues.append("handoff must use shared source artifact collection")

    collections = package.get("source_artifact_collections") if isinstance(package.get("source_artifact_collections"), list) else []
    if len(collections) != int(package.get("collection_count") or 0):
        issues.append("collection_count does not match source_artifact_collections")
    for collection in collections:
        if not isinstance(collection, Mapping):
            issues.append("collection entry must be a mapping")
            continue
        if collection.get("collection_status") != "READY_FOR_EXTRACTION":
            issues.append(f"collection is not READY_FOR_EXTRACTION: {collection.get('collection_id', '')}")
        safety = collection.get("safety") if isinstance(collection.get("safety"), Mapping) else {}
        if safety.get("explicit_files_only") is not True:
            issues.append("collection safety explicit_files_only must be true")
        if safety.get("folder_scan_performed") is not False:
            issues.append("collection must not perform folder scans")
        if safety.get("network_fetch_performed") is not False:
            issues.append("collection must not perform network fetches")

    safety = package.get("safety_contract") if isinstance(package.get("safety_contract"), Mapping) else {}
    if safety.get("explicit_files_only") is not True:
        issues.append("safety_contract explicit_files_only must be true")
    if safety.get("folder_scan_performed") is not False:
        issues.append("safety_contract folder_scan_performed must be false")
    if safety.get("network_fetch_performed") is not False:
        issues.append("safety_contract network_fetch_performed must be false")
    if safety.get("browser_launch_performed") is not False:
        issues.append("safety_contract browser_launch_performed must be false")
    if safety.get("artifact_bytes_read_for_hash_validation") is not True:
        issues.append("safety_contract must record explicit artifact byte validation")
    if safety.get("full_local_paths_serialized") is not False:
        issues.append("full local paths must not be serialized")

    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_artifact_intake_id": package.get("source_adapter_artifact_intake_id", ""),
        "source_adapter_capture_session_id": package.get("source_adapter_capture_session_id", ""),
        "receipt_count": package.get("receipt_count", 0),
        "artifact_file_count": package.get("artifact_file_count", 0),
        "collection_count": package.get("collection_count", 0),
        "artifact_intake_status": package.get("artifact_intake_status", ""),
    }


if __name__ == "__main__":
    print("Source Adapter Artifact Intake verifier self-test passed.")
