from __future__ import annotations

import json
import re
from typing import Any, Mapping

SCHEMA_VERSION = "msn_manual_archive_handoff_verifier_v1"
_SAFE_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
_URL_RE = re.compile(r"^https?://[^\s<>{}\"']+$", re.I)
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)


def _as_mapping(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _has_secret_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET_FIELD_RE.search(str(key)) or _has_secret_field(item):
                return True
    elif isinstance(value, list):
        return any(_has_secret_field(item) for item in value)
    return False


def verify_msn_manual_archive_handoff(handoff: Mapping[str, Any] | str) -> dict[str, Any]:
    packet = _as_mapping(handoff)
    issues: list[str] = []
    if packet.get("schema_version") != "msn_manual_archive_handoff_v1":
        issues.append("unexpected_schema_version")
    if packet.get("archive_handoff_status") != "MSN_MANUAL_ARCHIVE_HANDOFF_READY":
        issues.append("archive_handoff_not_ready")
    if not packet.get("archive_handoff_id"):
        issues.append("missing_archive_handoff_id")
    if not packet.get("release_id"):
        issues.append("missing_release_id")
    if not packet.get("queue_item_id"):
        issues.append("missing_queue_item_id")
    if not _URL_RE.match(str(packet.get("source_url") or "")):
        issues.append("invalid_source_url")
    if not _SHA256_RE.match(str(packet.get("source_url_sha256") or "")):
        issues.append("invalid_source_url_sha256")
    if packet.get("readiness_issues"):
        issues.append("handoff_contains_readiness_issues")
    if _has_secret_field(packet):
        issues.append("secret_like_field_detected")

    tasks = packet.get("archive_tasks") or []
    providers = packet.get("providers") or []
    if not isinstance(tasks, list) or not tasks:
        issues.append("missing_archive_tasks")
    if len(tasks) != len(providers):
        issues.append("provider_task_count_mismatch")
    task_providers: set[str] = set()
    for task in tasks if isinstance(tasks, list) else []:
        if not isinstance(task, Mapping):
            issues.append("invalid_archive_task")
            continue
        provider = str(task.get("provider") or "")
        task_providers.add(provider)
        if not _SAFE_PROVIDER_RE.match(provider):
            issues.append("unsafe_provider")
        if task.get("task_status") != "PENDING_OPERATOR_ARCHIVAL":
            issues.append("task_not_pending_operator_archival")
        if task.get("execution_mode") != "MANUAL_OPERATOR_ONLY":
            issues.append("task_not_manual_operator_only")
        if task.get("external_call_performed_by_code") is not False:
            issues.append("task_external_call_flag_not_false")
    if set(providers) != task_providers:
        issues.append("provider_list_task_provider_mismatch")

    result_template = packet.get("archive_result_template") or []
    for result in result_template if isinstance(result_template, list) else []:
        if not isinstance(result, Mapping):
            issues.append("invalid_result_template_entry")
            continue
        if str(result.get("archive_url_or_artifact_id") or ""):
            issues.append("result_template_already_contains_archive_result")
        if str(result.get("result_status") or "") != "PENDING":
            issues.append("result_template_not_pending")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": sorted(set(issues)),
        "archive_handoff_id": packet.get("archive_handoff_id"),
        "queue_item_id": packet.get("queue_item_id"),
        "release_id": packet.get("release_id"),
    }


def verify_msn_manual_archive_handoff_json(handoff: Mapping[str, Any] | str) -> str:
    return json.dumps(verify_msn_manual_archive_handoff(handoff), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


__all__ = ["SCHEMA_VERSION", "verify_msn_manual_archive_handoff", "verify_msn_manual_archive_handoff_json"]
