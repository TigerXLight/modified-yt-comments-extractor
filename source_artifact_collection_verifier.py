from __future__ import annotations

from typing import Any, Mapping

REQUIRED_SCHEMA_VERSION = "source_artifact_collection_v1"
VERIFIER_SCHEMA_VERSION = "source_artifact_collection_verifier_v1"


def verify_source_artifact_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if collection.get("schema_version") != REQUIRED_SCHEMA_VERSION:
        issues.append("schema_version must be source_artifact_collection_v1")
    if not collection.get("collection_id"):
        issues.append("collection_id is required")
    if not collection.get("adapter_id"):
        issues.append("adapter_id is required")
    if not collection.get("source_url"):
        issues.append("source_url is required")
    artifacts = collection.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        issues.append("at least one artifact is required")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                issues.append(f"artifact {index} must be an object")
                continue
            for key in ("role", "filename", "byte_count", "sha256"):
                if not artifact.get(key):
                    issues.append(f"artifact {index} missing {key}")
            if artifact.get("source_path_recorded"):
                issues.append(f"artifact {index} records a source path")
            if "\\" in str(artifact.get("filename", "")) or "/" in str(artifact.get("filename", "")):
                issues.append(f"artifact {index} filename must be a basename")
            if artifact.get("byte_count", 0) <= 0:
                issues.append(f"artifact {index} byte_count must be positive")
            if len(str(artifact.get("sha256", ""))) != 64:
                issues.append(f"artifact {index} sha256 must be 64 hex characters")
    safety = collection.get("safety") or {}
    if not safety.get("explicit_files_only"):
        issues.append("explicit_files_only must be true")
    for key in ("folder_scan_performed", "network_fetch_performed", "browser_launch_performed", "full_local_paths_serialized", "credentials_read"):
        if safety.get(key):
            issues.append(f"{key} must be false")
    missing = collection.get("missing_required_roles") or []
    if missing and collection.get("collection_status") == "READY_FOR_EXTRACTION":
        issues.append("collection cannot be READY_FOR_EXTRACTION while required roles are missing")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "collection_id": collection.get("collection_id", ""),
        "adapter_id": collection.get("adapter_id", ""),
        "artifact_count": len(artifacts) if isinstance(artifacts, list) else 0,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


__all__ = ["verify_source_artifact_collection"]
