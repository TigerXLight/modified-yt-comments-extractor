from __future__ import annotations

from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "source_comment_extraction_v1"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _filename_has_path_separator(value: str) -> bool:
    return "/" in value or "\\" in value


def verify_source_comment_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if extraction.get("schema_version") != EXPECTED_SCHEMA:
        issues.append("unexpected_schema_version")
    if not _safe_text(extraction.get("comment_extraction_id")):
        issues.append("missing_comment_extraction_id")
    if not _safe_text(extraction.get("adapter_id")):
        issues.append("missing_adapter_id")
    comments = extraction.get("comments")
    if not isinstance(comments, list):
        issues.append("comments_must_be_list")
        comments = []
    if extraction.get("comment_count") != len(comments):
        issues.append("comment_count_mismatch")
    if not _safe_text(extraction.get("comment_sha256")) or len(_safe_text(extraction.get("comment_sha256"))) != 64:
        issues.append("missing_comment_sha256")
    selected = extraction.get("selected_artifact")
    if not isinstance(selected, dict):
        issues.append("missing_selected_artifact")
    else:
        filename = _safe_text(selected.get("filename"))
        if not filename:
            issues.append("missing_selected_artifact_filename")
        if _filename_has_path_separator(filename):
            issues.append("selected_artifact_filename_contains_path")
    for item in comments:
        if not isinstance(item, dict):
            issues.append("comment_entry_not_object")
            continue
        if not _safe_text(item.get("comment_id")):
            issues.append("comment_missing_id")
        if not _safe_text(item.get("text")):
            issues.append("comment_missing_text")
    operator_summary = extraction.get("operator_summary")
    if not isinstance(operator_summary, dict):
        issues.append("missing_operator_summary")
    else:
        if operator_summary.get("live_network_used") is not False:
            issues.append("live_network_used_not_false")
        if operator_summary.get("folder_scan_used") is not False:
            issues.append("folder_scan_used_not_false")
        if operator_summary.get("full_local_paths_serialized") is not False:
            issues.append("full_local_paths_serialized_not_false")
    return {
        "schema_version": "source_comment_extraction_verifier_v1",
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "comment_extraction_id": extraction.get("comment_extraction_id"),
        "adapter_id": extraction.get("adapter_id"),
        "comment_count": extraction.get("comment_count", 0),
    }


def verify_source_comment_extraction_file(path: str | Path) -> dict[str, Any]:
    import json

    return verify_source_comment_extraction(json.loads(Path(path).read_text(encoding="utf-8")))
