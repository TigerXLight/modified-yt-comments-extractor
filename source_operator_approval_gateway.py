from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable


SOURCE_OPERATOR_APPROVAL_GATEWAY_SCHEMA_VERSION = "source_operator_approval_gateway_v1"


class OperatorExecutionAction(str, Enum):
    BROWSER_LOCAL_CAPTURE = "browser_local_capture"
    SCREENSHOT_CAPTURE = "screenshot_capture"
    ARTICLE_CAPTURE = "article_capture"
    PAGE_OUTLINE_CAPTURE = "page_outline_capture"
    COMMENTS_CAPTURE = "comments_capture"
    LIVECHAT_CAPTURE = "livechat_capture"
    MEDIA_DOWNLOAD_COPY = "media_download_copy"
    FFMPEG_MUX = "ffmpeg_mux"
    YT_DLP_EXECUTION = "yt_dlp_execution"
    ARCHIVE_CHECK = "archive_check"
    ARCHIVE_SUBMIT = "archive_submit"
    ARCHIVEBOX_EXECUTION = "archivebox_execution"
    OFFLINE_BUNDLE_WRITE = "offline_bundle_write"
    EVIDENCE_FILE_COPY = "evidence_file_copy"
    EVIDENCE_FILE_MOVE = "evidence_file_move"
    COMPLETED_EVIDENCE_RECEIPT = "completed_evidence_receipt"
    ASR_EXECUTION_READINESS = "asr_execution_readiness"


class OperatorExecutionScope(str, Enum):
    PREVIEW_ONLY = "preview_only"
    LOCAL_TEMP = "approved_local_temp_execution"
    USER_EVIDENCE = "approved_user_evidence_execution"
    LIVE_EXTERNAL = "approved_live_external_execution"


class OperatorApprovalStatus(str, Enum):
    PREVIEW_ONLY = "preview_only"
    APPROVED_LOCAL_TEMP_EXECUTION = "approved_local_temp_execution"
    APPROVED_USER_EVIDENCE_EXECUTION = "approved_user_evidence_execution"
    APPROVED_LIVE_EXTERNAL_EXECUTION = "approved_live_external_execution"
    BLOCKED_MISSING_APPROVAL = "blocked_missing_approval"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


EXTERNAL_NETWORK_ACTIONS = frozenset(
    {
        OperatorExecutionAction.ARCHIVE_CHECK,
        OperatorExecutionAction.ARCHIVE_SUBMIT,
        OperatorExecutionAction.YT_DLP_EXECUTION,
    }
)
USER_EVIDENCE_ACTIONS = frozenset(
    {
        OperatorExecutionAction.EVIDENCE_FILE_COPY,
        OperatorExecutionAction.EVIDENCE_FILE_MOVE,
        OperatorExecutionAction.COMPLETED_EVIDENCE_RECEIPT,
    }
)
SUBPROCESS_ACTIONS = frozenset(
    {
        OperatorExecutionAction.FFMPEG_MUX,
        OperatorExecutionAction.YT_DLP_EXECUTION,
        OperatorExecutionAction.ARCHIVEBOX_EXECUTION,
    }
)
ASR_ACTIONS = frozenset({OperatorExecutionAction.ASR_EXECUTION_READINESS})


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


def _stable_json(value: Any) -> str:
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def _action_value(action: OperatorExecutionAction | str) -> str:
    return action.value if isinstance(action, OperatorExecutionAction) else str(action)


def _actions_tuple(actions: Iterable[OperatorExecutionAction | str]) -> tuple[OperatorExecutionAction, ...]:
    return tuple(sorted((OperatorExecutionAction(_action_value(action)) for action in actions), key=lambda item: item.value))


@dataclass(frozen=True)
class OperatorApprovalToken:
    token_id: str
    actions: tuple[OperatorExecutionAction, ...]
    scope: OperatorExecutionScope
    approved_by_operator: bool
    operator_label: str = "operator"
    approval_note: str = ""
    allow_external_network: bool = False
    allow_archive_submit: bool = False
    allow_user_evidence_movement: bool = False
    allow_subprocess_execution: bool = False
    allow_asr_execution: bool = False
    cancelled: bool = False
    schema_version: str = SOURCE_OPERATOR_APPROVAL_GATEWAY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["action_count"] = len(self.actions)
        return data


