from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA_VERSION = "msn_manual_archive_review_package_v1"
ARCHIVE_REVIEW_STATUS_READY = "MSN_MANUAL_ARCHIVE_REVIEW_READY"
ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED = "MSN_MANUAL_ARCHIVE_REVIEW_REQUIRED"

_SUCCESS_STATUS = "ARCHIVED"
_ALLOWED_PROVIDERS = {
    "archive_today",
    "ghostarchive",
    "wayback_machine",
    "perma_cc",
    "manual_local_mirror",
}
_ARCHIVE_STATUSES = {"ARCHIVED", "FAILED", "SKIPPED", "PENDING"}
_URL_RE = re.compile(r"^https?://[^\s<>{}\"']+$", re.I)
_SAFE_ARTIFACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,220}$")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_ABSOLUTE_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _as_mapping(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


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


def _artifact_is_safe(provider: str, artifact: str) -> bool:
    if not artifact or _has_absolute_path(artifact):
        return False
    if provider == "manual_local_mirror":
        return bool(_SAFE_ARTIFACT_RE.match(artifact))
    return bool(_URL_RE.match(artifact))


def _normalise_receipts(receipts: Any) -> list[dict[str, Any]]:
    if not isinstance(receipts, list):
        return []
    return [dict(item) for item in receipts if isinstance(item, Mapping)]


def _review_action(action_id: str, label: str, required: bool = True) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "label": label,
        "required": required,
        "status": "PENDING_REVIEW",
        "completion_source": "manual_reviewer",
    }


