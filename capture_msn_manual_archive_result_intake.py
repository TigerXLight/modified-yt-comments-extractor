from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "msn_manual_archive_result_intake_v1"
ARCHIVE_RESULT_STATUS_READY = "MSN_MANUAL_ARCHIVE_RESULTS_READY"
ARCHIVE_RESULT_STATUS_REVIEW_REQUIRED = "MSN_MANUAL_ARCHIVE_RESULTS_REVIEW_REQUIRED"

_ALLOWED_PROVIDERS = {
    "archive_today",
    "ghostarchive",
    "wayback_machine",
    "perma_cc",
    "manual_local_mirror",
}
_ARCHIVE_STATUSES = {
    "ARCHIVED",
    "FAILED",
    "SKIPPED",
    "PENDING",
}
_SUCCESS_STATUS = "ARCHIVED"
_URL_RE = re.compile(r"^https?://[^\s<>{}\"']+$", re.I)
_SAFE_ARTIFACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,220}$")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_ABSOLUTE_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _as_mapping(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _as_results(value: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str) -> list[dict[str, Any]]:
    if isinstance(value, str):
        decoded = json.loads(value)
    else:
        decoded = value
    if isinstance(decoded, Mapping):
        if isinstance(decoded.get("results"), list):
            return [dict(item) for item in decoded["results"] if isinstance(item, Mapping)]
        if isinstance(decoded.get("archive_results"), list):
            return [dict(item) for item in decoded["archive_results"] if isinstance(item, Mapping)]
        if isinstance(decoded.get("archive_result_template"), list):
            return [dict(item) for item in decoded["archive_result_template"] if isinstance(item, Mapping)]
        return [dict(decoded)]
    return [dict(item) for item in decoded if isinstance(item, Mapping)]


def _safe_text(value: Any, *, max_length: int = 300) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _all_nested_values(value: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            values.append(key)
            values.extend(_all_nested_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_all_nested_values(item))
    else:
        values.append(value)
    return values


def _has_secret_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET_FIELD_RE.search(str(key)) or _has_secret_field(item):
                return True
    elif isinstance(value, list):
        return any(_has_secret_field(item) for item in value)
    return False


def _has_absolute_path(value: Any) -> bool:
    return any(_ABSOLUTE_PATH_RE.search(str(item)) for item in _all_nested_values(value))


def _normalise_provider(value: Any) -> str:
    token = str(value or "").strip().lower().replace("-", "_").replace(".", "_")
    aliases = {
        "archive_ph": "archive_today",
        "archive_today": "archive_today",
        "archive_is": "archive_today",
        "ghost_archive": "ghostarchive",
        "ghostarchive": "ghostarchive",
        "wayback": "wayback_machine",
        "wayback_machine": "wayback_machine",
        "internet_archive": "wayback_machine",
        "perma": "perma_cc",
        "perma_cc": "perma_cc",
        "local_mirror": "manual_local_mirror",
        "manual_local_mirror": "manual_local_mirror",
    }
    return aliases.get(token, token)


def _normalise_status(value: Any) -> str:
    token = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SUCCESS": "ARCHIVED",
        "SAVED": "ARCHIVED",
        "COMPLETE": "ARCHIVED",
        "COMPLETED": "ARCHIVED",
        "CAPTURED": "ARCHIVED",
        "ERROR": "FAILED",
        "FAIL": "FAILED",
        "NOT_AVAILABLE": "FAILED",
        "OMITTED": "SKIPPED",
    }
    return aliases.get(token, token or "PENDING")


def _result_artifact_is_safe(provider: str, value: str) -> bool:
    if not value:
        return False
    if _has_absolute_path(value):
        return False
    if provider == "manual_local_mirror":
        return bool(_SAFE_ARTIFACT_RE.match(value))
    return bool(_URL_RE.match(value))


def _receipt_for_result(result: Mapping[str, Any], *, task: Mapping[str, Any] | None) -> dict[str, Any]:
    provider = _normalise_provider(result.get("provider") or (task or {}).get("provider"))
    status = _normalise_status(result.get("result_status"))
    artifact = _safe_text(result.get("archive_url_or_artifact_id"), max_length=500)
    captured_at = _safe_text(result.get("captured_at_utc"), max_length=80)
    task_id = _safe_text(result.get("task_id") or (task or {}).get("task_id"), max_length=260)
    receipt = {
        "task_id": task_id,
        "provider": provider,
        "result_status": status,
        "archive_url_or_artifact_id": artifact,
        "archive_url_or_artifact_sha256": _hash_text(artifact) if artifact else "",
        "captured_at_utc": captured_at,
        "operator_label": _safe_text(result.get("operator_label"), max_length=120),
        "operator_notes": _safe_text(result.get("operator_notes"), max_length=500),
        "failure_reason": _safe_text(result.get("failure_reason"), max_length=500),
        "external_call_performed_by_code": bool(result.get("external_call_performed_by_code", False)),
        "matched_handoff_task": task is not None,
    }
    receipt["receipt_id"] = f"{task_id or provider}.archive_result.{_hash_json(receipt)[:12]}"
    return receipt


