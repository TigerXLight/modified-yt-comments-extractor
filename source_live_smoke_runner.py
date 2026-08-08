from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from source_named_site_method_packs import (
    SourceNamedSiteMethodPack,
    SourceNamedSiteMethodPackCollection,
    build_source_named_site_method_pack_collection,
)
from source_operator_approval_gateway import (
    OperatorApprovalDecision,
    OperatorApprovalStatus,
    OperatorApprovalToken,
    OperatorExecutionAction,
    OperatorExecutionScope,
    evaluate_operator_approval,
)


SOURCE_LIVE_SMOKE_RUNNER_SCHEMA_VERSION = "source_live_smoke_runner_v1"


class LiveSmokeRunnerStatus(str, Enum):
    DRY_RUN_PREVIEW = "dry_run_preview"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED_NOT_EXECUTED = "approved_not_executed"
    CANCELLED = "cancelled"
    RESULT_IMPORTED = "result_imported"


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


def _stable_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(value), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def _actions_for_method(method_id: str) -> tuple[OperatorExecutionAction, ...]:
    actions = [
        OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
        OperatorExecutionAction.SCREENSHOT_CAPTURE,
        OperatorExecutionAction.ARTICLE_CAPTURE,
    ]
    if "comments" in method_id or "thread" in method_id:
        actions.append(OperatorExecutionAction.COMMENTS_CAPTURE)
    if "livechat" in method_id:
        actions.append(OperatorExecutionAction.LIVECHAT_CAPTURE)
    if "youtube_media" in method_id:
        actions.extend((OperatorExecutionAction.MEDIA_DOWNLOAD_COPY, OperatorExecutionAction.ASR_EXECUTION_READINESS))
    if "archive" in method_id:
        actions.append(OperatorExecutionAction.ARCHIVE_CHECK)
    return tuple(sorted(set(actions), key=lambda item: item.value))


def _preview_command(method_id: str, source_url: str) -> tuple[str, ...]:
    return (
        "manual-operator",
        "source-smoke",
        "--method",
        method_id,
        "--source-url",
        source_url,
        "--dry-run",
    )


@dataclass(frozen=True)
class LiveSmokeRunnerPlan:
    plan_id: str
    named_site: str
    source_url: str
    method_pack_id: str
    method_id: str
    selected_capture_options: tuple[str, ...]
    approval_checklist: tuple[str, ...]
    required_manual_preconditions: tuple[str, ...]
    dry_run_command_preview: tuple[str, ...]
    expected_receipts_path: str
    status: LiveSmokeRunnerStatus = LiveSmokeRunnerStatus.DRY_RUN_PREVIEW
    operator_approval_required: bool = True
    run_command_gated_by_live_approval: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    asr_job_run: bool = False
    credentials_read: bool = False
    schema_version: str = SOURCE_LIVE_SMOKE_RUNNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LiveSmokeRunnerDecision:
    decision_id: str
    plan: LiveSmokeRunnerPlan
    approval_decisions: tuple[OperatorApprovalDecision, ...]
    status: LiveSmokeRunnerStatus
    command_executed: bool = False
    result_imported_to_workflow: bool = False
    imported_result_summary: Mapping[str, Any] | None = None
    cancellation_requested: bool = False
    schema_version: str = SOURCE_LIVE_SMOKE_RUNNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LiveSmokeRunnerPlanCollection:
    collection_id: str
    plans: tuple[LiveSmokeRunnerPlan, ...]
    schema_version: str = SOURCE_LIVE_SMOKE_RUNNER_SCHEMA_VERSION
    no_live_execution_performed: bool = True
    approval_required_count: int = 0

    @property
    def plan_count(self) -> int:
        return len(self.plans)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["plan_count"] = self.plan_count
        data["approval_required_count"] = sum(1 for plan in self.plans if plan.operator_approval_required)
        return data


