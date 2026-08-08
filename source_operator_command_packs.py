from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_named_site_method_packs import (
    SourceNamedSiteMethodPackCollection,
    build_source_named_site_method_pack_collection,
)


SOURCE_OPERATOR_COMMAND_PACKS_SCHEMA_VERSION = "source_operator_command_packs_v1"


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
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


def _operator_inputs_for_pack(pack: Any) -> tuple[str, ...]:
    inputs = list(tuple(getattr(pack, "required_operator_inputs", ()) or ()))
    inputs.extend(("explicit_site_level_approval", "operator_review_note"))
    if bool(getattr(pack, "selector_audit_required", False)):
        inputs.append("site_specific_selector_audit_note")
    if str(getattr(pack, "site_group", "")) == "twitter_x":
        inputs.append("operator_supplied_archive_or_export_reference")
    if str(getattr(pack, "method_id", "")) == "archive_only_import":
        inputs.extend(("archive_url", "original_url"))
    return _stable_tuple(inputs)


@dataclass(frozen=True)
class SourceOperatorCommandPack:
    command_pack_id: str
    named_site_method_pack_id: str
    site_profile_id: str
    site_group: str
    method_id: str
    source_type: str
    command_kind: str = "approval_gated_operator_command_pack"
    required_operator_inputs: tuple[str, ...] = ()
    approval_checklist: tuple[str, ...] = ()
    expected_artifact_refs: tuple[str, ...] = ()
    expected_receipt_refs: tuple[str, ...] = ()
    no_live_execution_status: str = "not_live_executed"
    rollback_no_file_move_note: str = "No evidence files are moved by this command pack."
    credential_boundary_note: str = "Credentials, cookies, accounts, and API keys are not included or read."
    source_evidence_mapping: Mapping[str, Any] | None = None
    total_export_mapping: Mapping[str, Any] | None = None
    metadata_only: bool = True
    operator_approval_required: bool = True
    executed: bool = False
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceOperatorCommandPackCollection:
    collection_id: str
    packs: tuple[SourceOperatorCommandPack, ...]
    schema_version: str = SOURCE_OPERATOR_COMMAND_PACKS_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    approval_status: str = "OPERATOR_APPROVAL_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    no_live_execution_status: str = "no_live_execution_performed"
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def pack_count(self) -> int:
        return len(self.packs)

    @property
    def approval_required_count(self) -> int:
        return sum(1 for pack in self.packs if pack.operator_approval_required)

    @property
    def selector_audit_required_count(self) -> int:
        return sum(1 for pack in self.packs if "site_specific_selector_audit_note" in pack.required_operator_inputs)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["pack_count"] = self.pack_count
        data["approval_required_count"] = self.approval_required_count
        data["selector_audit_required_count"] = self.selector_audit_required_count
        return data


def build_source_operator_command_pack_collection(
    named_site_method_packs: SourceNamedSiteMethodPackCollection | None = None,
) -> SourceOperatorCommandPackCollection:
    source_packs = named_site_method_packs or build_source_named_site_method_pack_collection()
    command_packs: list[SourceOperatorCommandPack] = []
    for pack in source_packs.packs:
        payload = {
            "method_id": pack.method_id,
            "pack_id": pack.pack_id,
            "schema_version": SOURCE_OPERATOR_COMMAND_PACKS_SCHEMA_VERSION,
        }
        expected_receipts = (
            "operator_approval_receipt",
            "manual_observation_receipt",
            "not_live_executed_receipt",
            "source_evidence_review_receipt",
            "total_export_review_receipt",
        )
        if pack.selector_audit_required:
            expected_receipts = expected_receipts + ("selector_audit_receipt",)
        command_packs.append(
            SourceOperatorCommandPack(
                command_pack_id="source_operator_command_pack_" + _sha16(payload),
                named_site_method_pack_id=pack.pack_id,
                site_profile_id=pack.site_profile_id,
                site_group=pack.site_group,
                method_id=pack.method_id,
                source_type=pack.source_type,
                required_operator_inputs=_operator_inputs_for_pack(pack),
                approval_checklist=(
                    "confirm_named_site_and_source_url",
                    "confirm_scope_is_approved_before_live_execution",
                    "confirm_no_credentials_cookies_accounts_or_api_keys_are_included",
                    "confirm_no_file_moves_or_completed_evidence_claims",
                    "confirm_operator_receipt_will_be_recorded_before_any_execution",
                ),
                expected_artifact_refs=pack.expected_artifact_refs,
                expected_receipt_refs=expected_receipts,
                source_evidence_mapping=pack.database_mapping,
                total_export_mapping=pack.total_export_mapping,
            )
        )
    command_packs.sort(key=lambda item: (item.site_group, item.method_id, item.command_pack_id))
    payload = {
        "command_pack_ids": [pack.command_pack_id for pack in command_packs],
        "schema_version": SOURCE_OPERATOR_COMMAND_PACKS_SCHEMA_VERSION,
    }
    return SourceOperatorCommandPackCollection(
        collection_id="source_operator_command_packs_" + _sha16(payload),
        packs=tuple(command_packs),
    )


def validate_source_operator_command_pack_collection(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_OPERATOR_COMMAND_PACKS_SCHEMA_VERSION:
        raise ValueError("Unsupported source operator command pack schema version")
    for required_true in ("metadata_only", "local_only", "sensitive_inference_prohibited"):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe operator command pack collection flag: {required_true}")
    for required_false in (
        "live_execution_performed",
        "browser_automation_performed",
        "provider_call_performed",
        "archive_submission_performed",
        "download_performed",
        "file_move_performed",
        "completed_evidence_claimed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe operator command pack collection flag: {required_false}")
    packs = data.get("packs", ())
    if not isinstance(packs, list) or not packs:
        raise ValueError("Operator command pack collection must contain packs")
    for pack in packs:
        if pack.get("executed") is not False:
            raise ValueError("Operator command pack must not be marked executed")
        if pack.get("operator_approval_required") is not True:
            raise ValueError("Operator command pack must require approval")


def source_operator_command_pack_collection_to_json(
    collection: SourceOperatorCommandPackCollection,
) -> str:
    return _stable_json(collection.to_dict(), pretty=True)
