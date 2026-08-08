from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from evidence_item_queue_store import (
    read_evidence_item_queue_review_store,
    validate_evidence_item_queue_review_store_document,
)
from access_provider_gate import (
    access_provider_gate_summary_to_json,
    validate_access_provider_gate_summary,
)
from source_evidence_review_export import (
    build_source_evidence_review_manifest_with_workflow_state,
    source_evidence_review_manifest_to_json,
)
from source_evidence_release_readiness import (
    source_evidence_release_readiness_to_json,
    validate_source_evidence_release_readiness,
)
from source_evidence_release_plan import (
    source_evidence_release_action_plan_to_json,
    validate_source_evidence_release_action_plan,
)
from source_grabbed_record import grabbed_source_record_to_json, validate_grabbed_source_record
from source_adapter_audit_registry import (
    source_adapter_audit_registry_to_json,
    validate_source_adapter_audit_registry,
)
from source_adapter_audit_report import (
    source_adapter_audit_report_to_json,
    validate_source_adapter_audit_report,
)
from source_named_site_priority_plan import (
    source_named_site_priority_plan_to_json,
    validate_source_named_site_priority_plan,
)
from source_named_site_method_packs import (
    source_named_site_method_pack_collection_to_json,
    validate_source_named_site_method_pack_collection,
)
from source_operator_command_packs import (
    source_operator_command_pack_collection_to_json,
    validate_source_operator_command_pack_collection,
)
from source_manual_smoke_checklists import (
    source_manual_smoke_checklist_collection_to_json,
    validate_source_manual_smoke_checklist_collection,
)
from source_site_method_audit_registry import (
    source_site_method_audit_registry_to_json,
    validate_source_site_method_audit_registry,
)
from source_evidence_workflow_state import (
    SourceEvidenceWorkflowState,
    source_evidence_workflow_state_to_json,
)


SOURCE_EVIDENCE_WORKFLOW_STORE_SCHEMA_VERSION = "source_evidence_workflow_store_v1"
WORKFLOW_STATE_FILENAME = "source_evidence_workflow_state.json"
REVIEW_MANIFEST_FILENAME = "source_evidence_review_manifest.json"
QUEUE_REVIEW_STORE_FILENAME = "evidence_item_queue_review_store.json"
RELEASE_READINESS_FILENAME = "source_evidence_release_readiness.json"
RELEASE_ACTION_PLAN_FILENAME = "source_evidence_release_action_plan.json"
GRABBED_SOURCE_RECORD_FILENAME = "source_grabbed_record.json"
DATABASE_SCAN_RESULT_FILENAME = "source_evidence_database_scan_result.json"
ACCESS_PROVIDER_GATE_FILENAME = "source_access_provider_gate_summary.json"
SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME = "source_adapter_audit_registry.json"
SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME = "source_site_method_audit_registry.json"
SOURCE_ADAPTER_AUDIT_REPORT_FILENAME = "source_adapter_audit_report.json"
SOURCE_NAMED_SITE_PRIORITY_PLAN_FILENAME = "source_named_site_priority_plan.json"
SOURCE_NAMED_SITE_METHOD_PACKS_FILENAME = "source_named_site_method_packs.json"
SOURCE_DATABASE_REVIEW_WORKFLOW_FILENAME = "source_database_review_workflow.json"
SOURCE_RECORD_REVIEW_WORKFLOW_FILENAME = "source_record_review_workflow.json"
SOURCE_SELECTOR_APPROVAL_PACKETS_FILENAME = "source_selector_approval_packets.json"
SOURCE_OPERATOR_COMMAND_PACKS_FILENAME = "source_operator_command_packs.json"
SOURCE_MANUAL_SMOKE_CHECKLISTS_FILENAME = "source_manual_smoke_checklists.json"
SOURCE_AUDIT_DASHBOARD_STATE_FILENAME = "source_audit_dashboard_state.json"
SOURCE_OPERATIONAL_CAPTURE_RUNTIME_FILENAME = "source_operational_capture_runtime.json"
SOURCE_ARTICLE_CAPTURE_RESULTS_FILENAME = "source_article_capture_results.json"
SOURCE_SCREENSHOT_CAPTURE_RESULTS_FILENAME = "source_screenshot_capture_results.json"
SOURCE_COMMENTS_CAPTURE_RESULTS_FILENAME = "source_comments_capture_results.json"
SOURCE_LIVECHAT_CAPTURE_RESULTS_FILENAME = "source_livechat_capture_results.json"
SOURCE_MEDIA_DISCOVERY_RESULTS_FILENAME = "source_media_discovery_results.json"
SOURCE_ARCHIVE_PROVIDER_RESULTS_FILENAME = "source_archive_provider_results.json"
SOURCE_OFFLINE_BUNDLE_PLAN_FILENAME = "source_offline_bundle_plan.json"
SOURCE_EVIDENCE_MOVEMENT_PLAN_FILENAME = "source_evidence_movement_plan.json"
SOURCE_DATABASE_RECOGNITION_PLAN_FILENAME = "source_database_recognition_plan.json"
SOURCE_URL_FILES_BRIDGE_STATE_FILENAME = "source_url_files_bridge_state.json"
SOURCE_BEHAVIOR_PROVENANCE_LOG_FILENAME = "source_behavior_provenance_log.json"
SOURCE_EXECUTION_BRIDGE_RESULTS_FILENAME = "source_execution_bridge_results.json"
BUNDLE_INDEX_FILENAME = "source_evidence_workflow_review_bundle.json"


