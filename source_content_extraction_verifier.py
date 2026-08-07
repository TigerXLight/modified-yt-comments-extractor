from __future__ import annotations

from typing import Any
import re

VERIFIER_SCHEMA_VERSION = "source_content_extraction_verifier_v1"


def _contains_full_local_path(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_full_local_path(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_full_local_path(v) for v in value)
    if isinstance(value, str):
        text = value.replace("/", "\\")
        if len(text) >= 3 and text[0].isalpha() and text[1:3]== ":\\":
            return True
        if re.search(r"[\\s\"'=,{\[][A-Za-z]:\\\\", text):
            return True
        if text.startswith("\\\\"):
            return True
    return False


def verify_source_content_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if extraction.get("schema_version") != "source_content_extraction_v1":
        issues.append("unexpected_schema_version")
    if not extraction.get("content_id"):
        issues.append("missing_content_id")
    if not extraction.get("adapter_id"):
        issues.append("missing_adapter_id")
    if not extraction.get("title"):
        issues.append("missing_title")
    if not extraction.get("body_text"):
        issues.append("missing_body_text")
    if not extraction.get("body_sha256"):
        issues.append("missing_body_sha256")
    selected = extraction.get("selected_artifact")
    if not isinstance(selected, dict) or not selected.get("filename"):
        issues.append("missing_selected_artifact_filename")
    operator_summary = extraction.get("operator_summary")
    if not isinstance(operator_summary, dict):
        issues.append("missing_operator_summary")
    else:
        if operator_summary.get("live_network_used") is not False:
            issues.append("live_network_used_not_false")
        if operator_summary.get("folder_scan_used") is not False:
            issues.append("folder_scan_used_not_false")
        if operator_summary.get("full_local_paths_serialized") is not False:
            issues.append("full_local_paths_serialized_flag_not_false")
    if _contains_full_local_path(extraction):
        issues.append("full_local_path_serialized")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "content_id": extraction.get("content_id"),
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
    }
