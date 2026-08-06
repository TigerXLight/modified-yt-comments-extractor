from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping
from urllib.parse import urlparse


ACTIVITY_LOG_SCHEMA_VERSION = "activity_log_model_v1"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ActivityActorType(_StringEnum):
    USER = "USER"
    APPLICATION = "APPLICATION"
    EXTERNAL_TOOL = "EXTERNAL_TOOL"


class ActivityType(_StringEnum):
    SOURCE_URL_ADDED = "SOURCE_URL_ADDED"
    SOURCE_URL_NORMALIZED = "SOURCE_URL_NORMALIZED"
    SOURCE_URL_REJECTED = "SOURCE_URL_REJECTED"
    MEDIA_ITEM_ADDED = "MEDIA_ITEM_ADDED"
    TRANSCRIPT_IMPORT_REVIEWED = "TRANSCRIPT_IMPORT_REVIEWED"
    CAPTURE_PLAN_PREVIEWED = "CAPTURE_PLAN_PREVIEWED"
    EXPORT_QUEUE_REVIEWED = "EXPORT_QUEUE_REVIEWED"
    REVIEW_NOTE_ADDED = "REVIEW_NOTE_ADDED"
    QUEUE_SUMMARY_GENERATED = "QUEUE_SUMMARY_GENERATED"


SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "session_token",
    "token",
)

RAW_PAYLOAD_KEY_FRAGMENTS = (
    "raw_comment",
    "raw_evidence",
    "raw_livechat",
    "raw_media",
    "raw_payload",
    "raw_record",
    "raw_reply",
    "raw_transcript",
    "tweet_text",
    "transcript_text",
)

