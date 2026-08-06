from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from capture_execution_gate import (
    EXECUTION_STATUS_APPROVAL_REQUIRED,
    EXECUTION_STATE_GATED,
    ExecutionActionKind,
    ExecutionGatePlan,
    build_execution_gate_plan,
    build_execution_gate_plan_text,
    build_execution_gate_request,
)


ONLINE_ASR_GATE_SCHEMA_VERSION = "online_asr_execution_gate_v1"
ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED = "CONFIGURED"
ONLINE_ASR_CREDENTIAL_STATE_MISSING = "MISSING"
ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE = "UNAVAILABLE"


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
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _sha16(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()[:16]


def _safe_credential_state(status: Any) -> str:
    if status is None:
        return ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE
    state = getattr(status, "state", status)
    value = getattr(state, "value", state)
    text = str(value or "").strip().upper()
    if text == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED:
        return ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED
    if text == ONLINE_ASR_CREDENTIAL_STATE_MISSING:
        return ONLINE_ASR_CREDENTIAL_STATE_MISSING
    if "UNAVAILABLE" in text:
        return ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE
    return text or ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE


def _option_attr(option: Any, name: str, default: str = "") -> str:
    return str(getattr(option, name, default) or "")


@dataclass(frozen=True)
class OnlineASRProviderGateRecord:
    provider_id: str
    display_name: str
    model_id: str
    credential_entry_id: str
    credential_state: str
    credential_configured: bool
    key_or_account_required: bool = True
    provider_call_allowed_without_user_approval: bool = False
    plaintext_secret_storage_allowed: bool = False
    schema_version: str = ONLINE_ASR_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRExecutionGateSummary:
    summary_id: str
    selected_provider_id: str
    selected_model_id: str
    media_file_selected: bool
    media_file_name_recorded: bool
    credential_configured: bool
    provider_count: int
    configured_provider_count: int
    provider_records: tuple[OnlineASRProviderGateRecord, ...]
    execution_gate_plan_id: str
    execution_status: str = EXECUTION_STATUS_APPROVAL_REQUIRED
    execution_state: str = EXECUTION_STATE_GATED
    key_or_account_required: bool = True
    approval_required: bool = True
    provider_call_allowed_without_user_approval: bool = False
    application_execution_allowed_without_user_action: bool = False
    plaintext_secret_storage_allowed: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    transcript_payload_included: bool = False
    completed_transcription_claimed: bool = False
    schema_version: str = ONLINE_ASR_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_online_asr_provider_gate_records(
    provider_options: Iterable[Any],
    credential_statuses: Mapping[str, Any] | None,
) -> tuple[OnlineASRProviderGateRecord, ...]:
    statuses = credential_statuses or {}
    records: list[OnlineASRProviderGateRecord] = []
    for option in provider_options:
        credential_entry_id = _option_attr(option, "credential_entry_id")
        credential_state = _safe_credential_state(statuses.get(credential_entry_id))
        records.append(
            OnlineASRProviderGateRecord(
                provider_id=_option_attr(option, "provider_id"),
                display_name=_option_attr(option, "display_name"),
                model_id=_option_attr(option, "model_id"),
                credential_entry_id=credential_entry_id,
                credential_state=credential_state,
                credential_configured=credential_state == ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
            )
        )
    return tuple(sorted(records, key=lambda record: record.provider_id))


def build_online_asr_execution_gate_plan(
    *,
    selected_provider: Any,
    provider_options: Iterable[Any],
    credential_statuses: Mapping[str, Any] | None,
    media_file_selected: bool,
    media_file_name: str = "",
) -> tuple[ExecutionGatePlan, OnlineASRExecutionGateSummary]:
    selected_provider_id = _option_attr(selected_provider, "provider_id")
    selected_model_id = _option_attr(selected_provider, "model_id")
    selected_display_name = _option_attr(selected_provider, "display_name", selected_provider_id)
    records = build_online_asr_provider_gate_records(provider_options, credential_statuses)
    selected_record = next(
        (record for record in records if record.provider_id == selected_provider_id),
        None,
    )
    credential_configured = bool(selected_record and selected_record.credential_configured)
    request = build_execution_gate_request(
        action_kind=ExecutionActionKind.ASR_PROVIDER_CALL,
        source_label=selected_display_name,
        intended_scope=(
            f"online_asr_provider_call:{selected_provider_id}:"
            f"model={selected_model_id}:"
            f"media_selected={str(bool(media_file_selected)).lower()}"
        ),
    )
    plan = build_execution_gate_plan((request,))
    payload = {
        "credential_configured": credential_configured,
        "execution_gate_plan_id": plan.plan_id,
        "media_file_name_recorded": bool(media_file_name),
        "media_file_selected": bool(media_file_selected),
        "provider_ids": [record.provider_id for record in records],
        "schema_version": ONLINE_ASR_GATE_SCHEMA_VERSION,
        "selected_model_id": selected_model_id,
        "selected_provider_id": selected_provider_id,
    }
    summary = OnlineASRExecutionGateSummary(
        summary_id="online_asr_execution_gate_summary_" + _sha16(payload),
        selected_provider_id=selected_provider_id,
        selected_model_id=selected_model_id,
        media_file_selected=bool(media_file_selected),
        media_file_name_recorded=bool(media_file_name),
        credential_configured=credential_configured,
        provider_count=len(records),
        configured_provider_count=sum(1 for record in records if record.credential_configured),
        provider_records=records,
        execution_gate_plan_id=plan.plan_id,
    )
    return plan, summary


def render_online_asr_execution_gate_summary_text(
    summary: OnlineASRExecutionGateSummary,
    *,
    plan: ExecutionGatePlan | None = None,
) -> str:
    lines = [
        "Online ASR execution gate",
        f"Summary ID: {summary.summary_id}",
        f"Selected provider: {summary.selected_provider_id}",
        f"Selected model: {summary.selected_model_id}",
        f"Credential configured: {str(summary.credential_configured).lower()}",
        f"Media selected: {str(summary.media_file_selected).lower()}",
        f"Provider call allowed without user approval: {str(summary.provider_call_allowed_without_user_approval).lower()}",
        f"Plaintext secret storage allowed: {str(summary.plaintext_secret_storage_allowed).lower()}",
        f"Full local path included: {str(summary.full_local_path_included).lower()}",
        f"Completed transcription claimed: {str(summary.completed_transcription_claimed).lower()}",
    ]
    if plan is not None:
        lines.append(build_execution_gate_plan_text(plan))
    return "\n".join(lines)
