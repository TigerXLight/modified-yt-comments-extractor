from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


SOURCE_REVIEW_PANEL_STATE_SCHEMA_VERSION = "source_review_panel_state_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _as_dict(value: Any) -> dict[str, Any]:
    data = _value_for_dict(value)
    return data if isinstance(data, dict) else {}


def _tuple_of_dicts(values: Any) -> tuple[Mapping[str, Any], ...]:
    result: list[Mapping[str, Any]] = []
    for item in tuple(values or ()):
        data = _as_dict(item)
        if data:
            result.append(data)
    return tuple(result)


@dataclass(frozen=True)
class SourceReviewPanelState:
    panel_id: str
    panel_kind: str
    title: str
    summary: Mapping[str, Any]
    rows: tuple[Mapping[str, Any], ...] = ()
    selected_row_state: Mapping[str, Any] | None = None
    pending_safe_edit_preview: Mapping[str, Any] | None = None
    rejected_unsafe_edit_preview: Mapping[str, Any] | None = None
    receipt_summary_rows: tuple[Mapping[str, Any], ...] = ()
    sidecar_file_summary: tuple[Mapping[str, Any], ...] = ()
    no_live_execution_status: str = "no_live_execution_performed"
    schema_version: str = SOURCE_REVIEW_PANEL_STATE_SCHEMA_VERSION
    metadata_only: bool = True
    user_review_required: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def receipt_summary_row_count(self) -> int:
        return len(self.receipt_summary_rows)

    @property
    def sidecar_file_count(self) -> int:
        return len(self.sidecar_file_summary)

    def to_dict(self) -> dict[str, Any]:
        data = {key: _value_for_dict(item) for key, item in asdict(self).items()}
        data["row_count"] = self.row_count
        data["receipt_summary_row_count"] = self.receipt_summary_row_count
        data["sidecar_file_count"] = self.sidecar_file_count
        return data


def _stored_file_rows(store_result: Any | None) -> tuple[Mapping[str, Any], ...]:
    if store_result is None:
        return ()
    return tuple(
        {
            "file_role": str(getattr(file, "file_role", "")),
            "filename": str(getattr(file, "filename", "")),
            "sha256": str(getattr(file, "sha256", "")),
            "size_bytes": int(getattr(file, "size_bytes", 0) or 0),
            "metadata_only": True,
            "full_local_path_included": False,
        }
        for file in tuple(getattr(store_result, "files", ()) or ())
    )


def build_database_review_panel_state(
    database_review_workflow: Any,
    *,
    store_result: Any | None = None,
    edit_preview: Any | None = None,
) -> SourceReviewPanelState:
    workflow = _as_dict(database_review_workflow)
    preview = _as_dict(edit_preview)
    accepted_preview = preview if preview.get("accepted_for_preview") is True else None
    rejected_preview = preview if preview.get("accepted_for_preview") is False else None
    summary = {
        "database_review_summary": workflow.get("bridge_summary", {}),
        "scan_count": workflow.get("scan_row_count", 0),
        "review_needed_count": workflow.get("review_needed_row_count", 0),
        "safe_edit_pending_count": workflow.get("pending_safe_edit_count", 0)
        + (1 if accepted_preview else 0),
        "rejected_unsafe_edit_count": workflow.get("rejected_unsafe_edit_count", 0)
        + (1 if rejected_preview else 0),
        "receipt_summary_row_count": workflow.get("receipt_summary_row_count", 0)
        + (1 if accepted_preview and accepted_preview.get("receipt_summary_row") else 0),
        "no_live_execution_status": "no_live_execution_performed",
    }
    return SourceReviewPanelState(
        panel_id="source_database_review_panel_" + _sha16((workflow.get("view_model_id"), preview)),
        panel_kind="database_review",
        title="Database Review",
        summary=summary,
        rows=_tuple_of_dicts(workflow.get("scan_rows")),
        selected_row_state=workflow.get("selected_row_state") or None,
        pending_safe_edit_preview=accepted_preview,
        rejected_unsafe_edit_preview=rejected_preview,
        receipt_summary_rows=tuple(workflow.get("receipt_summary_rows", ()) or ())
        + ((accepted_preview.get("receipt_summary_row"),) if accepted_preview and accepted_preview.get("receipt_summary_row") else ()),
        sidecar_file_summary=_stored_file_rows(store_result),
    )