def build_msn_manual_archive_result_intake(
    archive_handoff: Mapping[str, Any] | str,
    archive_results: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str,
    *,
    operator_label: str = "manual_operator",
    intake_notes: str = "",
) -> dict[str, Any]:
    handoff = _as_mapping(archive_handoff)
    results = _as_results(archive_results)

    queue_item_id = str(handoff.get("queue_item_id") or "")
    release_id = str(handoff.get("release_id") or "")
    handoff_id = str(handoff.get("archive_handoff_id") or "")
    source_url = str(handoff.get("source_url") or "")
    source_url_sha256 = str(handoff.get("source_url_sha256") or "")
    tasks = [dict(item) for item in handoff.get("archive_tasks", []) or [] if isinstance(item, Mapping)]
    task_by_id = {str(task.get("task_id") or ""): task for task in tasks}

    readiness_issues: list[str] = []
    if handoff.get("schema_version") != "msn_manual_archive_handoff_v1":
        readiness_issues.append("unexpected_archive_handoff_schema")
    if handoff.get("archive_handoff_status") != "MSN_MANUAL_ARCHIVE_HANDOFF_READY":
        readiness_issues.append("archive_handoff_not_ready")
    if handoff.get("readiness_issues"):
        readiness_issues.append("archive_handoff_has_readiness_issues")
    if not queue_item_id:
        readiness_issues.append("missing_queue_item_id")
    if not release_id:
        readiness_issues.append("missing_release_id")
    if not handoff_id:
        readiness_issues.append("missing_archive_handoff_id")
    if not tasks:
        readiness_issues.append("missing_archive_tasks")
    if _has_secret_field(handoff) or _has_secret_field(results):
        readiness_issues.append("secret_like_field_detected")
    if _has_absolute_path(handoff) or _has_absolute_path(results):
        readiness_issues.append("absolute_path_detected")

    seen_task_ids: set[str] = set()
    receipts: list[dict[str, Any]] = []
    for result in results:
        task_id = str(result.get("task_id") or "")
        task = task_by_id.get(task_id)
        provider = _normalise_provider(result.get("provider") or (task or {}).get("provider"))
        status = _normalise_status(result.get("result_status"))
        artifact = _safe_text(result.get("archive_url_or_artifact_id"), max_length=500)

        if task_id in seen_task_ids:
            readiness_issues.append(f"duplicate_result_for_task:{task_id}")
        seen_task_ids.add(task_id)
        if not task:
            readiness_issues.append(f"result_without_matching_task:{task_id or provider}")
        if provider not in _ALLOWED_PROVIDERS:
            readiness_issues.append(f"unsupported_archive_provider:{provider}")
        if status not in _ARCHIVE_STATUSES:
            readiness_issues.append(f"unsupported_archive_result_status:{status}")
        if status == _SUCCESS_STATUS and not _result_artifact_is_safe(provider, artifact):
            readiness_issues.append(f"unsafe_or_missing_archive_result:{task_id or provider}")
        if bool(result.get("external_call_performed_by_code", False)):
            readiness_issues.append(f"external_call_claim_detected:{task_id or provider}")
        if task and provider != _normalise_provider(task.get("provider")):
            readiness_issues.append(f"provider_mismatch_for_task:{task_id}")
        receipts.append(_receipt_for_result(result, task=task))

    missing_task_ids = sorted(set(task_by_id) - seen_task_ids)
    if missing_task_ids:
        readiness_issues.append("missing_results_for_handoff_tasks")
    successful_receipts = [receipt for receipt in receipts if receipt.get("result_status") == _SUCCESS_STATUS]
    if not successful_receipts:
        readiness_issues.append("no_successful_archive_result")

    archive_result_summary = {
        "task_count": len(tasks),
        "result_count": len(receipts),
        "successful_result_count": len(successful_receipts),
        "failed_result_count": len([receipt for receipt in receipts if receipt.get("result_status") == "FAILED"]),
        "skipped_result_count": len([receipt for receipt in receipts if receipt.get("result_status") == "SKIPPED"]),
        "pending_result_count": len([receipt for receipt in receipts if receipt.get("result_status") == "PENDING"]),
        "missing_task_result_count": len(missing_task_ids),
    }
    status = ARCHIVE_RESULT_STATUS_READY if not readiness_issues else ARCHIVE_RESULT_STATUS_REVIEW_REQUIRED
    archive_result_queue_update = {
        "schema_version": "msn_manual_archive_result_queue_update_v1",
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "archive_handoff_id": handoff_id,
        "archive_result_status": status,
        "archive_result_ready": status == ARCHIVE_RESULT_STATUS_READY,
        "successful_archive_count": len(successful_receipts),
        "ready_for_post_archive_review": status == ARCHIVE_RESULT_STATUS_READY,
    }

    packet = {
        "schema_version": SCHEMA_VERSION,
        "archive_result_status": status,
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "archive_handoff_id": handoff_id,
        "source_url": source_url,
        "source_url_sha256": source_url_sha256,
        "operator_label": _safe_text(operator_label, max_length=120),
        "intake_notes": _safe_text(intake_notes, max_length=500),
        "readiness_issues": readiness_issues,
        "archive_result_summary": archive_result_summary,
        "archive_result_receipts": receipts,
        "archive_result_queue_update": archive_result_queue_update,
        "intake_constraints": [
            "Archive results are operator-supplied manual records.",
            "This boundary does not fetch archived URLs or submit external archive requests.",
            "Successful status requires a safe archive URL or local mirror artifact identifier.",
            "Do not store credentials, cookies, tokens, or account-specific key material in archive results.",
        ],
        "next_boundary": "msn_manual_post_archive_review",
    }
    packet["archive_result_intake_id"] = f"{release_id or queue_item_id}.archive_result_intake.{_hash_json(packet)[:12]}"
    packet["content_sha256"] = _hash_json(packet)
    return packet


def msn_manual_archive_result_intake_to_json(packet: Mapping[str, Any]) -> str:
    return _stable_json(packet) + "\n"


__all__ = [
    "SCHEMA_VERSION",
    "ARCHIVE_RESULT_STATUS_READY",
    "ARCHIVE_RESULT_STATUS_REVIEW_REQUIRED",
    "build_msn_manual_archive_result_intake",
    "msn_manual_archive_result_intake_to_json",
]
