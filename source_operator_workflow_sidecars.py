from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any

from evidence_database_operator_workflow import EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION
from source_live_smoke_runner import build_live_smoke_runner_plan_collection
from source_operator_approval_gateway import (
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_gateway_summary,
    build_operator_approval_token,
)
from source_unified_execution_runner import SOURCE_UNIFIED_EXECUTION_RUNNER_SCHEMA_VERSION


SOURCE_OPERATOR_WORKFLOW_SIDECARS_SCHEMA_VERSION = "source_operator_workflow_sidecars_v1"


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


ALL_EXECUTION_ACTIONS = tuple(OperatorExecutionAction)


@dataclass(frozen=True)
class OperatorWorkflowSidecar:
    sidecar_id: str
    sidecar_role: str
    payload: dict[str, Any]
    schema_version: str = SOURCE_OPERATOR_WORKFLOW_SIDECARS_SCHEMA_VERSION
    user_review_required: bool = True
    live_execution_performed: bool = False
    external_network_performed: bool = False
    credentials_read: bool = False
    asr_job_run: bool = False
    user_evidence_file_moved: bool = False
    completed_real_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OperatorWorkflowSidecarBundle:
    bundle_id: str
    operator_approval_gateway: OperatorWorkflowSidecar
    unified_execution_jobs: OperatorWorkflowSidecar
    local_e2e_total_export: OperatorWorkflowSidecar
    live_smoke_runner: OperatorWorkflowSidecar
    database_movement_operator_workflow: OperatorWorkflowSidecar
    schema_version: str = SOURCE_OPERATOR_WORKFLOW_SIDECARS_SCHEMA_VERSION
    local_temp_fixture_tested: bool = True
    fake_http_tested: bool = True
    mocked_subprocess_tested: bool = True
    live_execution_performed: bool = False
    real_user_evidence_moved: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["sidecar_count"] = 5
        return data


def _sidecar(role: str, payload: dict[str, Any]) -> OperatorWorkflowSidecar:
    return OperatorWorkflowSidecar(
        sidecar_id=f"{role}_" + _sha16(payload),
        sidecar_role=role,
        payload=payload,
    )


def build_operator_workflow_sidecar_bundle() -> OperatorWorkflowSidecarBundle:
    preview_gateway = build_operator_approval_gateway_summary(
        ALL_EXECUTION_ACTIONS,
        requested_scope=OperatorExecutionScope.PREVIEW_ONLY,
    ).to_dict()
    local_token = build_operator_approval_token(
        actions=(
            OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
            OperatorExecutionAction.SCREENSHOT_CAPTURE,
            OperatorExecutionAction.ARTICLE_CAPTURE,
            OperatorExecutionAction.PAGE_OUTLINE_CAPTURE,
            OperatorExecutionAction.COMMENTS_CAPTURE,
            OperatorExecutionAction.LIVECHAT_CAPTURE,
            OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
            OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
        ),
        scope=OperatorExecutionScope.LOCAL_TEMP,
        approved_by_operator=True,
        approval_note="fixture/local temp operator workflow test token",
    )
    local_gateway = build_operator_approval_gateway_summary(
        local_token.actions,
        token=local_token,
        requested_scope=OperatorExecutionScope.LOCAL_TEMP,
    ).to_dict()
    approval_payload = {
        "preview_gateway": preview_gateway,
        "approved_local_temp_gateway": local_gateway,
        "real_external_network_requires_explicit_token": True,
        "real_archive_submit_requires_explicit_token": True,
        "real_user_evidence_movement_requires_explicit_token": True,
        "real_ffmpeg_ytdlp_archivebox_requires_explicit_token": True,
        "real_asr_provider_jobs_require_explicit_token": True,
    }
    unified_payload = {
        "schema_version": SOURCE_UNIFIED_EXECUTION_RUNNER_SCHEMA_VERSION,
        "runner_available": True,
        "calls_existing_bridge_modules": True,
        "local_temp_fixture_jobs_supported": True,
        "fake_http_client_supported": True,
        "mocked_subprocess_supported": True,
        "result_fields": (
            "job_id",
            "progress_events",
            "artifact_names",
            "artifact_hashes",
            "behavior_event_labels",
            "failure_receipts",
        ),
    }
    e2e_payload = {
        "schema_version": "source_local_e2e_export_v1",
        "local_e2e_total_export_callable": True,
        "package_contents": (
            "article_text",
            "visible_page_outline",
            "html_dom_snapshot",
            "faithful_screenshot",
            "comments_export",
            "livechat_export",
            "media_metadata_and_copy_receipt",
            "archive_fake_client_result",
            "offline_bundle",
            "behavior_provenance_log",
            "execution_bridge_sidecar",
            "movement_preview",
            "temp_completed_evidence_receipt",
        ),
        "real_user_evidence_file_movement_performed": False,
    }
    live_smoke_payload = build_live_smoke_runner_plan_collection().to_dict()
    database_payload = {
        "schema_version": EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION,
        "scan_temp_evidence_database_tree_callable": True,
        "preview_taxonomy_migration_callable": True,
        "approved_copy_move_callable": True,
        "collision_policy_supported": True,
        "rollback_failure_receipt_supported": True,
        "completed_evidence_receipt_after_hash_verification_only": True,
        "automatic_classification": False,
        "protected_attribute_inference_performed": False,
        "real_user_evidence_file_movement_performed": False,
    }
    sidecars = (
        _sidecar("operator_approval_gateway", approval_payload),
        _sidecar("unified_execution_jobs", unified_payload),
        _sidecar("local_e2e_total_export", e2e_payload),
        _sidecar("live_smoke_runner", live_smoke_payload),
        _sidecar("database_movement_operator_workflow", database_payload),
    )
    return OperatorWorkflowSidecarBundle(
        bundle_id="source_operator_workflow_sidecars_" + _sha16([sidecar.to_dict() for sidecar in sidecars]),
        operator_approval_gateway=sidecars[0],
        unified_execution_jobs=sidecars[1],
        local_e2e_total_export=sidecars[2],
        live_smoke_runner=sidecars[3],
        database_movement_operator_workflow=sidecars[4],
    )


def operator_workflow_sidecar_to_json(sidecar: OperatorWorkflowSidecar) -> str:
    return _stable_json(sidecar.to_dict(), pretty=True)


def operator_workflow_sidecar_bundle_to_json(bundle: OperatorWorkflowSidecarBundle) -> str:
    return _stable_json(bundle.to_dict(), pretty=True)
