from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_evidence_queue_verifier_v1"


def verify_source_evidence_queue(evidence_queue_item: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    item = evidence_queue_item if isinstance(evidence_queue_item, Mapping) else {}
    queue_item_id = str(item.get("queue_item_id") or "")
    package_id = str(item.get("total_export_package_id") or "")

    if item.get("schema_version") != "source_evidence_queue_v1":
        issues.append("schema_version must be source_evidence_queue_v1")
    if not queue_item_id:
        issues.append("queue_item_id is required")
    if not package_id:
        issues.append("total_export_package_id is required")
    if not str(item.get("capture_bundle_id") or ""):
        issues.append("capture_bundle_id is required")
    if not str(item.get("adapter_id") or ""):
        issues.append("adapter_id is required")
    if item.get("queue_status") != "READY_FOR_EVIDENCE_REVIEW":
        issues.append("queue_status must be READY_FOR_EVIDENCE_REVIEW")
    if item.get("review_state") != "PENDING_REVIEW":
        issues.append("review_state must be PENDING_REVIEW")

    content = item.get("content_summary")
    if not isinstance(content, Mapping):
        issues.append("content_summary object is required")
    else:
        if not str(content.get("title") or "") and not str(content.get("body_sha256") or "") and not int(content.get("body_char_count") or 0):
            issues.append("content_summary must include title, body_sha256, or body_char_count")

    comments = item.get("comment_summary")
    if not isinstance(comments, Mapping):
        issues.append("comment_summary object is required")
    else:
        count = comments.get("comment_count")
        if not isinstance(count, int) or count < 0:
            issues.append("comment_summary.comment_count must be a non-negative integer")

    artifact_index = item.get("artifact_index")
    if not isinstance(artifact_index, list):
        issues.append("artifact_index must be a list")
    else:
        for index, artifact in enumerate(artifact_index):
            if not isinstance(artifact, Mapping):
                issues.append(f"artifact_index[{index}] must be an object")
                continue
            filename = str(artifact.get("filename") or "")
            if not filename:
                issues.append(f"artifact_index[{index}].filename is required")
            if any(sep in filename for sep in ("/", "\\")) or (len(filename) > 1 and filename[1] == ":"):
                issues.append(f"artifact_index[{index}].filename must be a basename")

    actions = item.get("review_actions")
    if not isinstance(actions, list) or not actions:
        issues.append("review_actions must be a non-empty list")
    else:
        required_actions = [action for action in actions if isinstance(action, Mapping) and action.get("required")]
        if not required_actions:
            issues.append("at least one required review action is required")
        for index, action in enumerate(actions):
            if not isinstance(action, Mapping):
                issues.append(f"review_actions[{index}] must be an object")
                continue
            if not str(action.get("action_id") or ""):
                issues.append(f"review_actions[{index}].action_id is required")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "adapter_id": str(item.get("adapter_id") or ""),
        "source_url": str(item.get("source_url") or ""),
    }
