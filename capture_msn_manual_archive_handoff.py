from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "msn_manual_archive_handoff_v1"
ARCHIVE_HANDOFF_STATUS_READY = "MSN_MANUAL_ARCHIVE_HANDOFF_READY"
ARCHIVE_HANDOFF_STATUS_REVIEW_REQUIRED = "MSN_MANUAL_ARCHIVE_HANDOFF_REVIEW_REQUIRED"
TASK_STATUS_PENDING = "PENDING_OPERATOR_ARCHIVAL"

_ALLOWED_PROVIDERS = (
    "archive_today",
    "ghostarchive",
    "wayback_machine",
    "perma_cc",
    "manual_local_mirror",
)
_PROVIDER_LABELS = {
    "archive_today": "archive.today / archive.ph manual submission",
    "ghostarchive": "Ghostarchive manual submission",
    "wayback_machine": "Internet Archive Wayback manual save",
    "perma_cc": "Perma.cc manual capture",
    "manual_local_mirror": "Manual local mirror artifact",
}
_URL_RE = re.compile(r"^https?://[^\s<>{}\"']+$", re.I)
_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,220}$")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _normalise_providers(providers: Sequence[str] | None) -> list[str]:
    chosen = list(providers or ("archive_today", "ghostarchive", "wayback_machine"))
    normalised: list[str] = []
    for provider in chosen:
        token = str(provider or "").strip().lower().replace("-", "_").replace(".", "_")
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
        canonical = aliases.get(token, token)
        if canonical not in _ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported archive provider: {provider}")
        if canonical not in normalised:
            normalised.append(canonical)
    return normalised


def _operator_steps_for(provider: str) -> list[str]:
    if provider == "archive_today":
        return [
            "Open the source URL in the operator browser session.",
            "Submit the URL manually to archive.today/archive.ph.",
            "Record the resulting archive URL only after the service returns it.",
        ]
    if provider == "ghostarchive":
        return [
            "Open Ghostarchive manually.",
            "Submit the source URL using the site's normal operator flow.",
            "Record the archive URL and any failure text in the result template.",
        ]
    if provider == "wayback_machine":
        return [
            "Open the Wayback Machine save page manually.",
            "Submit the source URL without automation from this code path.",
            "Record the saved snapshot URL if the save succeeds.",
        ]
    if provider == "perma_cc":
        return [
            "Create a Perma.cc capture manually from an authorized operator account.",
            "Record the Perma link only after the operator confirms the capture.",
        ]
    return [
        "Create or select the local mirror artifact manually.",
        "Record only the safe relative artifact filename or identifier in the result template.",
    ]


def build_msn_manual_archive_handoff(
    release_audit_report: Mapping[str, Any] | str,
    *,
    source_url: str,
    providers: Sequence[str] | None = None,
    operator_label: str = "manual_operator",
    archive_notes: str = "",
) -> dict[str, Any]:
    audit = _as_mapping(release_audit_report)
    source_url = str(source_url or "").strip()
    provider_list = _normalise_providers(providers)

    queue_item_id = str(audit.get("queue_item_id") or "")
    release_id = str(audit.get("release_id") or "")
    audit_report_id = str(audit.get("audit_report_id") or "")
    audit_schema = str(audit.get("schema_version") or "")
    audit_status = str(audit.get("audit_status") or "")

    readiness_issues: list[str] = []
    if audit_schema != "msn_manual_release_audit_report_v1":
        readiness_issues.append("unexpected_audit_report_schema")
    if audit_status != "MSN_MANUAL_RELEASE_AUDIT_READY":
        readiness_issues.append("release_audit_not_ready")
    if audit.get("readiness_issues"):
        readiness_issues.append("release_audit_has_readiness_issues")
    if not queue_item_id:
        readiness_issues.append("missing_queue_item_id")
    if not release_id:
        readiness_issues.append("missing_release_id")
    if not audit_report_id:
        readiness_issues.append("missing_audit_report_id")
    if not _URL_RE.match(source_url):
        readiness_issues.append("invalid_source_url")
    if _has_secret_field(audit):
        readiness_issues.append("secret_like_audit_field_detected")
    if _has_absolute_path(audit):
        readiness_issues.append("absolute_path_detected_in_audit_report")

    source_url_sha256 = _hash_text(source_url) if source_url else ""
    archive_tasks: list[dict[str, Any]] = []
    result_templates: list[dict[str, Any]] = []
    for index, provider in enumerate(provider_list, start=1):
        task_seed = f"{release_id}|{provider}|{source_url_sha256}|{index}"
        task_id = f"{release_id or queue_item_id}.archive_task.{provider}.{_hash_text(task_seed)[:10]}"
        archive_tasks.append(
            {
                "task_id": task_id,
                "provider": provider,
                "provider_label": _PROVIDER_LABELS[provider],
                "task_status": TASK_STATUS_PENDING,
                "execution_mode": "MANUAL_OPERATOR_ONLY",
                "external_call_performed_by_code": False,
                "source_url_sha256": source_url_sha256,
                "operator_steps": _operator_steps_for(provider),
                "required_result_fields": [
                    "provider",
                    "task_id",
                    "result_status",
                    "archive_url_or_artifact_id",
                    "captured_at_utc",
                    "operator_label",
                    "operator_notes",
                ],
            }
        )
        result_templates.append(
            {
                "provider": provider,
                "task_id": task_id,
                "result_status": "PENDING",
                "archive_url_or_artifact_id": "",
                "captured_at_utc": "",
                "operator_label": _safe_text(operator_label, max_length=120),
                "operator_notes": "",
                "failure_reason": "",
            }
        )

    packet = {
        "schema_version": SCHEMA_VERSION,
        "archive_handoff_status": ARCHIVE_HANDOFF_STATUS_READY if not readiness_issues else ARCHIVE_HANDOFF_STATUS_REVIEW_REQUIRED,
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "audit_report_id": audit_report_id,
        "source_url": source_url,
        "source_url_sha256": source_url_sha256,
        "operator_label": _safe_text(operator_label, max_length=120),
        "archive_notes": _safe_text(archive_notes, max_length=500),
        "provider_count": len(provider_list),
        "providers": provider_list,
        "readiness_issues": readiness_issues,
        "archive_tasks": archive_tasks,
        "archive_result_template": result_templates,
        "handoff_constraints": [
            "Archive submissions are manual operator actions outside this code path.",
            "This packet does not prove any archive succeeded.",
            "Record archive result URLs only in the later archive-result intake boundary.",
            "Do not store credentials, cookies, tokens, or account-specific key material in archive results.",
        ],
        "next_boundary": "msn_manual_archive_result_intake",
    }
    packet["archive_handoff_id"] = f"{release_id or queue_item_id}.archive_handoff.{_hash_json(packet)[:12]}"
    packet["content_sha256"] = _hash_json(packet)
    return packet


def msn_manual_archive_handoff_to_json(packet: Mapping[str, Any]) -> str:
    return _stable_json(packet) + "\n"


__all__ = [
    "SCHEMA_VERSION",
    "ARCHIVE_HANDOFF_STATUS_READY",
    "ARCHIVE_HANDOFF_STATUS_REVIEW_REQUIRED",
    "TASK_STATUS_PENDING",
    "build_msn_manual_archive_handoff",
    "msn_manual_archive_handoff_to_json",
]