@dataclass(frozen=True)
class OperatorApprovalDecision:
    decision_id: str
    action: OperatorExecutionAction
    status: OperatorApprovalStatus
    allowed_to_execute: bool
    scope: OperatorExecutionScope
    token_id: str = ""
    reasons: tuple[str, ...] = ()
    requires_external_network_approval: bool = False
    requires_archive_submit_approval: bool = False
    requires_user_evidence_approval: bool = False
    requires_subprocess_approval: bool = False
    requires_asr_approval: bool = False
    external_network_allowed: bool = False
    user_evidence_allowed: bool = False
    live_external_allowed: bool = False
    asr_execution_allowed: bool = False
    schema_version: str = SOURCE_OPERATOR_APPROVAL_GATEWAY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OperatorApprovalGatewaySummary:
    summary_id: str
    decisions: tuple[OperatorApprovalDecision, ...]
    schema_version: str = SOURCE_OPERATOR_APPROVAL_GATEWAY_SCHEMA_VERSION
    no_execution_without_token: bool = True
    credentials_read: bool = False
    provider_call_performed: bool = False
    asr_job_run: bool = False

    @property
    def action_count(self) -> int:
        return len(self.decisions)

    @property
    def blocked_count(self) -> int:
        return sum(1 for decision in self.decisions if not decision.allowed_to_execute)

    @property
    def approved_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.allowed_to_execute)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["action_count"] = self.action_count
        data["blocked_count"] = self.blocked_count
        data["approved_count"] = self.approved_count
        return data


def build_operator_approval_token(
    *,
    actions: Iterable[OperatorExecutionAction | str],
    scope: OperatorExecutionScope = OperatorExecutionScope.PREVIEW_ONLY,
    approved_by_operator: bool = False,
    operator_label: str = "operator",
    approval_note: str = "",
    allow_external_network: bool = False,
    allow_archive_submit: bool = False,
    allow_user_evidence_movement: bool = False,
    allow_subprocess_execution: bool = False,
    allow_asr_execution: bool = False,
    cancelled: bool = False,
) -> OperatorApprovalToken:
    normalized_actions = _actions_tuple(actions)
    payload = (
        [action.value for action in normalized_actions],
        scope.value,
        approved_by_operator,
        operator_label,
        approval_note,
        allow_external_network,
        allow_archive_submit,
        allow_user_evidence_movement,
        allow_subprocess_execution,
        allow_asr_execution,
        cancelled,
    )
    return OperatorApprovalToken(
        token_id="operator_approval_token_" + _sha16(payload),
        actions=normalized_actions,
        scope=scope,
        approved_by_operator=approved_by_operator,
        operator_label=operator_label,
        approval_note=approval_note,
        allow_external_network=allow_external_network,
        allow_archive_submit=allow_archive_submit,
        allow_user_evidence_movement=allow_user_evidence_movement,
        allow_subprocess_execution=allow_subprocess_execution,
        allow_asr_execution=allow_asr_execution,
        cancelled=cancelled,
    )