@dataclass(frozen=True)
class SourceEvidenceWorkflowStoredFile:
    file_role: str
    filename: str
    sha256: str
    size_bytes: int
    mime_type: str = "application/json"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceEvidenceWorkflowStoreResult:
    bundle_id: str
    created_at_utc: str
    files: tuple[SourceEvidenceWorkflowStoredFile, ...]
    payload_sha256: str = ""
    schema_version: str = SOURCE_EVIDENCE_WORKFLOW_STORE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    approval_required: bool = True
    explicit_user_selected_output_directory: bool = True
    metadata_file_write_performed: bool = True
    metadata_file_read_performed: bool = False
    evidence_file_read_performed: bool = False
    evidence_file_check_performed: bool = False
    evidence_file_move_performed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_fetch_or_api_call_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    release_upload_performed: bool = False
    file_library_publish_performed: bool = False
    operator_signoff_performed: bool = False
    completed_release_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    note: str = (
        "Writes Source Evidence review metadata sidecars only. Stored summaries use "
        "file names and content hashes, not full local paths or raw evidence payloads."
    )

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        payload = dict(data)
        payload["payload_sha256"] = ""
        data["payload_sha256"] = self.payload_sha256 or _payload_sha256(payload)
        data["file_count"] = self.file_count
        return data


@dataclass(frozen=True)
class SourceEvidenceWorkflowStoreReadResult:
    bundle: Mapping[str, Any]
    workflow_state: Mapping[str, Any]
    review_manifest: Mapping[str, Any]
    queue_review_store: Mapping[str, Any]
    release_readiness: Mapping[str, Any]
    release_action_plan: Mapping[str, Any]
    grabbed_source_record: Mapping[str, Any]
    database_scan_result: Mapping[str, Any]
    access_provider_gate_summary: Mapping[str, Any]
    source_adapter_audit_registry: Mapping[str, Any]
    source_site_method_audit_registry: Mapping[str, Any]
    source_adapter_audit_report: Mapping[str, Any]
    source_named_site_priority_plan: Mapping[str, Any]
    source_named_site_method_packs: Mapping[str, Any]
    source_database_review_workflow: Mapping[str, Any]
    source_record_review_workflow: Mapping[str, Any]
    source_selector_approval_packets: Mapping[str, Any]
    source_operator_command_packs: Mapping[str, Any]
    source_manual_smoke_checklists: Mapping[str, Any]
    source_audit_dashboard_state: Mapping[str, Any]
    source_operational_capture_runtime: Mapping[str, Any]
    source_article_capture_results: Mapping[str, Any]
    source_screenshot_capture_results: Mapping[str, Any]
    source_comments_capture_results: Mapping[str, Any]
    source_livechat_capture_results: Mapping[str, Any]
    source_media_discovery_results: Mapping[str, Any]
    source_archive_provider_results: Mapping[str, Any]
    source_offline_bundle_plan: Mapping[str, Any]
    source_evidence_movement_plan: Mapping[str, Any]
    source_database_recognition_plan: Mapping[str, Any]
    source_url_files_bridge_state: Mapping[str, Any]
    source_behavior_provenance_log: Mapping[str, Any]
    source_execution_bridge_results: Mapping[str, Any]
    schema_version: str = SOURCE_EVIDENCE_WORKFLOW_STORE_SCHEMA_VERSION
    metadata_file_read_performed: bool = True
    evidence_file_read_performed: bool = False
    evidence_file_move_performed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


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


