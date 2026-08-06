from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from capture_action_log import ACTOR_TYPE_APPLICATION, CaptureActionLogEvent, build_action_log_event


EXECUTION_GATE_SCHEMA_VERSION = "execution_gate_v1"

EXECUTION_STATUS_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY = "APPROVED_FOR_MANUAL_OPERATOR_ONLY"
EXECUTION_STATUS_BLOCKED = "BLOCKED"
EXECUTION_STATUS_COMPLETED_MANUALLY_IMPORTED = "COMPLETED_MANUALLY_IMPORTED"

EXECUTION_STATE_GATED = "EXECUTION_GATED"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ExecutionActionKind(_StringEnum):
    LIVE_SITE_CAPTURE = "LIVE_SITE_CAPTURE"
    BROWSER_AUTOMATION = "BROWSER_AUTOMATION"
    ARCHIVE_CHECK = "ARCHIVE_CHECK"
    ARCHIVE_SUBMIT = "ARCHIVE_SUBMIT"
    MEDIA_DOWNLOAD = "MEDIA_DOWNLOAD"
    RENDERED_RECORDING = "RENDERED_RECORDING"
    WARC_CAPTURE = "WARC_CAPTURE"
    WACZ_PACKAGE = "WACZ_PACKAGE"
    ARCHIVEBOX_EXECUTION = "ARCHIVEBOX_EXECUTION"
    ASR_PROVIDER_CALL = "ASR_PROVIDER_CALL"
    EVIDENCE_FILE_MOVE = "EVIDENCE_FILE_MOVE"
    BROAD_FOLDER_SCAN = "BROAD_FOLDER_SCAN"


ACTION_KINDS = tuple(kind.value for kind in ExecutionActionKind)

DEFAULT_SAFETY_PROHIBITIONS = (
    "no_live_network_without_later_site_action_approval",
    "no_browser_automation_without_later_site_action_approval",
    "no_archive_provider_check_or_submission_without_later_approval",
    "no_external_download_without_later_approval",
    "no_real_screenshot_or_ocr_without_later_approval",
    "no_ffmpeg_or_ytdlp_execution_without_later_approval",
    "no_warc_capture_or_wacz_packaging_without_later_approval",
    "no_archivebox_docker_wsl_remote_execution_without_later_approval",
    "no_credentials_cookies_accounts_auth_headers_or_browser_profiles",
    "no_captcha_solving_stealth_fingerprint_evasion_or_proxy_rotation",
    "no_drm_cdm_eme_hdcp_or_protected_buffer_circumvention",
    "no_broad_folder_scan",
    "no_evidence_file_move",
    "no_provider_network_call_without_later_approval",
    "no_automatic_classification",
    "no_sensitive_attribute_inference",
)


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


def _source_host_label(source_url: str) -> str:
    if not source_url:
        return ""
    return (urlparse(source_url).hostname or "").lower()


def _source_url_hash(source_url: str) -> str:
    if not source_url:
        return ""
    return "url_" + hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]