def evaluate_operator_approval(
    action: OperatorExecutionAction | str,
    *,
    token: OperatorApprovalToken | None = None,
    requested_scope: OperatorExecutionScope = OperatorExecutionScope.PREVIEW_ONLY,
) -> OperatorApprovalDecision:
    normalized_action = OperatorExecutionAction(_action_value(action))
    reasons: list[str] = []
    requires_external = normalized_action in EXTERNAL_NETWORK_ACTIONS or requested_scope == OperatorExecutionScope.LIVE_EXTERNAL
    requires_archive_submit = normalized_action == OperatorExecutionAction.ARCHIVE_SUBMIT
    requires_user_evidence = normalized_action in USER_EVIDENCE_ACTIONS or requested_scope == OperatorExecutionScope.USER_EVIDENCE
    requires_subprocess = normalized_action in SUBPROCESS_ACTIONS
    requires_asr = normalized_action in ASR_ACTIONS
    if requested_scope == OperatorExecutionScope.PREVIEW_ONLY:
        return OperatorApprovalDecision(
            decision_id="operator_approval_decision_" + _sha16((normalized_action.value, "preview")),
            action=normalized_action,
            status=OperatorApprovalStatus.PREVIEW_ONLY,
            allowed_to_execute=False,
            scope=requested_scope,
            reasons=("preview_only_no_execution",),
            requires_external_network_approval=requires_external,
            requires_archive_submit_approval=requires_archive_submit,
            requires_user_evidence_approval=requires_user_evidence,
            requires_subprocess_approval=requires_subprocess,
            requires_asr_approval=requires_asr,
        )
    if token is None:
        reasons.append("operator_approval_token_required")
    else:
        if token.cancelled:
            reasons.append("operator_cancelled")
        if not token.approved_by_operator:
            reasons.append("operator_approval_not_granted")
        if normalized_action not in token.actions:
            reasons.append("action_not_covered_by_token")
        if token.scope != requested_scope:
            reasons.append("approval_scope_mismatch")
        if requires_external and not token.allow_external_network:
            reasons.append("external_network_approval_required")
        if requires_archive_submit and not token.allow_archive_submit:
            reasons.append("archive_submit_approval_required")
        if requires_user_evidence and not token.allow_user_evidence_movement:
            reasons.append("user_evidence_movement_approval_required")
        if requires_subprocess and not token.allow_subprocess_execution:
            reasons.append("subprocess_execution_approval_required")
        if requires_asr and not token.allow_asr_execution:
            reasons.append("asr_execution_approval_required")
    allowed = not reasons
    if allowed and requested_scope == OperatorExecutionScope.LOCAL_TEMP:
        status = OperatorApprovalStatus.APPROVED_LOCAL_TEMP_EXECUTION
    elif allowed and requested_scope == OperatorExecutionScope.USER_EVIDENCE:
        status = OperatorApprovalStatus.APPROVED_USER_EVIDENCE_EXECUTION
    elif allowed and requested_scope == OperatorExecutionScope.LIVE_EXTERNAL:
        status = OperatorApprovalStatus.APPROVED_LIVE_EXTERNAL_EXECUTION
    elif "operator_cancelled" in reasons:
        status = OperatorApprovalStatus.CANCELLED
    else:
        status = OperatorApprovalStatus.BLOCKED_MISSING_APPROVAL
    return OperatorApprovalDecision(
        decision_id="operator_approval_decision_" + _sha16((normalized_action.value, requested_scope.value, token.to_dict() if token else None, reasons)),
        action=normalized_action,
        status=status,
        allowed_to_execute=allowed,
        scope=requested_scope,
        token_id=token.token_id if token else "",
        reasons=tuple(reasons),
        requires_external_network_approval=requires_external,
        requires_archive_submit_approval=requires_archive_submit,
        requires_user_evidence_approval=requires_user_evidence,
        requires_subprocess_approval=requires_subprocess,
        requires_asr_approval=requires_asr,
        external_network_allowed=bool(token and token.allow_external_network and allowed),
        user_evidence_allowed=bool(token and token.allow_user_evidence_movement and allowed),
        live_external_allowed=requested_scope == OperatorExecutionScope.LIVE_EXTERNAL and allowed,
        asr_execution_allowed=bool(token and token.allow_asr_execution and allowed),
    )


def build_operator_approval_gateway_summary(
    actions: Iterable[OperatorExecutionAction | str],
    *,
    token: OperatorApprovalToken | None = None,
    requested_scope: OperatorExecutionScope = OperatorExecutionScope.PREVIEW_ONLY,
) -> OperatorApprovalGatewaySummary:
    decisions = tuple(
        evaluate_operator_approval(action, token=token, requested_scope=requested_scope)
        for action in _actions_tuple(actions)
    )
    return OperatorApprovalGatewaySummary(
        summary_id="operator_approval_gateway_" + _sha16([decision.to_dict() for decision in decisions]),
        decisions=decisions,
    )


def operator_approval_gateway_summary_to_json(summary: OperatorApprovalGatewaySummary) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)
