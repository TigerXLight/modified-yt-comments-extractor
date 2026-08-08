from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any

from capture_controller import OperationalCapturePlanResult
from capture_export_queue import (
    OperationalCaptureExportQueueConnection,
    connect_operational_capture_plan_to_export_queue,
)
from evidence_item_queue_store import (
    EvidenceItemQueueReviewStoreDocument,
    build_evidence_item_queue_review_store_document,
)
from source_evidence_review_export import build_source_evidence_review_manifest
from source_evidence_release_readiness import (
    SourceEvidenceReleaseReadiness,
    build_source_evidence_release_readiness,
)
from total_export_manifest import TotalExportManifest


SOURCE_EVIDENCE_WORKFLOW_STATE_SCHEMA_VERSION = "source_evidence_workflow_state_v1"


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


@dataclass(frozen=True)
class SourceEvidenceWorkflowState:
    """App-facing source-evidence state assembled without running live capture."""

    source_row_id: str
    source_title: str
    adapter_id: str
    selected_modes: tuple[str, ...]
    screenshot_intents: tuple[str, ...]
    execution_gate_status: str
    execution_gate_plan_id: str
    execution_gate_action_kinds: tuple[str, ...]
    queue_item_count: int
    queue_link_count: int
    total_export_asset_count: int
    evidence_index_record_count: int
    review_preview_record_count: int
    queue_review_store_id: str
    review_manifest_package_id: str
    review_manifest_asset_count: int
    release_readiness: SourceEvidenceReleaseReadiness
    release_readiness_id: str
    release_target_count: int
    connection: OperationalCaptureExportQueueConnection
    queue_review_store_document: EvidenceItemQueueReviewStoreDocument
    review_manifest: TotalExportManifest
    schema_version: str = SOURCE_EVIDENCE_WORKFLOW_STATE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    approval_required: bool = True
    local_only: bool = True
    metadata_only: bool = True
    runtime_executed: bool = False
    live_network_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    file_existence_claimed: bool = False
    raw_payload_included: bool = False
    full_local_path_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        gate_actions = ", ".join(self.execution_gate_action_kinds) or "(none)"
        return "\n".join(
            [
                "Source Evidence workflow state",
                f"Source: {self.source_title}",
                f"Adapter: {self.adapter_id}",
                f"Review status: {self.review_status}",
                f"Execution state: {self.execution_state}",
                f"Execution gate status: {self.execution_gate_status}",
                f"Execution-gated actions: {gate_actions}",
                f"Queue items: {self.queue_item_count}",
                f"Queue links: {self.queue_link_count}",
                f"Total Export assets: {self.total_export_asset_count}",
                f"Review manifest assets: {self.review_manifest_asset_count}",
                f"Release readiness: {self.release_readiness.release_status}",
                f"Release targets: {self.release_target_count}",
                f"Queue review store: {self.queue_review_store_id}",
                "Runtime executed: false",
                "Live/network/browser/archive/download/file actions performed: none",
                "Evidence status: USER_REVIEW_REQUIRED; completion, verification, and finalization are not claimed",
            ]
        )


def build_source_evidence_workflow_state(
    plan: OperationalCapturePlanResult,
    *,
    package_id: str = "",
    created_at_utc: str = "",
    app_version: str = "",
    database_root_id: str = "",
    taxonomy_version_id: str = "",
) -> SourceEvidenceWorkflowState:
    timestamp = created_at_utc or (
        plan.action_events[-1].timestamp_utc if plan.action_events else "1970-01-01T00:00:00Z"
    )
    safe_package_id = package_id or f"source_evidence_review_{plan.source_row_id}"
    connection = connect_operational_capture_plan_to_export_queue(
        plan,
        package_id=safe_package_id,
        database_root_id=database_root_id,
        taxonomy_version_id=taxonomy_version_id,
    )
    previous_hash = plan.action_events[-1].event_hash if plan.action_events else ""
    store_document = build_evidence_item_queue_review_store_document(
        connection.queue,
        session_id=f"{safe_package_id}_queue_review_store",
        timestamp_utc=timestamp,
        previous_event_hash=previous_hash,
        actor_id="application",
        actor_label="application",
        app_version=app_version,
    )
    gate_plan = plan.execution_gate_plan
    gate_actions = tuple(
        request.action_kind.value for request in gate_plan.requests
    ) if gate_plan is not None else ()
    gate_status = gate_plan.status if gate_plan is not None else "APPROVAL_REQUIRED"
    gate_id = gate_plan.plan_id if gate_plan is not None else ""
    release_readiness = build_source_evidence_release_readiness(
        source_row_id=plan.source_row_id,
        adapter_id=plan.adapter_id,
        selected_modes=plan.selected_modes,
        execution_gate_status=gate_status,
        execution_gate_action_kinds=gate_actions,
        queue_item_count=len(connection.queue.items),
        total_export_asset_count=len(connection.total_export_manifest.assets),
        review_manifest_package_id=safe_package_id,
        queue_review_store_id=store_document.store_id,
        created_at_utc=timestamp,
    )
    review_manifest = build_source_evidence_review_manifest(
        package_id=safe_package_id,
        created_at_utc=timestamp,
        source_urls=(plan.canonical_url,),
        queue=connection.queue,
        execution_gate_plan=plan.execution_gate_plan,
        queue_review_store_document=store_document,
        release_readiness_metadata=release_readiness.to_dict(),
        app_version=app_version,
    )
    return SourceEvidenceWorkflowState(
        source_row_id=plan.source_row_id,
        source_title=plan.source_title,
        adapter_id=plan.adapter_id,
        selected_modes=tuple(plan.selected_modes),
        screenshot_intents=tuple(plan.screenshot_intents),
        execution_gate_status=gate_status,
        execution_gate_plan_id=gate_id,
        execution_gate_action_kinds=gate_actions,
        queue_item_count=len(connection.queue.items),
        queue_link_count=len(connection.queue.links),
        total_export_asset_count=len(connection.total_export_manifest.assets),
        evidence_index_record_count=len(connection.evidence_index_records),
        review_preview_record_count=connection.review_preview.record_count,
        queue_review_store_id=store_document.store_id,
        review_manifest_package_id=review_manifest.package_id,
        review_manifest_asset_count=len(review_manifest.assets),
        release_readiness=release_readiness,
        release_readiness_id=release_readiness.release_readiness_id,
        release_target_count=release_readiness.target_count,
        connection=connection,
        queue_review_store_document=store_document,
        review_manifest=review_manifest,
    )


def source_evidence_workflow_state_to_json(state: SourceEvidenceWorkflowState) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True)