def build_live_smoke_runner_plan(
    pack: SourceNamedSiteMethodPack,
    *,
    source_url: str,
    selected_capture_options: Sequence[str] = (),
) -> LiveSmokeRunnerPlan:
    checklist = (
        "confirm_site_url_and_method_pack",
        "confirm_operator_is_allowed_to_access_site_manually",
        "confirm_no_credentials_cookies_accounts_or_credential_material_are_supplied",
        "confirm_archive_submit_or_external_download_requires_separate_approval",
        "confirm_results_import_records_receipts_without claiming final verified artifacts",
    )
    preconditions = tuple(sorted(set(pack.required_operator_inputs + ("live_site_operator_approval_token", "receipts_output_directory"))))
    default_options = tuple(action.value for action in _actions_for_method(pack.method_id))
    return LiveSmokeRunnerPlan(
        plan_id="live_smoke_runner_plan_" + _sha16((pack.pack_id, source_url, selected_capture_options)),
        named_site=pack.site_display_name,
        source_url=source_url,
        method_pack_id=pack.pack_id,
        method_id=pack.method_id,
        selected_capture_options=tuple(sorted(selected_capture_options)) or default_options,
        approval_checklist=checklist,
        required_manual_preconditions=preconditions,
        dry_run_command_preview=_preview_command(pack.method_id, source_url),
        expected_receipts_path=f"receipts/{pack.method_id}_manual_smoke_receipt.json",
    )


def build_live_smoke_runner_plan_collection(
    *,
    source_url: str = "https://example.invalid/source",
    packs: SourceNamedSiteMethodPackCollection | None = None,
) -> LiveSmokeRunnerPlanCollection:
    collection = packs or build_source_named_site_method_pack_collection()
    plans = tuple(
        build_live_smoke_runner_plan(pack, source_url=source_url)
        for pack in sorted(collection.packs, key=lambda item: (item.site_group, item.method_id))
    )
    return LiveSmokeRunnerPlanCollection(
        collection_id="live_smoke_runner_plans_" + _sha16([plan.to_dict() for plan in plans]),
        plans=plans,
    )


def evaluate_live_smoke_runner_plan(
    plan: LiveSmokeRunnerPlan,
    *,
    token: OperatorApprovalToken | None = None,
    cancel_requested: bool = False,
) -> LiveSmokeRunnerDecision:
    if cancel_requested:
        return LiveSmokeRunnerDecision(
            decision_id="live_smoke_runner_decision_" + _sha16((plan.to_dict(), "cancelled")),
            plan=plan,
            approval_decisions=(),
            status=LiveSmokeRunnerStatus.CANCELLED,
            cancellation_requested=True,
        )
    decisions = tuple(
        evaluate_operator_approval(
            action,
            token=token,
            requested_scope=OperatorExecutionScope.LIVE_EXTERNAL,
        )
        for action in _actions_for_method(plan.method_id)
    )
    if not decisions or any(decision.status != OperatorApprovalStatus.APPROVED_LIVE_EXTERNAL_EXECUTION for decision in decisions):
        status = LiveSmokeRunnerStatus.APPROVAL_REQUIRED
    else:
        status = LiveSmokeRunnerStatus.APPROVED_NOT_EXECUTED
    return LiveSmokeRunnerDecision(
        decision_id="live_smoke_runner_decision_" + _sha16((plan.to_dict(), [decision.to_dict() for decision in decisions])),
        plan=plan,
        approval_decisions=decisions,
        status=status,
        command_executed=False,
    )


def import_manual_live_smoke_result(
    plan: LiveSmokeRunnerPlan,
    *,
    operator_result_summary: Mapping[str, Any],
) -> LiveSmokeRunnerDecision:
    safe_summary = {
        "review_status": str(operator_result_summary.get("review_status") or "USER_REVIEW_REQUIRED"),
        "receipt_name": str(operator_result_summary.get("receipt_name") or ""),
        "artifact_count": int(operator_result_summary.get("artifact_count", 0) or 0),
        "operator_note_present": bool(operator_result_summary.get("operator_note_present", False)),
        "live_execution_was_manual": True,
        "raw_payload_included": False,
        "completed_evidence_claimed": False,
    }
    return LiveSmokeRunnerDecision(
        decision_id="live_smoke_runner_import_" + _sha16((plan.to_dict(), safe_summary)),
        plan=plan,
        approval_decisions=(),
        status=LiveSmokeRunnerStatus.RESULT_IMPORTED,
        command_executed=False,
        result_imported_to_workflow=True,
        imported_result_summary=safe_summary,
    )


def live_smoke_runner_to_json(value: Any) -> str:
    return _stable_json(value, pretty=True)
