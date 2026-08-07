from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_capture_bundle_verifier_v1"
_SAFE_FILENAME_RE = re.compile(r"^[^\\/]+$")


def verify_source_capture_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(bundle, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": ["bundle must be a JSON object"],
            "capture_bundle_id": "",
            "adapter_id": "",
        }

    capture_bundle_id = str(bundle.get("capture_bundle_id") or "")
    adapter_id = str(bundle.get("adapter_id") or "")
    if bundle.get("schema_version") != "source_capture_bundle_v1":
        issues.append("schema_version must be source_capture_bundle_v1")
    if not capture_bundle_id:
        issues.append("capture_bundle_id is required")
    if not adapter_id:
        issues.append("adapter_id is required")

    content = bundle.get("content")
    if not isinstance(content, Mapping):
        issues.append("content object is required")
    else:
        if not str(content.get("title") or "").strip() and not str(content.get("body_text") or "").strip():
            issues.append("content must include title or body_text")
        if int(content.get("body_char_count") or 0) < 0:
            issues.append("content.body_char_count must not be negative")

    manifest = bundle.get("capture_manifest")
    if not isinstance(manifest, Mapping):
        issues.append("capture_manifest object is required")
    else:
        if manifest.get("capture_bundle_id") != capture_bundle_id:
            issues.append("capture_manifest.capture_bundle_id mismatch")
        if manifest.get("schema_version") != "source_capture_manifest_v1":
            issues.append("capture_manifest schema mismatch")

    handoff = bundle.get("total_export_handoff")
    if not isinstance(handoff, Mapping):
        issues.append("total_export_handoff object is required")
    else:
        if handoff.get("capture_bundle_id") != capture_bundle_id:
            issues.append("total_export_handoff.capture_bundle_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_TOTAL_EXPORT_PACKAGE":
            issues.append("total_export_handoff must be READY_FOR_TOTAL_EXPORT_PACKAGE")

    artifact_index = bundle.get("artifact_index")
    if not isinstance(artifact_index, list):
        issues.append("artifact_index must be a list")
    else:
        seen: set[tuple[str, str]] = set()
        for idx, item in enumerate(artifact_index):
            if not isinstance(item, Mapping):
                issues.append(f"artifact_index[{idx}] must be an object")
                continue
            filename = str(item.get("filename") or "")
            role = str(item.get("role") or "")
            if not filename or not _SAFE_FILENAME_RE.match(filename) or filename in {".", ".."}:
                issues.append(f"artifact_index[{idx}].filename must be a safe basename")
            if ".." in filename.split("."):
                issues.append(f"artifact_index[{idx}].filename must not contain traversal")
            if not role:
                issues.append(f"artifact_index[{idx}].role is required")
            key = (filename, role)
            if key in seen:
                issues.append(f"artifact_index[{idx}] duplicates filename/role")
            seen.add(key)

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter_id,
        "source_url": str(bundle.get("source_url") or ""),
    }
