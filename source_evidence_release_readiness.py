from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


SOURCE_EVIDENCE_RELEASE_READINESS_SCHEMA_VERSION = "source_evidence_release_readiness_v1"

RELEASE_STATUS_APPROVAL_REQUIRED = "RELEASE_APPROVAL_REQUIRED"
TARGET_STATUS_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

RELEASE_TARGET_KINDS = (
    "total_export_release_manifest",
    "release_upload_target_receipt",
    "file_library_publish_receipt",
    "operator_signoff_receipt",
)


@dataclass(frozen=True)
class SourceEvidenceReleaseTargetReadiness:
    target_kind: str
    target_status: str = TARGET_STATUS_APPROVAL_REQUIRED
    user_review_required: bool = True
    approval_required: bool = True
    metadata_only: bool = True
    live_execution_performed: bool = False
    release_upload_performed: bool = False
    file_library_publish_performed: bool = False
    operator_signoff_performed: bool = False
    completed_release_claimed: bool = False
    note: str = "Release target is represented as metadata only; no delivery action was executed."

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceEvidenceReleaseReadiness:
    release_readiness_id: str
    source_row_id: str
    adapter_id: str
    selected_modes: tuple[str, ...]
    execution_gate_status: str
    execution_gate_action_kinds: tuple[str, ...]
    queue_item_count: int
    total_export_asset_count: int
    review_manifest_package_id: str
    queue_review_store_id: str
    created_at_utc: str
    targets: tuple[SourceEvidenceReleaseTargetReadiness, ...]
    schema_version: str = SOURCE_EVIDENCE_RELEASE_READINESS_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    release_status: str = RELEASE_STATUS_APPROVAL_REQUIRED
    provenance_status: str = "DERIVED_FROM_SOURCE_EVIDENCE_WORKFLOW_METADATA"
    metadata_only: bool = True
    local_only: bool = True
    approval_required: bool = True
    manual_operator_required: bool = True
    export_metadata_only: bool = True
    release_upload_performed: bool = False
    file_library_publish_performed: bool = False
    operator_signoff_performed: bool = False
    live_fetch_or_api_call_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    evidence_file_move_performed: bool = False
    file_existence_claimed: bool = False
    raw_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    completed_release_claimed: bool = False
    verified_evidence_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def target_count(self) -> int:
        return len(self.targets)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["target_count"] = self.target_count
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


def _sha16(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


def build_source_evidence_release_readiness(
    *,
    source_row_id: str,
    adapter_id: str,
    selected_modes: Iterable[str],
    execution_gate_status: str,
    execution_gate_action_kinds: Iterable[str],
    queue_item_count: int,
    total_export_asset_count: int,
    review_manifest_package_id: str,
    queue_review_store_id: str,
    created_at_utc: str,
) -> SourceEvidenceReleaseReadiness:
    modes = _stable_tuple(selected_modes)
    gate_actions = _stable_tuple(execution_gate_action_kinds)
    targets = tuple(
        SourceEvidenceReleaseTargetReadiness(target_kind=target_kind)
        for target_kind in RELEASE_TARGET_KINDS
    )
    payload = {
        "adapter_id": str(adapter_id or ""),
        "execution_gate_action_kinds": gate_actions,
        "execution_gate_status": str(execution_gate_status or ""),
        "queue_review_store_id": str(queue_review_store_id or ""),
        "review_manifest_package_id": str(review_manifest_package_id or ""),
        "selected_modes": modes,
        "source_row_id": str(source_row_id or ""),
        "target_kinds": RELEASE_TARGET_KINDS,
    }
    return SourceEvidenceReleaseReadiness(
        release_readiness_id="source_evidence_release_readiness_" + _sha16(payload),
        source_row_id=str(source_row_id or ""),
        adapter_id=str(adapter_id or ""),
        selected_modes=modes,
        execution_gate_status=str(execution_gate_status or ""),
        execution_gate_action_kinds=gate_actions,
        queue_item_count=max(int(queue_item_count), 0),
        total_export_asset_count=max(int(total_export_asset_count), 0),
        review_manifest_package_id=str(review_manifest_package_id or ""),
        queue_review_store_id=str(queue_review_store_id or ""),
        created_at_utc=str(created_at_utc or ""),
        targets=targets,
    )


def validate_source_evidence_release_readiness(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_EVIDENCE_RELEASE_READINESS_SCHEMA_VERSION:
        raise ValueError("Unsupported Source Evidence release readiness schema version")
    if data.get("release_status") != RELEASE_STATUS_APPROVAL_REQUIRED:
        raise ValueError("Source Evidence release readiness must remain approval-required")
    for required_true in (
        "metadata_only",
        "local_only",
        "approval_required",
        "manual_operator_required",
        "export_metadata_only",
        "sensitive_inference_prohibited",
    ):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe Source Evidence release readiness flag: {required_true}")
    for required_false in (
        "release_upload_performed",
        "file_library_publish_performed",
        "operator_signoff_performed",
        "live_fetch_or_api_call_performed",
        "browser_automation_performed",
        "archive_provider_call_performed",
        "download_performed",
        "evidence_file_move_performed",
        "file_existence_claimed",
        "raw_payload_included",
        "full_local_path_included",
        "completed_evidence_claimed",
        "completed_release_claimed",
        "verified_evidence_claimed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe Source Evidence release readiness flag: {required_false}")
    target_kinds = [target.get("target_kind") for target in data.get("targets", []) if isinstance(target, Mapping)]
    if tuple(target_kinds) != RELEASE_TARGET_KINDS:
        raise ValueError("Source Evidence release readiness targets are incomplete or out of order")


def source_evidence_release_readiness_to_json(
    readiness: SourceEvidenceReleaseReadiness,
) -> str:
    return _stable_json(readiness.to_dict(), pretty=True)