def build_msn_manual_archive_review_package(
    archive_result_intake: Mapping[str, Any] | str,
    *,
    reviewer_label: str = "manual_reviewer",
    review_notes: str = "",
) -> dict[str, Any]:
    intake = _as_mapping(archive_result_intake)
    receipts = _normalise_receipts(intake.get("archive_result_receipts"))

    queue_item_id = str(intake.get("queue_item_id") or "")
    release_id = str(intake.get("release_id") or "")
    handoff_id = str(intake.get("archive_handoff_id") or "")
    intake_id = str(intake.get("archive_result_intake_id") or "")
    source_url_sha256 = str(intake.get("source_url_sha256") or "")
    source_url = str(intake.get("source_url") or "")

    readiness_issues: list[str] = []
    if intake.get("schema_version") != "msn_manual_archive_result_intake_v1":
        readiness_issues.append("unexpected_archive_result_intake_schema")
    if intake.get("archive_result_status") != "MSN_MANUAL_ARCHIVE_RESULTS_READY":
        readiness_issues.append("archive_results_not_ready")
    if intake.get("readiness_issues"):
        readiness_issues.append("archive_result_intake_has_readiness_issues")
    queue_update = intake.get("archive_result_queue_update") or {}
    if isinstance(queue_update, Mapping) and not queue_update.get("ready_for_post_archive_review"):
        readiness_issues.append("archive_result_queue_update_not_ready_for_review")
    if not queue_item_id:
        readiness_issues.append("missing_queue_item_id")
    if not release_id:
        readiness_issues.append("missing_release_id")
    if not handoff_id:
        readiness_issues.append("missing_archive_handoff_id")
    if not intake_id:
        readiness_issues.append("missing_archive_result_intake_id")
    if not receipts:
        readiness_issues.append("missing_archive_result_receipts")
    if _has_secret_field(intake):
        readiness_issues.append("secret_like_field_detected")
    if _has_absolute_path(intake):
        readiness_issues.append("absolute_path_detected")

    receipt_index: list[dict[str, Any]] = []
    successful_receipts: list[dict[str, Any]] = []
    seen_receipt_ids: set[str] = set()
    for receipt in receipts:
        receipt_id = _safe_text(receipt.get("receipt_id"), max_length=260)
        task_id = _safe_text(receipt.get("task_id"), max_length=260)
        provider = _safe_text(receipt.get("provider"), max_length=80)
        result_status = _safe_text(receipt.get("result_status"), max_length=80).upper()
        artifact = _safe_text(receipt.get("archive_url_or_artifact_id"), max_length=500)
        artifact_sha = _safe_text(receipt.get("archive_url_or_artifact_sha256"), max_length=80)

        if not receipt_id:
            readiness_issues.append(f"missing_receipt_id:{task_id or provider or 'unknown'}")
        if receipt_id and receipt_id in seen_receipt_ids:
            readiness_issues.append(f"duplicate_receipt_id:{receipt_id}")
        seen_receipt_ids.add(receipt_id)
        if provider not in _ALLOWED_PROVIDERS:
            readiness_issues.append(f"unsupported_archive_provider:{provider or 'missing'}")
        if result_status not in _ARCHIVE_STATUSES:
            readiness_issues.append(f"unsupported_archive_result_status:{result_status or 'missing'}")
        if not bool(receipt.get("matched_handoff_task", False)):
            readiness_issues.append(f"unmatched_handoff_task:{receipt_id or task_id or provider}")
        if bool(receipt.get("external_call_performed_by_code", False)):
            readiness_issues.append(f"external_call_claim_detected:{receipt_id or task_id or provider}")
        if result_status == _SUCCESS_STATUS:
            if not _artifact_is_safe(provider, artifact):
                readiness_issues.append(f"unsafe_or_missing_successful_archive_artifact:{receipt_id or task_id or provider}")
            if not artifact_sha:
                readiness_issues.append(f"missing_successful_archive_artifact_hash:{receipt_id or task_id or provider}")
            successful_receipts.append(dict(receipt))
        receipt_index.append(
            {
                "receipt_id": receipt_id,
                "task_id": task_id,
                "provider": provider,
                "result_status": result_status,
                "is_successful_archive": result_status == _SUCCESS_STATUS,
                "archive_artifact_sha256": artifact_sha,
                "matched_handoff_task": bool(receipt.get("matched_handoff_task", False)),
            }
        )

    if not successful_receipts:
        readiness_issues.append("no_successful_archive_receipt")

    status = ARCHIVE_REVIEW_STATUS_READY if not readiness_issues else ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED
    review_actions = [
        _review_action("confirm_successful_archive_receipts", "Confirm successful archive receipts are operator-supplied and match handoff tasks."),
        _review_action("manually_compare_archive_target", "Manually compare archived target against the released MSN evidence package."),
        _review_action("confirm_no_secret_or_absolute_path", "Confirm archive receipts contain no credentials and no full local paths."),
        _review_action("record_archive_review_decision", "Record archive review decision before final archive closeout."),
    ]
    archive_receipt_index = {
        "schema_version": "msn_manual_archive_receipt_index_v1",
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "archive_handoff_id": handoff_id,
        "archive_result_intake_id": intake_id,
        "receipt_count": len(receipt_index),
        "successful_receipt_count": len(successful_receipts),
        "receipts": receipt_index,
    }
    archive_review_queue_update = {
        "schema_version": "msn_manual_archive_review_queue_update_v1",
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "archive_result_intake_id": intake_id,
        "archive_review_status": status,
        "archive_review_ready": status == ARCHIVE_REVIEW_STATUS_READY,
        "successful_archive_count": len(successful_receipts),
        "ready_for_archive_review_decision": status == ARCHIVE_REVIEW_STATUS_READY,
    }

    package = {
        "schema_version": SCHEMA_VERSION,
        "archive_review_status": status,
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "archive_handoff_id": handoff_id,
        "archive_result_intake_id": intake_id,
        "source_url": source_url,
        "source_url_sha256": source_url_sha256,
        "reviewer_label": _safe_text(reviewer_label, max_length=120),
        "review_notes": _safe_text(review_notes, max_length=500),
        "readiness_issues": readiness_issues,
        "archive_result_summary": dict(intake.get("archive_result_summary") or {}),
        "successful_archive_receipts": successful_receipts,
        "archive_receipt_index": archive_receipt_index,
        "required_review_actions": review_actions,
        "archive_review_queue_update": archive_review_queue_update,
        "review_constraints": [
            "Archive review is manual and local; no archived URL is fetched by this boundary.",
            "This package does not approve the archive evidence; it prepares it for reviewer decision.",
            "Successful archive receipts must be supplied by the operator and matched to archive handoff tasks.",
            "No credentials, cookies, tokens, or full local paths may be stored in archive evidence records.",
        ],
        "next_boundary": "msn_manual_archive_review_decision",
    }
    package["archive_review_package_id"] = f"{release_id or queue_item_id}.archive_review.{_hash_json(package)[:12]}"
    package["content_sha256"] = _hash_json(package)
    return package


def msn_manual_archive_review_package_to_json(package: Mapping[str, Any]) -> str:
    return _stable_json(package) + "\n"


__all__ = [
    "SCHEMA_VERSION",
    "ARCHIVE_REVIEW_STATUS_READY",
    "ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED",
    "build_msn_manual_archive_review_package",
    "msn_manual_archive_review_package_to_json",
]