FILE_STATE_KEY_FRAGMENTS = (
    "checksum",
    "exists",
    "file_exists",
    "file_size",
    "hash",
    "local_path",
    "path_checked",
    "sha256",
    "size_bytes",
)


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _value_for_dict(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _value_for_dict(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _lower_key(key: str) -> str:
    return str(key or "").lower().replace("-", "_")


def _contains_fragment(key: str, fragments: tuple[str, ...]) -> bool:
    lowered = _lower_key(key)
    return any(fragment in lowered for fragment in fragments)


def _looks_like_full_local_path(value: str) -> bool:
    text = value.strip()
    if len(text) >= 3 and text[1] == ":" and text[2] in ("\\", "/"):
        return True
    return text.startswith("\\\\")


def _validate_safe_metadata(value: Any, *, key_path: str = "metadata") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{key_path}.{key_text}"
            if _contains_fragment(key_text, SECRET_KEY_FRAGMENTS):
                raise ValueError(f"Unsafe secret-like activity metadata field: {child_path}")
            if _contains_fragment(key_text, RAW_PAYLOAD_KEY_FRAGMENTS):
                raise ValueError(f"Unsafe raw-payload activity metadata field: {child_path}")
            if _contains_fragment(key_text, FILE_STATE_KEY_FRAGMENTS):
                raise ValueError(f"Unsafe file-state activity metadata field: {child_path}")
            _validate_safe_metadata(child, key_path=child_path)
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_safe_metadata(child, key_path=f"{key_path}[{index}]")
        return
    if isinstance(value, str) and _looks_like_full_local_path(value):
        raise ValueError(f"Unsafe full local path in activity metadata: {key_path}")


def _safe_metadata(value: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(value or {})
    _validate_safe_metadata(data)
    return {
        str(key): _value_for_dict(data[key])
        for key in sorted(data, key=lambda item: str(item))
    }


def _hash_text(prefix: str, text: str) -> str:
    if not text:
        return ""
    return prefix + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _source_host_label(source_url: str) -> str:
    if not source_url:
        return ""
    parsed = urlparse(source_url)
    return (parsed.hostname or "").lower()


@dataclass(frozen=True)
class ActivityLogPrivacyPolicy:
    schema_version: str = ACTIVITY_LOG_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    telemetry_enabled: bool = False
    persistence_enabled: bool = False
    user_review_required: bool = True
    raw_payloads_allowed: bool = False
    full_local_paths_allowed: bool = False
    file_reads_allowed: bool = False
    file_checks_allowed: bool = False
    file_moves_allowed: bool = False
    file_existence_claims_allowed: bool = False
    completed_evidence_claims_allowed: bool = False
    verified_evidence_claims_allowed: bool = False
    automatic_classification_allowed: bool = False
    protected_attribute_inference_allowed: bool = False
    credentials_allowed: bool = False
    network_allowed: bool = False
    browser_automation_allowed: bool = False
    note: str = (
        "MODEL_ONLY behavior/activity metadata contract; no runtime logging, "
        "telemetry, persistence, file operations, or classification is performed."
    )

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class BehaviorActivityRecord:
    activity_id: str
    session_id: str
    activity_type: ActivityType
    actor_type: ActivityActorType
    activity_time_utc: str
    actor_label_recorded: bool = False
    item_id: str = ""
    source_url_recorded: bool = False
    source_url_hash: str = ""
    source_host_label: str = ""
    before_state_hash: str = ""
    after_state_hash: str = ""
    changed_fields: tuple[str, ...] = ()
    user_note_recorded: bool = False
    evidence_basis_recorded: bool = False
    export_package_id: str = ""
    database_root_recorded: bool = False
    metadata_summary: Mapping[str, Any] | None = None
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    telemetry_enabled: bool = False
    persistence_enabled: bool = False
    file_read_performed: bool = False
    file_check_performed: bool = False
    file_move_performed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference: bool = False
    schema_version: str = ACTIVITY_LOG_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["metadata_summary"] = _safe_metadata(self.metadata_summary)
        return data


@dataclass(frozen=True)
class BehaviorActivityLogSummary:
    summary_id: str
    status: str
    record_count: int = 0
    activity_type_counts: tuple[dict[str, Any], ...] = ()
    actor_type_counts: tuple[dict[str, Any], ...] = ()
    source_url_recorded_count: int = 0
    source_host_labels: tuple[str, ...] = ()
    changed_field_count: int = 0
    user_note_recorded_count: int = 0
    evidence_basis_recorded_count: int = 0
    metadata_only: bool = True
    local_only: bool = True
    telemetry_enabled: bool = False
    persistence_enabled: bool = False
    file_read_performed: bool = False
    file_check_performed: bool = False
    file_move_performed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference: bool = False
    user_review_required: bool = True
    schema_version: str = ACTIVITY_LOG_SCHEMA_VERSION
    note: str = (
        "Summary-only behavior/activity metadata; runtime logging and storage "
        "remain unimplemented."
    )

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def behavior_activity_record_id(
    *,
    session_id: str,
    activity_type: ActivityType,
    actor_type: ActivityActorType,
    activity_time_utc: str,
    item_id: str = "",
    source_url_hash: str = "",
    before_state_hash: str = "",
    after_state_hash: str = "",
    changed_fields: tuple[str, ...] = (),
) -> str:
    payload = {
        "activity_time_utc": activity_time_utc,
        "activity_type": activity_type.value,
        "actor_type": actor_type.value,
        "after_state_hash": after_state_hash,
        "before_state_hash": before_state_hash,
        "changed_fields": list(changed_fields),
        "item_id": item_id,
        "session_id": session_id,
        "source_url_hash": source_url_hash,
    }
    return "activity_" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()[:16]


def build_behavior_activity_record(
    *,
    session_id: str,
    activity_type: ActivityType,
    actor_type: ActivityActorType,
    activity_time_utc: str,
    actor_label: str = "",
    item_id: str = "",
    source_url: str = "",
    before_state_hash: str = "",
    after_state_hash: str = "",
    changed_fields: tuple[str, ...] = (),
    user_note: str = "",
    evidence_basis: str = "",
    export_package_id: str = "",
    database_root_label: str = "",
    metadata_summary: Mapping[str, Any] | None = None,
) -> BehaviorActivityRecord:
    if not session_id:
        raise ValueError("session_id is required for behavior/activity metadata")
    if not activity_time_utc:
        raise ValueError("activity_time_utc is required for deterministic behavior/activity metadata")
    if not isinstance(activity_type, ActivityType):
        raise ValueError("activity_type must be an ActivityType")
    if not isinstance(actor_type, ActivityActorType):
        raise ValueError("actor_type must be an ActivityActorType")

    safe_metadata = _safe_metadata(metadata_summary)
    normalized_changed_fields = tuple(
        sorted({str(field) for field in changed_fields if str(field)})
    )
    source_hash = _hash_text("source_url_", source_url)
    record_id = behavior_activity_record_id(
        session_id=session_id,
        activity_type=activity_type,
        actor_type=actor_type,
        activity_time_utc=activity_time_utc,
        item_id=item_id,
        source_url_hash=source_hash,
        before_state_hash=before_state_hash,
        after_state_hash=after_state_hash,
        changed_fields=normalized_changed_fields,
    )
    return BehaviorActivityRecord(
        activity_id=record_id,
        session_id=session_id,
        activity_type=activity_type,
        actor_type=actor_type,
        activity_time_utc=activity_time_utc,
        actor_label_recorded=bool(actor_label),
        item_id=item_id,
        source_url_recorded=bool(source_url),
        source_url_hash=source_hash,
        source_host_label=_source_host_label(source_url),
        before_state_hash=before_state_hash,
        after_state_hash=after_state_hash,
        changed_fields=normalized_changed_fields,
        user_note_recorded=bool(user_note),
        evidence_basis_recorded=bool(evidence_basis),
        export_package_id=export_package_id,
        database_root_recorded=bool(database_root_label),
        metadata_summary=safe_metadata,
    )


def _count_rows(values: tuple[str, ...], label: str) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for value in sorted(set(values)):
        rows.append({label: value, "count": sum(1 for item in values if item == value)})
    return tuple(rows)


def behavior_activity_log_summary_id(
    records: tuple[BehaviorActivityRecord, ...],
) -> str:
    payload = {
        "record_ids": [record.activity_id for record in records],
        "summary_kind": "behavior_activity_log_metadata",
    }
    return "activity_summary_" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()[:16]


def build_behavior_activity_log_summary(
    records: tuple[BehaviorActivityRecord, ...],
) -> BehaviorActivityLogSummary:
    ordered_records = tuple(sorted(records, key=lambda record: record.activity_id))
    activity_types = tuple(record.activity_type.value for record in ordered_records)
    actor_types = tuple(record.actor_type.value for record in ordered_records)
    source_host_labels = tuple(
        sorted({record.source_host_label for record in ordered_records if record.source_host_label})
    )
    return BehaviorActivityLogSummary(
        summary_id=behavior_activity_log_summary_id(ordered_records),
        status="USER_REVIEW_REQUIRED" if ordered_records else "NO_ACTIVITY_RECORDS",
        record_count=len(ordered_records),
        activity_type_counts=_count_rows(activity_types, "activity_type"),
        actor_type_counts=_count_rows(actor_types, "actor_type"),
        source_url_recorded_count=sum(1 for record in ordered_records if record.source_url_recorded),
        source_host_labels=source_host_labels,
        changed_field_count=sum(len(record.changed_fields) for record in ordered_records),
        user_note_recorded_count=sum(1 for record in ordered_records if record.user_note_recorded),
        evidence_basis_recorded_count=sum(1 for record in ordered_records if record.evidence_basis_recorded),
    )


def behavior_activity_record_to_json(record: BehaviorActivityRecord) -> str:
    return json.dumps(record.to_dict(), indent=2, sort_keys=True)


def behavior_activity_log_summary_to_json(summary: BehaviorActivityLogSummary) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_behavior_activity_log_summary_text(
    summary: BehaviorActivityLogSummary,
) -> str:
    return "\n".join(
        [
            "Behavior/activity log metadata summary",
            f"Summary ID: {summary.summary_id}",
            f"Status: {summary.status}",
            f"Records: {summary.record_count}",
            f"Source URLs recorded: {summary.source_url_recorded_count}",
            f"Changed fields: {summary.changed_field_count}",
            "Metadata only: yes",
            "Local only: yes",
            "Telemetry enabled: false",
            "Persistence enabled: false",
            "File read/check/move flags: false",
            "File existence/final/completed/verified evidence claims: false",
            "Raw payload/full local path flags: false",
            "Auto-classify flag: false",
            "Protected-attribute inference: false",
        ]
    )