def _normalize_action_kind(action_kind: str | ExecutionActionKind) -> ExecutionActionKind:
    text = action_kind.value if isinstance(action_kind, ExecutionActionKind) else str(action_kind or "")
    normalized = text.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        return ExecutionActionKind(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported execution-gate action kind: {action_kind}") from exc


@dataclass(frozen=True)
class ExecutionGateApprovalMetadata:
    approved_by_label_recorded: bool = False
    approved_at_utc: str = ""
    approved_action_ids: tuple[str, ...] = ()
    approval_reference_id: str = ""
    safety_boundaries_acknowledged: bool = False
    approval_status: str = EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ExecutionGateRequest:
    request_id: str
    action_kind: ExecutionActionKind
    source_label: str = ""
    source_url_recorded: bool = False
    source_url_hash: str = ""
    source_host_label: str = ""
    intended_scope: str = ""
    approval_status: str = EXECUTION_STATUS_APPROVAL_REQUIRED
    execution_state: str = EXECUTION_STATE_GATED
    application_execution_allowed: bool = False
    manual_operator_only: bool = True
    user_review_required: bool = True
    safety_prohibitions: tuple[str, ...] = DEFAULT_SAFETY_PROHIBITIONS
    schema_version: str = EXECUTION_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ExecutionGateDecision:
    request_id: str
    action_kind: ExecutionActionKind
    approval_status: str = EXECUTION_STATUS_APPROVAL_REQUIRED
    execution_state: str = EXECUTION_STATE_GATED
    approval_required: bool = True
    approved_for_manual_operator_only: bool = False
    application_execution_allowed: bool = False
    command_emitted: bool = False
    network_allowed: bool = False
    browser_automation_allowed: bool = False
    archive_provider_allowed: bool = False
    download_allowed: bool = False
    file_move_allowed: bool = False
    broad_folder_scan_allowed: bool = False
    provider_call_allowed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    warning: str = "Execution remains gated; no runtime action is emitted."

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ExecutionGatePlan:
    plan_id: str
    status: str
    requests: tuple[ExecutionGateRequest, ...]
    decisions: tuple[ExecutionGateDecision, ...]
    approval_metadata: ExecutionGateApprovalMetadata | None = None
    safety_prohibitions: tuple[str, ...] = DEFAULT_SAFETY_PROHIBITIONS
    execution_state: str = EXECUTION_STATE_GATED
    approval_required: bool = True
    application_execution_allowed: bool = False
    command_count: int = 0
    live_network_allowed: bool = False
    browser_automation_allowed: bool = False
    archive_provider_allowed: bool = False
    download_allowed: bool = False
    file_move_allowed: bool = False
    broad_folder_scan_allowed: bool = False
    provider_call_allowed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    schema_version: str = EXECUTION_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_execution_gate_request(
    *,
    action_kind: str | ExecutionActionKind,
    source_label: str = "",
    source_url: str = "",
    intended_scope: str = "",
) -> ExecutionGateRequest:
    kind = _normalize_action_kind(action_kind)
    request_payload = {
        "action_kind": kind.value,
        "intended_scope": intended_scope,
        "source_host_label": _source_host_label(source_url),
        "source_label": source_label,
        "source_url_hash": _source_url_hash(source_url),
    }
    return ExecutionGateRequest(
        request_id="execution_gate_request_" + _sha16(request_payload),
        action_kind=kind,
        source_label=source_label,
        source_url_recorded=bool(source_url),
        source_url_hash=request_payload["source_url_hash"],
        source_host_label=request_payload["source_host_label"],
        intended_scope=intended_scope,
    )


def build_execution_gate_plan(
    requests: Iterable[ExecutionGateRequest],
    *,
    approval_metadata: ExecutionGateApprovalMetadata | None = None,
) -> ExecutionGatePlan:
    ordered_requests = tuple(sorted(tuple(requests), key=lambda request: request.request_id))
    approved_ids = set(approval_metadata.approved_action_ids) if approval_metadata else set()
    acknowledged = bool(
        approval_metadata
        and approval_metadata.safety_boundaries_acknowledged
        and approval_metadata.approved_by_label_recorded
        and approval_metadata.approved_at_utc
    )
    decisions: list[ExecutionGateDecision] = []
    for request in ordered_requests:
        manual_approved = acknowledged and request.request_id in approved_ids
        decisions.append(
            ExecutionGateDecision(
                request_id=request.request_id,
                action_kind=request.action_kind,
                approval_status=(
                    EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
                    if manual_approved
                    else EXECUTION_STATUS_APPROVAL_REQUIRED
                ),
                approval_required=not manual_approved,
                approved_for_manual_operator_only=manual_approved,
            )
        )
    payload = {
        "approval_statuses": [decision.approval_status for decision in decisions],
        "request_ids": [request.request_id for request in ordered_requests],
        "schema_version": EXECUTION_GATE_SCHEMA_VERSION,
    }
    status = (
        EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
        if decisions and all(decision.approved_for_manual_operator_only for decision in decisions)
        else EXECUTION_STATUS_APPROVAL_REQUIRED
    )
    return ExecutionGatePlan(
        plan_id="execution_gate_plan_" + _sha16(payload),
        status=status,
        requests=ordered_requests,
        decisions=tuple(decisions),
        approval_metadata=approval_metadata,
        approval_required=any(decision.approval_required for decision in decisions) or not decisions,
    )


def execution_gate_plan_to_action_log_events(
    plan: ExecutionGatePlan,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> tuple[CaptureActionLogEvent, ...]:
    if not session_id:
        raise ValueError("session_id is required for execution-gate receipts")
    if not timestamp_utc:
        raise ValueError("timestamp_utc is required for deterministic execution-gate receipts")
    event = build_action_log_event(
        session_id=session_id,
        actor_type=ACTOR_TYPE_APPLICATION,
        actor_id=actor_id,
        action_type="execution_gate_plan_recorded",
        result=plan.status,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        target_id=plan.plan_id,
        request_summary={
            "action_kinds": tuple(request.action_kind.value for request in plan.requests),
            "application_execution_allowed": False,
            "approval_required": plan.approval_required,
            "automatic_classification": False,
            "browser_automation_allowed": False,
            "command_count": 0,
            "download_allowed": False,
            "execution_state": plan.execution_state,
            "file_move_allowed": False,
            "live_network_allowed": False,
            "plan_id": plan.plan_id,
            "provider_call_allowed": False,
            "request_count": len(plan.requests),
            "sensitive_inference_prohibited": True,
            "status": plan.status,
        },
        warnings=(
            "Execution gate metadata only; no live, browser, archive, download, provider, scan, file-move, or classification action is emitted.",
        ),
        app_version=app_version,
    )
    return (event,)


def execution_gate_plan_to_json(plan: ExecutionGatePlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True)


def build_execution_gate_plan_text(plan: ExecutionGatePlan) -> str:
    action_kinds = ", ".join(request.action_kind.value for request in plan.requests) or "(none)"
    return "\n".join(
        [
            "Execution gate plan",
            f"Plan ID: {plan.plan_id}",
            f"Status: {plan.status}",
            f"Actions: {action_kinds}",
            f"Approval required: {str(plan.approval_required).lower()}",
            "Execution state: EXECUTION_GATED",
            "Manual operator only: yes",
            "Application execution allowed: false",
            "Commands emitted: 0",
            "Live/network/browser/archive/download/provider/file-move flags: false",
            "Automatic classification: false",
            "Sensitive inference prohibited: true",
        ]
    )
