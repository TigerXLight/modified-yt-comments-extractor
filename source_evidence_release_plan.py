from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_evidence_release_readiness import (
    RELEASE_STATUS_APPROVAL_REQUIRED,
    SourceEvidenceReleaseReadiness,
)


SOURCE_EVIDENCE_RELEASE_PLAN_SCHEMA_VERSION = "source_evidence_release_plan_v1"


@dataclass(frozen=True)
class SourceEvidenceReleaseActionReceipt:
    action_id: str
    target_kind: str
    action_status: str = RELEASE_STATUS_APPROVAL_REQUIRED
    approval_required: bool = True
    user_review_required: bool = True
    metadata_only: bool = True
    manual_operator_required: bool = True
    command_emitted: bool = False
    release_upload_performed: bool = False
    file_library_publish_performed: bool = False
    operator_signoff_performed: bool = False
    completed_release_claimed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    note: str = "Approval-required release target receipt; no release action was executed."

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceEvidenceReleaseActionPlan:
    release_action_plan_id: str
    release_readiness_id: str
    source_row_id: str
    review_manifest_package_id: str
    queue_review_store_id: str
    receipts: tuple[SourceEvidenceReleaseActionReceipt, ...]
    created_at_utc: str
    schema_version: str = SOURCE_EVIDENCE_RELEASE_PLAN_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    release_status: str = RELEASE_STATUS_APPROVAL_REQUIRED
    metadata_only: bool = True
    local_only: bool = True
    approval_required: bool = True
    manual_operator_required: bool = True
    user_review_required: bool = True
    export_metadata_only: bool = True
    command_count: int = 0
    release_upload_performed: bool = False
    file_library_publish_performed: bool = False
    operator_signoff_performed: bool = False
    completed_release_claimed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    live_fetch_or_api_call_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    evidence_file_move_performed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def receipt_count(self) -> int:
        return len(self.receipts)

    @property
    def operator_signoff_required(self) -> bool:
        return any(receipt.target_kind == "operator_signoff_receipt" for receipt in self.receipts)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["operator_signoff_required"] = self.operator_signoff_required
        data["receipt_count"] = self.receipt_count
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


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _receipt_for_target(
    *,
    release_readiness_id: str,
    target_kind: str,
) -> SourceEvidenceReleaseActionReceipt:
    payload = {
        "release_readiness_id": release_readiness_id,
        "target_kind": target_kind,
    }
    return SourceEvidenceReleaseActionReceipt(
        action_id="source_release_action_" + _sha16(payload),
        target_kind=str(target_kind or ""),
    )


def build_source_evidence_release_action_plan(
    readiness: SourceEvidenceReleaseReadiness,
) -> SourceEvidenceReleaseActionPlan:
    receipts = tuple(
        _receipt_for_target(
            release_readiness_id=readiness.release_readiness_id,
            target_kind=target.target_kind,
        )
        for target in readiness.targets
    )
    payload = {
        "queue_review_store_id": readiness.queue_review_store_id,
        "receipt_target_kinds": tuple(receipt.target_kind for receipt in receipts),
        "release_readiness_id": readiness.release_readiness_id,
        "review_manifest_package_id": readiness.review_manifest_package_id,
        "source_row_id": readiness.source_row_id,
    }
    return SourceEvidenceReleaseActionPlan(
        release_action_plan_id="source_release_plan_" + _sha16(payload),
        release_readiness_id=readiness.release_readiness_id,
        source_row_id=readiness.source_row_id,
        review_manifest_package_id=readiness.review_manifest_package_id,
        queue_review_store_id=readiness.queue_review_store_id,
        receipts=receipts,
        created_at_utc=readiness.created_at_utc,
    )


def validate_source_evidence_release_action_plan(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_EVIDENCE_RELEASE_PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported Source Evidence release action plan schema version")
    if data.get("release_status") != RELEASE_STATUS_APPROVAL_REQUIRED:
        raise ValueError("Source Evidence release action plan must remain approval-required")
    for required_true in (
        "metadata_only",
        "local_only",
        "approval_required",
        "manual_operator_required",
        "user_review_required",
        "export_metadata_only",
        "sensitive_inference_prohibited",
    ):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe Source Evidence release action plan flag: {required_true}")
    for required_false in (
        "release_upload_performed",
        "file_library_publish_performed",
        "operator_signoff_performed",
        "completed_release_claimed",
        "file_existence_claimed",
        "full_local_path_included",
        "raw_payload_included",
        "live_fetch_or_api_call_performed",
        "browser_automation_performed",
        "archive_provider_call_performed",
        "download_performed",
        "evidence_file_move_performed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe Source Evidence release action plan flag: {required_false}")
    if data.get("command_count") != 0:
        raise ValueError("Source Evidence release action plan must not emit commands")
    receipts = data.get("receipts", [])
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("Source Evidence release action plan requires receipt metadata")
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise ValueError("Source Evidence release receipt must be an object")
        if receipt.get("action_status") != RELEASE_STATUS_APPROVAL_REQUIRED:
            raise ValueError("Source Evidence release receipt must remain approval-required")
        for required_false in (
            "command_emitted",
            "release_upload_performed",
            "file_library_publish_performed",
            "operator_signoff_performed",
            "completed_release_claimed",
            "file_existence_claimed",
            "full_local_path_included",
            "raw_payload_included",
        ):
            if receipt.get(required_false) is not False:
                raise ValueError(f"Unsafe Source Evidence release receipt flag: {required_false}")


def source_evidence_release_action_plan_to_json(
    plan: SourceEvidenceReleaseActionPlan,
) -> str:
    return _stable_json(plan.to_dict(), pretty=True)