def build_source_record_review_panel_state(source_record_review_workflow: Any) -> SourceReviewPanelState:
    workflow = _as_dict(source_record_review_workflow)
    summary = {
        "source_record_count": workflow.get("source_record_count", 0),
        "reference_count": workflow.get("reference_count", 0),
        "selector_cross_link_count": workflow.get("selector_audit_cross_link_count", 0),
        "annotation_receipt_count": workflow.get("annotation_receipt_count", 0),
        "named_site_method_pack_count": workflow.get("named_site_method_pack_count", 0),
    }
    return SourceReviewPanelState(
        panel_id="source_record_review_panel_" + _sha16((workflow.get("workflow_id"), summary)),
        panel_kind="source_record_review",
        title="Source Record Review",
        summary=summary,
        rows=_tuple_of_dicts(workflow.get("rows")),
        receipt_summary_rows=_tuple_of_dicts(
            receipt
            for row in tuple(workflow.get("rows", ()) or ())
            for receipt in (row.get("annotation_receipts", ()) if isinstance(row, dict) else ())
        ),
    )


def build_selector_approval_panel_state(selector_approval_packets: Any) -> SourceReviewPanelState:
    packets = _as_dict(selector_approval_packets)
    summary = {
        "approval_packet_count": packets.get("packet_count", 0),
        "manual_smoke_checklist_row_count": packets.get("manual_smoke_checklist_row_count", 0),
        "not_live_executed_receipt_count": packets.get("not_live_executed_receipt_count", 0),
        "selector_audit_required": True,
    }
    return SourceReviewPanelState(
        panel_id="source_selector_approval_panel_" + _sha16((packets.get("collection_id"), summary)),
        panel_kind="selector_approval",
        title="Selector Approval",
        summary=summary,
        rows=_tuple_of_dicts(packets.get("packets")),
        receipt_summary_rows=_tuple_of_dicts(packets.get("not_live_executed_receipts")),
    )


def build_named_site_method_pack_panel_state(named_site_method_packs: Any) -> SourceReviewPanelState:
    packs = _as_dict(named_site_method_packs)
    summary = {
        "named_site_method_pack_count": packs.get("pack_count", 0),
        "msn_pack_count": packs.get("msn_pack_count", 0),
        "twitter_x_pack_count": packs.get("twitter_x_pack_count", 0),
        "youtube_pack_count": packs.get("youtube_pack_count", 0),
        "generic_archive_pack_count": packs.get("generic_archive_pack_count", 0),
        "selector_audit_required_count": packs.get("selector_audit_required_count", 0),
        "live_approved_only_count": packs.get("live_approved_only_count", 0),
    }
    return SourceReviewPanelState(
        panel_id="source_named_site_method_pack_panel_" + _sha16((packs.get("collection_id"), summary)),
        panel_kind="named_site_method_packs",
        title="Named-Site Method Packs",
        summary=summary,
        rows=_tuple_of_dicts(packs.get("packs")),
    )


def build_source_audit_dashboard_state(
    *,
    database_review_workflow: Any,
    source_record_review_workflow: Any,
    selector_approval_packets: Any,
    named_site_method_packs: Any,
    operator_command_packs: Any | None = None,
    manual_smoke_checklists: Any | None = None,
    access_online_asr_bridge_summary: Any | None = None,
) -> SourceReviewPanelState:
    database = _as_dict(database_review_workflow)
    records = _as_dict(source_record_review_workflow)
    selectors = _as_dict(selector_approval_packets)
    packs = _as_dict(named_site_method_packs)
    commands = _as_dict(operator_command_packs)
    smoke = _as_dict(manual_smoke_checklists)
    access = _as_dict(access_online_asr_bridge_summary)
    summary = {
        "database_scan_count": database.get("scan_row_count", 0),
        "review_needed_count": database.get("review_needed_row_count", 0),
        "safe_edit_pending_count": database.get("pending_safe_edit_count", 0),
        "rejected_unsafe_edit_count": database.get("rejected_unsafe_edit_count", 0),
        "source_record_count": records.get("source_record_count", 0),
        "named_site_method_pack_count": packs.get("pack_count", 0),
        "selector_approval_packet_count": selectors.get("packet_count", 0),
        "selector_audit_required_count": packs.get("selector_audit_required_count", 0),
        "operator_command_pack_count": commands.get("pack_count", 0),
        "manual_smoke_checklist_pack_count": smoke.get("pack_count", 0),
        "access_online_asr_bridge_summary_id": access.get("summary_id", ""),
        "no_live_execution_status": "no_live_execution_performed",
    }
    rows = (
        {"row_kind": "database_review", **summary},
        {"row_kind": "source_record_review", **records},
        {"row_kind": "selector_approval", **selectors},
        {"row_kind": "named_site_method_packs", **packs},
    )
    return SourceReviewPanelState(
        panel_id="source_audit_dashboard_state_" + _sha16(summary),
        panel_kind="source_audit_dashboard",
        title="Source Audit Dashboard",
        summary=summary,
        rows=rows,
    )


def source_review_panel_state_to_json(state: SourceReviewPanelState) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True)