def _payload_sha256(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_name = handle.name
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    try:
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _stored_file(file_role: str, filename: str, content: str) -> SourceEvidenceWorkflowStoredFile:
    encoded = content.encode("utf-8")
    return SourceEvidenceWorkflowStoredFile(
        file_role=file_role,
        filename=filename,
        sha256=hashlib.sha256(encoded).hexdigest(),
        size_bytes=len(encoded),
    )


def _result_payload_for_hash(result: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    payload["payload_sha256"] = ""
    payload.pop("file_count", None)
    return payload


def validate_source_evidence_workflow_store_result(result: Mapping[str, Any]) -> None:
    if result.get("schema_version") != SOURCE_EVIDENCE_WORKFLOW_STORE_SCHEMA_VERSION:
        raise ValueError("Unsupported Source Evidence workflow store schema version")
    for required_true in (
        "metadata_only",
        "local_only",
        "approval_required",
        "explicit_user_selected_output_directory",
        "metadata_file_write_performed",
        "sensitive_inference_prohibited",
    ):
        if result.get(required_true) is not True:
            raise ValueError(f"Unsafe Source Evidence workflow store flag: {required_true}")
    for required_false in (
        "evidence_file_read_performed",
        "evidence_file_check_performed",
        "evidence_file_move_performed",
        "file_existence_claimed",
        "full_local_path_included",
        "raw_payload_included",
        "completed_evidence_claimed",
        "verified_evidence_claimed",
        "live_fetch_or_api_call_performed",
        "browser_automation_performed",
        "archive_provider_call_performed",
        "download_performed",
        "release_upload_performed",
        "file_library_publish_performed",
        "operator_signoff_performed",
        "completed_release_claimed",
        "automatic_classification",
    ):
        if result.get(required_false) is not False:
            raise ValueError(f"Unsafe Source Evidence workflow store flag: {required_false}")
    expected_hash = str(result.get("payload_sha256", ""))
    actual_hash = _payload_sha256(_result_payload_for_hash(result))
    if expected_hash != actual_hash:
        raise ValueError("Source Evidence workflow store hash mismatch")


def build_source_evidence_workflow_store_result(
    *,
    state: SourceEvidenceWorkflowState,
    files: tuple[SourceEvidenceWorkflowStoredFile, ...],
) -> SourceEvidenceWorkflowStoreResult:
    payload = {
        "created_at_utc": state.review_manifest.created_at_utc,
        "execution_gate_plan_id": state.execution_gate_plan_id,
        "files": [file.to_dict() for file in files],
        "queue_review_store_id": state.queue_review_store_id,
        "review_manifest_package_id": state.review_manifest_package_id,
        "schema_version": SOURCE_EVIDENCE_WORKFLOW_STORE_SCHEMA_VERSION,
        "source_row_id": state.source_row_id,
    }
    bundle_id = "source_evidence_workflow_store_" + _payload_sha256(payload)[:16]
    result = SourceEvidenceWorkflowStoreResult(
        bundle_id=bundle_id,
        created_at_utc=state.review_manifest.created_at_utc,
        files=files,
    )
    return SourceEvidenceWorkflowStoreResult(
        **{
            **result.__dict__,
            "payload_sha256": result.to_dict()["payload_sha256"],
        }
    )


def write_source_evidence_workflow_review_bundle(
    state: SourceEvidenceWorkflowState,
    output_directory: str | os.PathLike[str],
) -> SourceEvidenceWorkflowStoreResult:
    """Persist a metadata-only review bundle for an app-selected workflow state.

    This writes review sidecars into a caller-selected directory. It does not read,
    check, move, or claim any underlying evidence files.
    """
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)

    workflow_state_json = source_evidence_workflow_state_to_json(state)
    release_readiness = state.release_readiness.to_dict()
    validate_source_evidence_release_readiness(release_readiness)
    release_readiness_json = source_evidence_release_readiness_to_json(state.release_readiness)
    release_action_plan = state.release_action_plan.to_dict()
    validate_source_evidence_release_action_plan(release_action_plan)
    release_action_plan_json = source_evidence_release_action_plan_to_json(state.release_action_plan)
    grabbed_source_record = state.grabbed_source_record.to_dict() if state.grabbed_source_record is not None else {}
    if grabbed_source_record:
        validate_grabbed_source_record(grabbed_source_record)
        grabbed_source_record_json = grabbed_source_record_to_json(state.grabbed_source_record)
    else:
        grabbed_source_record_json = _stable_json({}, pretty=True)
    database_scan_result = state.database_scan_result.to_dict()
    database_scan_result_json = _stable_json(database_scan_result, pretty=True)
    access_provider_gate_summary = state.access_provider_gate_summary.to_dict()
    validate_access_provider_gate_summary(access_provider_gate_summary)
    access_provider_gate_json = access_provider_gate_summary_to_json(
        state.access_provider_gate_summary
    )
    source_adapter_audit_registry = state.source_adapter_audit_registry.to_dict()
    validate_source_adapter_audit_registry(source_adapter_audit_registry)
    source_adapter_audit_registry_json = source_adapter_audit_registry_to_json(
        state.source_adapter_audit_registry
    )
    source_site_method_audit_registry = state.source_site_method_audit_registry.to_dict()
    validate_source_site_method_audit_registry(source_site_method_audit_registry)
    source_site_method_audit_registry_json = source_site_method_audit_registry_to_json(
        state.source_site_method_audit_registry
    )
    source_adapter_audit_report = state.source_adapter_audit_report.to_dict()
    validate_source_adapter_audit_report(source_adapter_audit_report)
    source_adapter_audit_report_json = source_adapter_audit_report_to_json(
        state.source_adapter_audit_report
    )
    source_named_site_priority_plan = state.source_named_site_priority_plan.to_dict()
    validate_source_named_site_priority_plan(source_named_site_priority_plan)
    source_named_site_priority_plan_json = source_named_site_priority_plan_to_json(
        state.source_named_site_priority_plan
    )
    source_named_site_method_packs = state.source_named_site_method_packs.to_dict()
    validate_source_named_site_method_pack_collection(source_named_site_method_packs)
    source_named_site_method_packs_json = source_named_site_method_pack_collection_to_json(
        state.source_named_site_method_packs
    )
    source_database_review_workflow = state.source_database_review_workflow.to_dict()
    source_database_review_workflow_json = _stable_json(source_database_review_workflow, pretty=True)
    source_record_review_workflow = state.source_record_review_workflow.to_dict()
    source_record_review_workflow_json = _stable_json(source_record_review_workflow, pretty=True)
    source_selector_approval_packets = state.source_selector_approval_packets.to_dict()
    source_selector_approval_packets_json = _stable_json(source_selector_approval_packets, pretty=True)
    source_operator_command_packs = state.source_operator_command_packs.to_dict()
    validate_source_operator_command_pack_collection(source_operator_command_packs)
    source_operator_command_packs_json = source_operator_command_pack_collection_to_json(
        state.source_operator_command_packs
    )
    source_manual_smoke_checklists = state.source_manual_smoke_checklists.to_dict()
    validate_source_manual_smoke_checklist_collection(source_manual_smoke_checklists)
    source_manual_smoke_checklists_json = source_manual_smoke_checklist_collection_to_json(
        state.source_manual_smoke_checklists
    )
    source_audit_dashboard_state = state.source_audit_dashboard_state.to_dict()
    source_audit_dashboard_state_json = _stable_json(source_audit_dashboard_state, pretty=True)
    source_operational_capture_runtime = _value_for_dict(state.source_operational_capture_runtime)
    source_operational_capture_runtime_json = _stable_json(source_operational_capture_runtime, pretty=True)
    source_article_capture_results = {
        "schema_version": "source_article_capture_results_v1",
        "article_result": state.source_fixture_capture_results["article_result"],
        "page_outline_result": state.source_fixture_capture_results["page_outline_result"],
        "no_live_execution": True,
    }
    source_article_capture_results_json = _stable_json(source_article_capture_results, pretty=True)
    source_screenshot_capture_results = {
        "schema_version": "source_screenshot_capture_results_v1",
        "screenshot_results": state.source_fixture_capture_results["screenshot_results"],
        "screenshots_taken": False,
        "no_live_execution": True,
    }
    source_screenshot_capture_results_json = _stable_json(source_screenshot_capture_results, pretty=True)
    source_comments_capture_results = {
        "schema_version": "source_comments_capture_results_v1",
        "comments_result": state.source_fixture_capture_results["comments_result"],
        "virtualized_comment_checkpoint": state.source_fixture_capture_results[
            "virtualized_comment_checkpoint"
        ],
        "encoded_payload_results": state.source_fixture_capture_results["encoded_payload_results"],
        "challenge_states": state.source_fixture_capture_results["challenge_states"],
        "no_live_execution": True,
    }
    source_comments_capture_results_json = _stable_json(source_comments_capture_results, pretty=True)
    source_livechat_capture_results = {
        "schema_version": "source_livechat_capture_results_v1",
        "livechat_result": state.source_fixture_capture_results["livechat_result"],
        "screenshots_default_on": False,
        "no_live_execution": True,
    }
    source_livechat_capture_results_json = _stable_json(source_livechat_capture_results, pretty=True)
    source_media_discovery_results = {
        "schema_version": "source_media_discovery_results_v1",
        "media_discovery_result": state.source_media_archive_runtime["media_discovery_result"],
        "mux_plan": state.source_media_archive_runtime["mux_plan"],
        "rendered_citation_plan": state.source_media_archive_runtime["rendered_citation_plan"],
        "protected_output_result": state.source_media_archive_runtime["protected_output_result"],
        "no_download_or_mux_execution": True,
    }
    source_media_discovery_results_json = _stable_json(source_media_discovery_results, pretty=True)
    source_archive_provider_results = {
        "schema_version": "source_archive_provider_results_v1",
        "archive_provider_results": state.source_media_archive_runtime["archive_provider_results"],
        "provider_call_performed": False,
        "submission_performed": False,
    }
    source_archive_provider_results_json = _stable_json(source_archive_provider_results, pretty=True)
    source_offline_bundle_plan = {
        "schema_version": "source_offline_bundle_plan_v1",
        "offline_bundle_plan": state.source_media_archive_runtime["offline_bundle_plan"],
        "archivebox_command_plans": state.source_media_archive_runtime["archivebox_command_plans"],
        "archivebox_executed": False,
    }
    source_offline_bundle_plan_json = _stable_json(source_offline_bundle_plan, pretty=True)
    source_evidence_movement_plan = _value_for_dict(state.source_evidence_movement_plan)
    source_evidence_movement_plan_json = _stable_json(source_evidence_movement_plan, pretty=True)
    source_database_recognition_plan = _value_for_dict(state.source_database_recognition_plan)
    source_database_recognition_plan_json = _stable_json(source_database_recognition_plan, pretty=True)
    source_url_files_bridge_state = _value_for_dict(state.source_url_files_bridge_state)
    source_url_files_bridge_state_json = _stable_json(source_url_files_bridge_state, pretty=True)
    source_behavior_provenance_log = _value_for_dict(state.source_behavior_provenance_log)
    source_behavior_provenance_log_json = _stable_json(source_behavior_provenance_log, pretty=True)
    source_execution_bridge_results = _value_for_dict(state.source_execution_bridge_results)
    source_execution_bridge_results_json = _stable_json(source_execution_bridge_results, pretty=True)
    review_manifest = build_source_evidence_review_manifest_with_workflow_state(
        state.review_manifest,
        workflow_state_metadata=state.to_dict(),
        release_readiness_metadata=release_readiness,
        source_adapter_audit_registry_metadata=source_adapter_audit_registry,
        source_site_method_audit_registry_metadata=source_site_method_audit_registry,
        source_adapter_audit_report_metadata=source_adapter_audit_report,
        source_named_site_priority_plan_metadata=source_named_site_priority_plan,
        source_named_site_method_packs_metadata=source_named_site_method_packs,
        source_database_review_workflow_metadata=source_database_review_workflow,
        source_record_review_workflow_metadata=source_record_review_workflow,
        source_selector_approval_packets_metadata=source_selector_approval_packets,
        source_operator_command_packs_metadata=source_operator_command_packs,
        source_manual_smoke_checklists_metadata=source_manual_smoke_checklists,
        source_audit_dashboard_state_metadata=source_audit_dashboard_state,
        source_operational_capture_runtime_metadata=source_operational_capture_runtime,
        source_article_capture_results_metadata=source_article_capture_results,
        source_screenshot_capture_results_metadata=source_screenshot_capture_results,
        source_comments_capture_results_metadata=source_comments_capture_results,
        source_livechat_capture_results_metadata=source_livechat_capture_results,
        source_media_discovery_results_metadata=source_media_discovery_results,
        source_archive_provider_results_metadata=source_archive_provider_results,
        source_offline_bundle_plan_metadata=source_offline_bundle_plan,
        source_evidence_movement_plan_metadata=source_evidence_movement_plan,
        source_database_recognition_plan_metadata=source_database_recognition_plan,
        source_url_files_bridge_state_metadata=source_url_files_bridge_state,
        source_behavior_provenance_log_metadata=source_behavior_provenance_log,
        source_execution_bridge_results_metadata=source_execution_bridge_results,
    )
    review_manifest_json = source_evidence_review_manifest_to_json(review_manifest)
    queue_review_store = state.queue_review_store_document.to_dict()
    validate_evidence_item_queue_review_store_document(queue_review_store)
    queue_review_store_json = _stable_json(queue_review_store, pretty=True)

    files = (
        _stored_file("workflow_state", WORKFLOW_STATE_FILENAME, workflow_state_json),
        _stored_file("review_manifest", REVIEW_MANIFEST_FILENAME, review_manifest_json),
        _stored_file("queue_review_store", QUEUE_REVIEW_STORE_FILENAME, queue_review_store_json),
        _stored_file("release_readiness", RELEASE_READINESS_FILENAME, release_readiness_json),
        _stored_file("release_action_plan", RELEASE_ACTION_PLAN_FILENAME, release_action_plan_json),
        _stored_file("grabbed_source_record", GRABBED_SOURCE_RECORD_FILENAME, grabbed_source_record_json),
        _stored_file("database_scan_result", DATABASE_SCAN_RESULT_FILENAME, database_scan_result_json),
        _stored_file("access_provider_gate", ACCESS_PROVIDER_GATE_FILENAME, access_provider_gate_json),
        _stored_file(
            "source_adapter_audit_registry",
            SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME,
            source_adapter_audit_registry_json,
        ),
        _stored_file(
            "source_site_method_audit_registry",
            SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME,
            source_site_method_audit_registry_json,
        ),
        _stored_file(
            "source_adapter_audit_report",
            SOURCE_ADAPTER_AUDIT_REPORT_FILENAME,
            source_adapter_audit_report_json,
        ),
        _stored_file(
            "source_named_site_priority_plan",
            SOURCE_NAMED_SITE_PRIORITY_PLAN_FILENAME,
            source_named_site_priority_plan_json,
        ),
        _stored_file(
            "source_named_site_method_packs",
            SOURCE_NAMED_SITE_METHOD_PACKS_FILENAME,
            source_named_site_method_packs_json,
        ),
        _stored_file(
            "source_database_review_workflow",
            SOURCE_DATABASE_REVIEW_WORKFLOW_FILENAME,
            source_database_review_workflow_json,
        ),
        _stored_file(
            "source_record_review_workflow",
            SOURCE_RECORD_REVIEW_WORKFLOW_FILENAME,
            source_record_review_workflow_json,
        ),
        _stored_file(
            "source_selector_approval_packets",
            SOURCE_SELECTOR_APPROVAL_PACKETS_FILENAME,
            source_selector_approval_packets_json,
        ),
        _stored_file(
            "source_operator_command_packs",
            SOURCE_OPERATOR_COMMAND_PACKS_FILENAME,
            source_operator_command_packs_json,
        ),
        _stored_file(
            "source_manual_smoke_checklists",
            SOURCE_MANUAL_SMOKE_CHECKLISTS_FILENAME,
            source_manual_smoke_checklists_json,
        ),
        _stored_file(
            "source_audit_dashboard_state",
            SOURCE_AUDIT_DASHBOARD_STATE_FILENAME,
            source_audit_dashboard_state_json,
        ),
        _stored_file("source_operational_capture_runtime", SOURCE_OPERATIONAL_CAPTURE_RUNTIME_FILENAME, source_operational_capture_runtime_json),
        _stored_file("source_article_capture_results", SOURCE_ARTICLE_CAPTURE_RESULTS_FILENAME, source_article_capture_results_json),
        _stored_file("source_screenshot_capture_results", SOURCE_SCREENSHOT_CAPTURE_RESULTS_FILENAME, source_screenshot_capture_results_json),
        _stored_file("source_comments_capture_results", SOURCE_COMMENTS_CAPTURE_RESULTS_FILENAME, source_comments_capture_results_json),
        _stored_file("source_livechat_capture_results", SOURCE_LIVECHAT_CAPTURE_RESULTS_FILENAME, source_livechat_capture_results_json),
        _stored_file("source_media_discovery_results", SOURCE_MEDIA_DISCOVERY_RESULTS_FILENAME, source_media_discovery_results_json),
        _stored_file("source_archive_provider_results", SOURCE_ARCHIVE_PROVIDER_RESULTS_FILENAME, source_archive_provider_results_json),
        _stored_file("source_offline_bundle_plan", SOURCE_OFFLINE_BUNDLE_PLAN_FILENAME, source_offline_bundle_plan_json),
        _stored_file("source_evidence_movement_plan", SOURCE_EVIDENCE_MOVEMENT_PLAN_FILENAME, source_evidence_movement_plan_json),
        _stored_file("source_database_recognition_plan", SOURCE_DATABASE_RECOGNITION_PLAN_FILENAME, source_database_recognition_plan_json),
        _stored_file("source_url_files_bridge_state", SOURCE_URL_FILES_BRIDGE_STATE_FILENAME, source_url_files_bridge_state_json),
        _stored_file("source_behavior_provenance_log", SOURCE_BEHAVIOR_PROVENANCE_LOG_FILENAME, source_behavior_provenance_log_json),
        _stored_file("source_execution_bridge_results", SOURCE_EXECUTION_BRIDGE_RESULTS_FILENAME, source_execution_bridge_results_json),
    )
    result = build_source_evidence_workflow_store_result(state=state, files=files)
    result_json = source_evidence_workflow_store_result_to_json(result)

    _atomic_write_text(output_root / WORKFLOW_STATE_FILENAME, workflow_state_json)
    _atomic_write_text(output_root / REVIEW_MANIFEST_FILENAME, review_manifest_json)
    _atomic_write_text(output_root / QUEUE_REVIEW_STORE_FILENAME, queue_review_store_json)
    _atomic_write_text(output_root / RELEASE_READINESS_FILENAME, release_readiness_json)
    _atomic_write_text(output_root / RELEASE_ACTION_PLAN_FILENAME, release_action_plan_json)
    _atomic_write_text(output_root / GRABBED_SOURCE_RECORD_FILENAME, grabbed_source_record_json)
    _atomic_write_text(output_root / DATABASE_SCAN_RESULT_FILENAME, database_scan_result_json)
    _atomic_write_text(output_root / ACCESS_PROVIDER_GATE_FILENAME, access_provider_gate_json)
    _atomic_write_text(
        output_root / SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME,
        source_adapter_audit_registry_json,
    )
    _atomic_write_text(
        output_root / SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME,
        source_site_method_audit_registry_json,
    )
    _atomic_write_text(
        output_root / SOURCE_ADAPTER_AUDIT_REPORT_FILENAME,
        source_adapter_audit_report_json,
    )
    _atomic_write_text(
        output_root / SOURCE_NAMED_SITE_PRIORITY_PLAN_FILENAME,
        source_named_site_priority_plan_json,
    )
    _atomic_write_text(
        output_root / SOURCE_NAMED_SITE_METHOD_PACKS_FILENAME,
        source_named_site_method_packs_json,
    )
    _atomic_write_text(
        output_root / SOURCE_DATABASE_REVIEW_WORKFLOW_FILENAME,
        source_database_review_workflow_json,
    )
    _atomic_write_text(
        output_root / SOURCE_RECORD_REVIEW_WORKFLOW_FILENAME,
        source_record_review_workflow_json,
    )
    _atomic_write_text(
        output_root / SOURCE_SELECTOR_APPROVAL_PACKETS_FILENAME,
        source_selector_approval_packets_json,
    )
    _atomic_write_text(
        output_root / SOURCE_OPERATOR_COMMAND_PACKS_FILENAME,
        source_operator_command_packs_json,
    )
    _atomic_write_text(
        output_root / SOURCE_MANUAL_SMOKE_CHECKLISTS_FILENAME,
        source_manual_smoke_checklists_json,
    )
    _atomic_write_text(
        output_root / SOURCE_AUDIT_DASHBOARD_STATE_FILENAME,
        source_audit_dashboard_state_json,
    )
    _atomic_write_text(output_root / SOURCE_OPERATIONAL_CAPTURE_RUNTIME_FILENAME, source_operational_capture_runtime_json)
    _atomic_write_text(output_root / SOURCE_ARTICLE_CAPTURE_RESULTS_FILENAME, source_article_capture_results_json)
    _atomic_write_text(output_root / SOURCE_SCREENSHOT_CAPTURE_RESULTS_FILENAME, source_screenshot_capture_results_json)
    _atomic_write_text(output_root / SOURCE_COMMENTS_CAPTURE_RESULTS_FILENAME, source_comments_capture_results_json)
    _atomic_write_text(output_root / SOURCE_LIVECHAT_CAPTURE_RESULTS_FILENAME, source_livechat_capture_results_json)
    _atomic_write_text(output_root / SOURCE_MEDIA_DISCOVERY_RESULTS_FILENAME, source_media_discovery_results_json)
    _atomic_write_text(output_root / SOURCE_ARCHIVE_PROVIDER_RESULTS_FILENAME, source_archive_provider_results_json)
    _atomic_write_text(output_root / SOURCE_OFFLINE_BUNDLE_PLAN_FILENAME, source_offline_bundle_plan_json)
    _atomic_write_text(output_root / SOURCE_EVIDENCE_MOVEMENT_PLAN_FILENAME, source_evidence_movement_plan_json)
    _atomic_write_text(output_root / SOURCE_DATABASE_RECOGNITION_PLAN_FILENAME, source_database_recognition_plan_json)
    _atomic_write_text(output_root / SOURCE_URL_FILES_BRIDGE_STATE_FILENAME, source_url_files_bridge_state_json)
    _atomic_write_text(output_root / SOURCE_BEHAVIOR_PROVENANCE_LOG_FILENAME, source_behavior_provenance_log_json)
    _atomic_write_text(output_root / SOURCE_EXECUTION_BRIDGE_RESULTS_FILENAME, source_execution_bridge_results_json)
    _atomic_write_text(output_root / BUNDLE_INDEX_FILENAME, result_json)
    return result


def read_source_evidence_workflow_review_bundle(
    input_directory: str | os.PathLike[str],
) -> SourceEvidenceWorkflowStoreReadResult:
    input_root = Path(input_directory)
    bundle = json.loads((input_root / BUNDLE_INDEX_FILENAME).read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        raise ValueError("Source Evidence workflow store bundle index must be a JSON object")
    validate_source_evidence_workflow_store_result(bundle)
    workflow_state = json.loads((input_root / WORKFLOW_STATE_FILENAME).read_text(encoding="utf-8"))
    review_manifest = json.loads((input_root / REVIEW_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    queue_review_store = read_evidence_item_queue_review_store(input_root / QUEUE_REVIEW_STORE_FILENAME)
    release_readiness = json.loads((input_root / RELEASE_READINESS_FILENAME).read_text(encoding="utf-8"))
    release_action_plan = json.loads((input_root / RELEASE_ACTION_PLAN_FILENAME).read_text(encoding="utf-8"))
    grabbed_source_record = json.loads((input_root / GRABBED_SOURCE_RECORD_FILENAME).read_text(encoding="utf-8"))
    database_scan_result = json.loads((input_root / DATABASE_SCAN_RESULT_FILENAME).read_text(encoding="utf-8"))
    access_provider_gate_summary = json.loads((input_root / ACCESS_PROVIDER_GATE_FILENAME).read_text(encoding="utf-8"))
    source_adapter_audit_registry = json.loads(
        (input_root / SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME).read_text(encoding="utf-8")
    )
    source_site_method_audit_registry = json.loads(
        (input_root / SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME).read_text(encoding="utf-8")
    )
    source_adapter_audit_report = json.loads(
        (input_root / SOURCE_ADAPTER_AUDIT_REPORT_FILENAME).read_text(encoding="utf-8")
    )
    source_named_site_priority_plan = json.loads(
        (input_root / SOURCE_NAMED_SITE_PRIORITY_PLAN_FILENAME).read_text(encoding="utf-8")
    )
    source_named_site_method_packs = json.loads(
        (input_root / SOURCE_NAMED_SITE_METHOD_PACKS_FILENAME).read_text(encoding="utf-8")
    )
    source_database_review_workflow = json.loads(
        (input_root / SOURCE_DATABASE_REVIEW_WORKFLOW_FILENAME).read_text(encoding="utf-8")
    )
    source_record_review_workflow = json.loads(
        (input_root / SOURCE_RECORD_REVIEW_WORKFLOW_FILENAME).read_text(encoding="utf-8")
    )
    source_selector_approval_packets = json.loads(
        (input_root / SOURCE_SELECTOR_APPROVAL_PACKETS_FILENAME).read_text(encoding="utf-8")
    )
    source_operator_command_packs = json.loads(
        (input_root / SOURCE_OPERATOR_COMMAND_PACKS_FILENAME).read_text(encoding="utf-8")
    )
    source_manual_smoke_checklists = json.loads(
        (input_root / SOURCE_MANUAL_SMOKE_CHECKLISTS_FILENAME).read_text(encoding="utf-8")
    )
    source_audit_dashboard_state = json.loads(
        (input_root / SOURCE_AUDIT_DASHBOARD_STATE_FILENAME).read_text(encoding="utf-8")
    )
    source_operational_capture_runtime = json.loads(
        (input_root / SOURCE_OPERATIONAL_CAPTURE_RUNTIME_FILENAME).read_text(encoding="utf-8")
    )
    source_article_capture_results = json.loads(
        (input_root / SOURCE_ARTICLE_CAPTURE_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_screenshot_capture_results = json.loads(
        (input_root / SOURCE_SCREENSHOT_CAPTURE_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_comments_capture_results = json.loads(
        (input_root / SOURCE_COMMENTS_CAPTURE_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_livechat_capture_results = json.loads(
        (input_root / SOURCE_LIVECHAT_CAPTURE_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_media_discovery_results = json.loads(
        (input_root / SOURCE_MEDIA_DISCOVERY_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_archive_provider_results = json.loads(
        (input_root / SOURCE_ARCHIVE_PROVIDER_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    source_offline_bundle_plan = json.loads(
        (input_root / SOURCE_OFFLINE_BUNDLE_PLAN_FILENAME).read_text(encoding="utf-8")
    )
    source_evidence_movement_plan = json.loads(
        (input_root / SOURCE_EVIDENCE_MOVEMENT_PLAN_FILENAME).read_text(encoding="utf-8")
    )
    source_database_recognition_plan = json.loads(
        (input_root / SOURCE_DATABASE_RECOGNITION_PLAN_FILENAME).read_text(encoding="utf-8")
    )
    source_url_files_bridge_state = json.loads(
        (input_root / SOURCE_URL_FILES_BRIDGE_STATE_FILENAME).read_text(encoding="utf-8")
    )
    source_behavior_provenance_log = json.loads(
        (input_root / SOURCE_BEHAVIOR_PROVENANCE_LOG_FILENAME).read_text(encoding="utf-8")
    )
    source_execution_bridge_results = json.loads(
        (input_root / SOURCE_EXECUTION_BRIDGE_RESULTS_FILENAME).read_text(encoding="utf-8")
    )
    if not isinstance(workflow_state, dict) or not isinstance(review_manifest, dict):
        raise ValueError("Source Evidence workflow bundle sidecars must be JSON objects")
    if not isinstance(release_readiness, dict):
        raise ValueError("Source Evidence release readiness sidecar must be a JSON object")
    validate_source_evidence_release_readiness(release_readiness)
    if not isinstance(release_action_plan, dict):
        raise ValueError("Source Evidence release action plan sidecar must be a JSON object")
    validate_source_evidence_release_action_plan(release_action_plan)
    if not isinstance(grabbed_source_record, dict) or not isinstance(database_scan_result, dict):
        raise ValueError("Source Evidence grabbed source/database scan sidecars must be JSON objects")
    if grabbed_source_record:
        validate_grabbed_source_record(grabbed_source_record)
    if not isinstance(access_provider_gate_summary, dict):
        raise ValueError("Source Evidence access provider gate sidecar must be a JSON object")
    validate_access_provider_gate_summary(access_provider_gate_summary)
    if not isinstance(source_adapter_audit_registry, dict):
        raise ValueError("Source Evidence adapter audit registry sidecar must be a JSON object")
    validate_source_adapter_audit_registry(source_adapter_audit_registry)
    if not isinstance(source_site_method_audit_registry, dict):
        raise ValueError("Source Evidence site/method audit registry sidecar must be a JSON object")
    validate_source_site_method_audit_registry(source_site_method_audit_registry)
    if not isinstance(source_adapter_audit_report, dict):
        raise ValueError("Source Evidence adapter audit report sidecar must be a JSON object")
    validate_source_adapter_audit_report(source_adapter_audit_report)
    if not isinstance(source_named_site_priority_plan, dict):
        raise ValueError("Source Evidence named-site priority plan sidecar must be a JSON object")
    validate_source_named_site_priority_plan(source_named_site_priority_plan)
    if not isinstance(source_named_site_method_packs, dict):
        raise ValueError("Source Evidence named-site method packs sidecar must be a JSON object")
    validate_source_named_site_method_pack_collection(source_named_site_method_packs)
    if not isinstance(source_database_review_workflow, dict):
        raise ValueError("Source Evidence database review workflow sidecar must be a JSON object")
    if not isinstance(source_record_review_workflow, dict):
        raise ValueError("Source Evidence source record review workflow sidecar must be a JSON object")
    if not isinstance(source_selector_approval_packets, dict):
        raise ValueError("Source Evidence selector approval packets sidecar must be a JSON object")
    if not isinstance(source_operator_command_packs, dict):
        raise ValueError("Source Evidence operator command packs sidecar must be a JSON object")
    validate_source_operator_command_pack_collection(source_operator_command_packs)
    if not isinstance(source_manual_smoke_checklists, dict):
        raise ValueError("Source Evidence manual smoke checklists sidecar must be a JSON object")
    validate_source_manual_smoke_checklist_collection(source_manual_smoke_checklists)
    if not isinstance(source_audit_dashboard_state, dict):
        raise ValueError("Source Evidence audit dashboard state sidecar must be a JSON object")
    for label, payload in (
        ("operational capture runtime", source_operational_capture_runtime),
        ("article capture results", source_article_capture_results),
        ("screenshot capture results", source_screenshot_capture_results),
        ("comments capture results", source_comments_capture_results),
        ("livechat capture results", source_livechat_capture_results),
        ("media discovery results", source_media_discovery_results),
        ("archive provider results", source_archive_provider_results),
        ("offline bundle plan", source_offline_bundle_plan),
        ("evidence movement plan", source_evidence_movement_plan),
        ("database recognition plan", source_database_recognition_plan),
        ("URL/FILES bridge state", source_url_files_bridge_state),
        ("behavior provenance log", source_behavior_provenance_log),
        ("execution bridge results", source_execution_bridge_results),
    ):
        if not isinstance(payload, dict):
            raise ValueError(f"Source Evidence {label} sidecar must be a JSON object")
    return SourceEvidenceWorkflowStoreReadResult(
        bundle=bundle,
        workflow_state=workflow_state,
        review_manifest=review_manifest,
        queue_review_store=queue_review_store,
        release_readiness=release_readiness,
        release_action_plan=release_action_plan,
        grabbed_source_record=grabbed_source_record,
        database_scan_result=database_scan_result,
        access_provider_gate_summary=access_provider_gate_summary,
        source_adapter_audit_registry=source_adapter_audit_registry,
        source_site_method_audit_registry=source_site_method_audit_registry,
        source_adapter_audit_report=source_adapter_audit_report,
        source_named_site_priority_plan=source_named_site_priority_plan,
        source_named_site_method_packs=source_named_site_method_packs,
        source_database_review_workflow=source_database_review_workflow,
        source_record_review_workflow=source_record_review_workflow,
        source_selector_approval_packets=source_selector_approval_packets,
        source_operator_command_packs=source_operator_command_packs,
        source_manual_smoke_checklists=source_manual_smoke_checklists,
        source_audit_dashboard_state=source_audit_dashboard_state,
        source_operational_capture_runtime=source_operational_capture_runtime,
        source_article_capture_results=source_article_capture_results,
        source_screenshot_capture_results=source_screenshot_capture_results,
        source_comments_capture_results=source_comments_capture_results,
        source_livechat_capture_results=source_livechat_capture_results,
        source_media_discovery_results=source_media_discovery_results,
        source_archive_provider_results=source_archive_provider_results,
        source_offline_bundle_plan=source_offline_bundle_plan,
        source_evidence_movement_plan=source_evidence_movement_plan,
        source_database_recognition_plan=source_database_recognition_plan,
        source_url_files_bridge_state=source_url_files_bridge_state,
        source_behavior_provenance_log=source_behavior_provenance_log,
        source_execution_bridge_results=source_execution_bridge_results,
    )


def source_evidence_workflow_store_result_to_json(
    result: SourceEvidenceWorkflowStoreResult,
) -> str:
    return _stable_json(result.to_dict(), pretty=True)
