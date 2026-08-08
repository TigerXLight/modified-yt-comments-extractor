from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any

from capture_controller import OperationalCapturePlanResult
from access_keys_catalog import build_default_access_keys_catalog
from access_provider_gate import (
    AccessProviderGateSummary,
    build_access_provider_gate_summary,
)
from capture_export_queue import (
    OperationalCaptureExportQueueConnection,
    connect_operational_capture_plan_to_export_queue,
)
from evidence_database_index import (
    EvidenceIndexManifest,
    evidence_index_record_from_source_site_method_audit_row,
    scan_evidence_index_records,
    stable_evidence_id,
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
from source_evidence_release_plan import (
    SourceEvidenceReleaseActionPlan,
    build_source_evidence_release_action_plan,
)
from source_adapter_audit_registry import (
    SourceAdapterAuditRegistry,
    build_source_adapter_audit_registry,
)
from source_adapter_audit_report import (
    SourceAdapterAuditReport,
    build_source_adapter_audit_report,
)
from source_named_site_priority_plan import (
    SourceNamedSitePriorityPlan,
    build_source_named_site_priority_plan,
)
from source_site_method_audit_registry import (
    SourceSiteMethodAuditRegistry,
    build_source_site_method_audit_registry,
    build_source_site_selector_audit_pack_collection,
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
    grabbed_source_record: Any | None
    grabbed_source_record_id: str
    grabbed_source_artifact_count: int
    database_scan_result: Any
    database_scan_record_count: int
    database_scan_matched_count: int
    access_provider_gate_summary: AccessProviderGateSummary
    access_provider_gate_summary_id: str
    access_provider_gate_record_count: int
    access_provider_gate_approval_required_count: int
    source_adapter_audit_registry: SourceAdapterAuditRegistry
    source_adapter_audit_registry_id: str
    source_adapter_audit_entry_count: int
    source_adapter_audit_required_count: int
    source_site_method_audit_registry: SourceSiteMethodAuditRegistry
    source_site_method_audit_registry_id: str
    source_site_method_audit_row_count: int
    source_site_method_selector_audit_required_count: int
    source_site_method_live_approved_only_count: int
    source_adapter_audit_report: SourceAdapterAuditReport
    source_adapter_audit_report_id: str
    source_adapter_audit_report_row_count: int
    source_adapter_audit_report_selector_audit_required_count: int
    source_named_site_priority_plan: SourceNamedSitePriorityPlan
    source_named_site_priority_plan_id: str
    source_named_site_priority_plan_row_count: int
    source_named_site_priority_plan_approval_required_count: int
    release_readiness: SourceEvidenceReleaseReadiness
    release_readiness_id: str
    release_target_count: int
    release_action_plan: SourceEvidenceReleaseActionPlan
    release_action_plan_id: str
    release_action_receipt_count: int
    operator_signoff_required: bool
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
        data = _value_for_dict(self)
        data["source_adapter_audit_registry"] = self.source_adapter_audit_registry.to_dict()
        data["source_site_method_audit_registry"] = self.source_site_method_audit_registry.to_dict()
        data["source_adapter_audit_report"] = self.source_adapter_audit_report.to_dict()
        data["source_named_site_priority_plan"] = self.source_named_site_priority_plan.to_dict()
        return data

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
                f"Grabbed source record: {self.grabbed_source_record_id}",
                f"Database scan records: {self.database_scan_matched_count}/{self.database_scan_record_count}",
                f"Access/provider gate: {self.access_provider_gate_summary_id}",
                f"Access/provider records: {self.access_provider_gate_record_count}",
                f"Access/provider approvals required: {self.access_provider_gate_approval_required_count}",
                f"Source adapter audit registry: {self.source_adapter_audit_registry_id}",
                f"Source adapter audit entries: {self.source_adapter_audit_entry_count}",
                f"Source adapter audit-required entries: {self.source_adapter_audit_required_count}",
                f"Source site/method audit registry: {self.source_site_method_audit_registry_id}",
                f"Source site/method audit rows: {self.source_site_method_audit_row_count}",
                f"Source site/method selector audit-required rows: {self.source_site_method_selector_audit_required_count}",
                f"Source site/method live-approved-only rows: {self.source_site_method_live_approved_only_count}",
                f"Source adapter audit report: {self.source_adapter_audit_report_id}",
                f"Source adapter audit report rows: {self.source_adapter_audit_report_row_count}",
                f"Source adapter audit report selector audit-required rows: {self.source_adapter_audit_report_selector_audit_required_count}",
                f"Named-site priority plan: {self.source_named_site_priority_plan_id}",
                f"Named-site priority rows: {self.source_named_site_priority_plan_row_count}",
                f"Named-site priority approvals required: {self.source_named_site_priority_plan_approval_required_count}",
                f"Release readiness: {self.release_readiness.release_status}",
                f"Release targets: {self.release_target_count}",
                f"Release action plan: {self.release_action_plan_id}",
                f"Release action receipts: {self.release_action_receipt_count}",
                f"Operator signoff required: {str(self.operator_signoff_required).lower()}",
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
    source_adapter_audit_registry = build_source_adapter_audit_registry()
    source_site_method_audit_registry = build_source_site_method_audit_registry()
    source_site_selector_audit_packs = build_source_site_selector_audit_pack_collection(
        source_site_method_audit_registry
    )
    source_adapter_audit_report = build_source_adapter_audit_report(
        adapter_registry=source_adapter_audit_registry,
        site_method_registry=source_site_method_audit_registry,
        selector_pack_collection=source_site_selector_audit_packs,
        workflow_sidecar_filenames=(
            "source_adapter_audit_registry.json",
            "source_site_method_audit_registry.json",
            "source_site_selector_audit_packs.json",
            "source_adapter_audit_report.json",
        ),
    )
    source_named_site_priority_plan = build_source_named_site_priority_plan(
        source_site_method_audit_registry
    )
    site_method_audit_records = tuple(
        evidence_index_record_from_source_site_method_audit_row(
            row,
            database_root_id=database_root_id,
            taxonomy_version_id=taxonomy_version_id,
        )
        for row in source_site_method_audit_registry.rows
    )
    previous_hash = plan.action_events[-1].event_hash if plan.action_events else ""
    evidence_scan_manifest = EvidenceIndexManifest(
        manifest_id=stable_evidence_id("workflow_scan_manifest", plan.source_row_id, safe_package_id),
        records=tuple(connection.evidence_index_records) + site_method_audit_records,
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
    )
    evidence_scan_result = scan_evidence_index_records(evidence_scan_manifest)
    access_provider_gate_summary = build_access_provider_gate_summary(
        build_default_access_keys_catalog()
    )
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
    release_action_plan = build_source_evidence_release_action_plan(release_readiness)
    review_manifest = build_source_evidence_review_manifest(
        package_id=safe_package_id,
        created_at_utc=timestamp,
        source_urls=(plan.canonical_url,),
        queue=connection.queue,
        execution_gate_plan=plan.execution_gate_plan,
        queue_review_store_document=store_document,
        workflow_state_metadata={
            "database_scan_result": evidence_scan_result.to_dict(),
            "access_provider_gate_summary": access_provider_gate_summary.to_dict(),
            "source_adapter_audit_registry": source_adapter_audit_registry.to_dict(),
            "source_site_method_audit_registry": source_site_method_audit_registry.to_dict(),
            "source_adapter_audit_report": source_adapter_audit_report.to_dict(),
            "source_named_site_priority_plan": source_named_site_priority_plan.to_dict(),
            "grabbed_source_record": (
                plan.grabbed_source_record.to_dict()
                if plan.grabbed_source_record is not None
                else None
            ),
        },
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
        grabbed_source_record=plan.grabbed_source_record,
        grabbed_source_record_id=(
            plan.grabbed_source_record.grabbed_source_record_id
            if plan.grabbed_source_record is not None
            else ""
        ),
        grabbed_source_artifact_count=(
            plan.grabbed_source_record.artifact_count
            if plan.grabbed_source_record is not None
            else 0
        ),
        database_scan_result=evidence_scan_result,
        database_scan_record_count=evidence_scan_result.scanned_record_count,
        database_scan_matched_count=evidence_scan_result.matched_record_count,
        access_provider_gate_summary=access_provider_gate_summary,
        access_provider_gate_summary_id=access_provider_gate_summary.gate_summary_id,
        access_provider_gate_record_count=access_provider_gate_summary.record_count,
        access_provider_gate_approval_required_count=(
            access_provider_gate_summary.approval_required_count
        ),
        source_adapter_audit_registry=source_adapter_audit_registry,
        source_adapter_audit_registry_id=source_adapter_audit_registry.registry_id,
        source_adapter_audit_entry_count=source_adapter_audit_registry.entry_count,
        source_adapter_audit_required_count=source_adapter_audit_registry.audit_required_count,
        source_site_method_audit_registry=source_site_method_audit_registry,
        source_site_method_audit_registry_id=source_site_method_audit_registry.registry_id,
        source_site_method_audit_row_count=source_site_method_audit_registry.row_count,
        source_site_method_selector_audit_required_count=(
            source_site_method_audit_registry.selector_audit_required_count
        ),
        source_site_method_live_approved_only_count=(
            source_site_method_audit_registry.live_approved_only_count
        ),
        source_adapter_audit_report=source_adapter_audit_report,
        source_adapter_audit_report_id=source_adapter_audit_report.report_id,
        source_adapter_audit_report_row_count=source_adapter_audit_report.row_count,
        source_adapter_audit_report_selector_audit_required_count=(
            source_adapter_audit_report.selector_audit_required_count
        ),
        source_named_site_priority_plan=source_named_site_priority_plan,
        source_named_site_priority_plan_id=source_named_site_priority_plan.plan_id,
        source_named_site_priority_plan_row_count=source_named_site_priority_plan.row_count,
        source_named_site_priority_plan_approval_required_count=(
            source_named_site_priority_plan.approval_required_count
        ),
        release_readiness=release_readiness,
        release_readiness_id=release_readiness.release_readiness_id,
        release_target_count=release_readiness.target_count,
        release_action_plan=release_action_plan,
        release_action_plan_id=release_action_plan.release_action_plan_id,
        release_action_receipt_count=release_action_plan.receipt_count,
        operator_signoff_required=release_action_plan.operator_signoff_required,
        connection=connection,
        queue_review_store_document=store_document,
        review_manifest=review_manifest,
    )


def source_evidence_workflow_state_to_json(state: SourceEvidenceWorkflowState) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True)
