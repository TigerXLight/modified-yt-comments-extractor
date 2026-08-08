from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_adapters import default_source_method_profile_for_adapter


SOURCE_GRABBED_RECORD_SCHEMA_VERSION = "source_grabbed_record_v1"


@dataclass(frozen=True)
class GrabbedSourceArchiveReceipt:
    service_id: str
    status: str
    archive_url: str = ""
    result_reference: str = ""
    provider_call_performed: bool = False
    submission_performed: bool = False
    user_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class GrabbedSourceRecord:
    grabbed_source_record_id: str
    source_row_id: str
    source_url: str
    canonical_url: str
    site_profile_id: str
    adapter_id: str
    capture_method_profile_id: str
    capture_method_family: str
    operator_approval_reference: str = ""
    relative_artifact_paths: tuple[str, ...] = ()
    archive_receipts: tuple[GrabbedSourceArchiveReceipt, ...] = ()
    transcript_or_asr_reference: str = ""
    content_digest_sha256: str = ""
    redacted_credential_references: tuple[str, ...] = ()
    evidence_item_ids: tuple[str, ...] = ()
    total_export_item_ids: tuple[str, ...] = ()
    created_at_utc: str = ""
    updated_at_utc: str = ""
    review_state: str = "USER_REVIEW_REQUIRED"
    schema_version: str = SOURCE_GRABBED_RECORD_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    manual_operator_only: bool = True
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    live_capture_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    evidence_file_move_performed: bool = False
    automatic_classification: bool = False

    @property
    def artifact_count(self) -> int:
        return len(self.relative_artifact_paths)

    @property
    def archive_receipt_count(self) -> int:
        return len(self.archive_receipts)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["artifact_count"] = self.artifact_count
        data["archive_receipt_count"] = self.archive_receipt_count
        return data


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), ensure_ascii=False, indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()


def _sha16(data: Any) -> str:
    return _sha256(data)[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


def _archive_receipts_from_metadata(
    source_row_id: str,
    archive_metadata: Iterable[Mapping[str, Any]],
) -> tuple[GrabbedSourceArchiveReceipt, ...]:
    receipts: list[GrabbedSourceArchiveReceipt] = []
    for item in archive_metadata:
        service_id = str(item.get("service_id") or item.get("archive_service") or "").strip()
        status = str(item.get("status") or item.get("archive_status") or "approval_required").strip()
        if not service_id:
            continue
        receipts.append(
            GrabbedSourceArchiveReceipt(
                service_id=service_id,
                status=status,
                archive_url=str(item.get("archive_url") or "").strip(),
                result_reference=f"{source_row_id}:{service_id}:{status}",
                provider_call_performed=bool(item.get("provider_call_performed", False)),
                submission_performed=bool(item.get("submission_performed", False)),
            )
        )
    receipts.sort(key=lambda receipt: (receipt.service_id, receipt.status, receipt.archive_url))
    return tuple(receipts)


def build_grabbed_source_record(
    *,
    source_row_id: str,
    source_url: str,
    canonical_url: str,
    adapter_id: str,
    relative_artifact_paths: Iterable[str],
    selected_modes: Iterable[str],
    evidence_item_ids: Iterable[str] = (),
    total_export_item_ids: Iterable[str] = (),
    archive_metadata: Iterable[Mapping[str, Any]] = (),
    operator_approval_reference: str = "",
    transcript_or_asr_reference: str = "",
    redacted_credential_references: Iterable[str] = (),
    created_at_utc: str = "",
    updated_at_utc: str = "",
) -> GrabbedSourceRecord:
    profile = default_source_method_profile_for_adapter(adapter_id)
    safe_artifact_paths = _stable_tuple(
        path for path in relative_artifact_paths if "/" in str(path or "") and "\\" not in str(path or "")
    )
    archive_receipts = _archive_receipts_from_metadata(source_row_id, archive_metadata)
    content_digest = _sha256(
        {
            "adapter_id": adapter_id,
            "archive_receipts": [receipt.to_dict() for receipt in archive_receipts],
            "canonical_url": canonical_url,
            "relative_artifact_paths": safe_artifact_paths,
            "selected_modes": _stable_tuple(selected_modes),
            "source_row_id": source_row_id,
        }
    )
    identity_payload = {
        "adapter_id": adapter_id,
        "canonical_url": canonical_url,
        "content_digest_sha256": content_digest,
        "profile_id": profile.profile_id,
        "source_row_id": source_row_id,
    }
    return GrabbedSourceRecord(
        grabbed_source_record_id="grabbed_source_" + _sha16(identity_payload),
        source_row_id=str(source_row_id or ""),
        source_url=str(source_url or ""),
        canonical_url=str(canonical_url or source_url or ""),
        site_profile_id=profile.profile_id,
        adapter_id=str(adapter_id or ""),
        capture_method_profile_id=profile.profile_id,
        capture_method_family=profile.method_family,
        operator_approval_reference=str(operator_approval_reference or ""),
        relative_artifact_paths=safe_artifact_paths,
        archive_receipts=archive_receipts,
        transcript_or_asr_reference=str(transcript_or_asr_reference or ""),
        content_digest_sha256=content_digest,
        redacted_credential_references=_stable_tuple(redacted_credential_references),
        evidence_item_ids=_stable_tuple(evidence_item_ids),
        total_export_item_ids=_stable_tuple(total_export_item_ids),
        created_at_utc=str(created_at_utc or ""),
        updated_at_utc=str(updated_at_utc or created_at_utc or ""),
    )


def validate_grabbed_source_record(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_GRABBED_RECORD_SCHEMA_VERSION:
        raise ValueError("Unsupported grabbed source record schema version")
    for required in ("grabbed_source_record_id", "source_row_id", "canonical_url", "adapter_id"):
        if not data.get(required):
            raise ValueError(f"Grabbed source record missing required field: {required}")
    for required_false in (
        "file_existence_claimed",
        "full_local_path_included",
        "raw_payload_included",
        "live_capture_performed",
        "browser_automation_performed",
        "archive_provider_call_performed",
        "download_performed",
        "evidence_file_move_performed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe grabbed source record flag: {required_false}")


def grabbed_source_record_to_json(record: GrabbedSourceRecord) -> str:
    return _stable_json(record.to_dict(), pretty=True)
