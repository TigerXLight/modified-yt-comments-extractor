from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping

from evidence_database_index import (
    EvidenceIndexManifest,
    EvidenceIndexScanFilter,
    EvidenceIndexUpdateResult,
    SourceSiteMethodAuditUpdatePatch,
    apply_source_site_method_audit_update,
    scan_evidence_index_records,
    scan_review_needed_evidence_index_records,
    scan_source_site_method_audit_records,
    scan_source_site_method_review_needed_records,
)


SOURCE_DATABASE_REVIEW_WORKFLOW_SCHEMA_VERSION = "source_database_review_workflow_v1"

SAFE_REVIEW_METADATA_STATES = (
    "metadata_audit_ready",
    "selector_audit_required",
    "not_yet_executed",
    "live_approved_only",
)

UNSAFE_TEXT_MARKERS = (
    "api key",
    "authorization:",
    "bearer ",
    "cookie:",
    "credential",
    "password",
    "secret",
    "session cookie",
    "token=",
)

PROTECTED_OR_SENSITIVE_MARKERS = (
    "religion",
    "ethnicity",
    "nationality",
    "political",
    "protected attribute",
    "sensitive classification",
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
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _has_absolute_local_path(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    if re.search(r"(^|[\s'\"])[A-Za-z]:\\", text):
        return True
    if "\\\\" in text:
        return True
    return False


def _has_unsafe_text(value: str) -> bool:
    normalized = _clean(value).lower()
    if not normalized:
        return False
    if any(marker in normalized for marker in UNSAFE_TEXT_MARKERS):
        return True
    return _has_absolute_local_path(normalized)


def _has_protected_sensitive_text(value: str) -> bool:
    normalized = _clean(value).lower()
    return bool(normalized and any(marker in normalized for marker in PROTECTED_OR_SENSITIVE_MARKERS))


@dataclass(frozen=True)
class SourceDatabaseReviewFilterState:
    site_profile: str = ""
    status: str = ""
    review_state: str = ""
    artifact_type: str = ""
    source_url_contains: str = ""
    row_kind: str = ""
    show_review_needed_only: bool = False

    def to_scan_filter(self) -> EvidenceIndexScanFilter:
        return EvidenceIndexScanFilter(
            site_profile=self.site_profile,
            status=self.status,
            review_state=self.review_state,
            artifact_type=self.artifact_type,
            source_url_contains=self.source_url_contains,
        )

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewSelectedRowState:
    row_id: str = ""
    row_kind: str = ""
    display_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewPendingEditState:
    target_item_id: str
    status: str = ""
    operator_review_note: str = ""
    selector_audit_note: str = ""
    manual_observation_note: str = ""
    archive_fallback_note: str = ""
    review_queue_assignment: str = ""
    source_record_cross_reference_note: str = ""
    total_export_inclusion_note: str = ""
    completed_evidence_claimed: bool = False
    live_execution_claimed: bool = False
    file_movement_claimed: bool = False
    raw_payload_insertion_claimed: bool = False
    local_absolute_path_insertion_claimed: bool = False
    credential_material_claimed: bool = False
    protected_sensitive_classification_claimed: bool = False
    automatic_classification_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewSafeUpdateProposalRow:
    proposal_id: str
    item_id: str
    status: str = ""
    changed_fields: tuple[str, ...] = ()
    receipt_id: str = ""
    preview_only: bool = True
    ready_for_apply: bool = False
    metadata_only: bool = True
    user_review_required: bool = True
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewRejectedUpdateRow:
    rejection_id: str
    item_id: str
    reasons: tuple[str, ...]
    metadata_only: bool = True
    rejected: bool = True
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewReceiptSummaryRow:
    receipt_id: str
    item_id: str
    changed_fields: tuple[str, ...] = ()
    validation_status: str = "ok"
    preview_only: bool = True
    file_read_performed: bool = False
    file_write_performed: bool = False
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewEditPreview:
    preview_id: str
    item_id: str
    accepted_for_preview: bool
    proposal_row: SourceDatabaseReviewSafeUpdateProposalRow | None = None
    rejected_update_row: SourceDatabaseReviewRejectedUpdateRow | None = None
    receipt_summary_row: SourceDatabaseReviewReceiptSummaryRow | None = None
    errors: tuple[str, ...] = ()
    metadata_only: bool = True
    preview_before_apply: bool = True
    file_write_performed: bool = False
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewBridgeSummary:
    summary_id: str
    database_scan_row_count: int = 0
    review_needed_row_count: int = 0
    selector_audit_required_count: int = 0
    pending_safe_edit_count: int = 0
    rejected_unsafe_edit_count: int = 0
    source_record_count: int = 0
    evidence_queue_row_count: int = 0
    approval_packet_count: int = 0
    named_site_method_pack_count: int = 0
    named_site_method_pack_selector_audit_required_count: int = 0
    no_live_execution_performed: bool = True
    metadata_only: bool = True
    user_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceDatabaseReviewViewModel:
    view_model_id: str
    schema_version: str = SOURCE_DATABASE_REVIEW_WORKFLOW_SCHEMA_VERSION
    scan_rows: tuple[Mapping[str, Any], ...] = ()
    review_needed_rows: tuple[Mapping[str, Any], ...] = ()
    adapter_audit_rows: tuple[Mapping[str, Any], ...] = ()
    site_method_audit_rows: tuple[Mapping[str, Any], ...] = ()
    named_site_method_pack_rows: tuple[Mapping[str, Any], ...] = ()
    source_grabbed_record_rows: tuple[Mapping[str, Any], ...] = ()
    evidence_queue_rows: tuple[Mapping[str, Any], ...] = ()
    safe_update_proposals: tuple[SourceDatabaseReviewSafeUpdateProposalRow, ...] = ()
    rejected_update_rows: tuple[SourceDatabaseReviewRejectedUpdateRow, ...] = ()
    receipt_summary_rows: tuple[SourceDatabaseReviewReceiptSummaryRow, ...] = ()
    filter_state: SourceDatabaseReviewFilterState = field(default_factory=SourceDatabaseReviewFilterState)
    selected_row_state: SourceDatabaseReviewSelectedRowState = field(
        default_factory=SourceDatabaseReviewSelectedRowState
    )
    pending_edit_state: SourceDatabaseReviewPendingEditState | None = None
    bridge_summary: SourceDatabaseReviewBridgeSummary | None = None
    metadata_only: bool = True
    user_review_required: bool = True
    no_live_execution_performed: bool = True
    no_file_movement_performed: bool = True
    no_completed_evidence_claimed: bool = True

    @property
    def scan_row_count(self) -> int:
        return len(self.scan_rows)

    @property
    def review_needed_row_count(self) -> int:
        return len(self.review_needed_rows)

    @property
    def adapter_audit_row_count(self) -> int:
        return len(self.adapter_audit_rows)

    @property
    def site_method_audit_row_count(self) -> int:
        return len(self.site_method_audit_rows)

    @property
    def named_site_method_pack_row_count(self) -> int:
        return len(self.named_site_method_pack_rows)

    @property
    def named_site_method_pack_selector_audit_required_count(self) -> int:
        return sum(
            1 for row in self.named_site_method_pack_rows if row.get("selector_audit_required") is True
        )

    @property
    def source_grabbed_record_count(self) -> int:
        return len(self.source_grabbed_record_rows)

    @property
    def evidence_queue_row_count(self) -> int:
        return len(self.evidence_queue_rows)

    @property
    def pending_safe_edit_count(self) -> int:
        return len(self.safe_update_proposals)

    @property
    def rejected_unsafe_edit_count(self) -> int:
        return len(self.rejected_update_rows)

    @property
    def receipt_summary_row_count(self) -> int:
        return len(self.receipt_summary_rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data.update(
            {
                "scan_row_count": self.scan_row_count,
                "review_needed_row_count": self.review_needed_row_count,
                "adapter_audit_row_count": self.adapter_audit_row_count,
                "site_method_audit_row_count": self.site_method_audit_row_count,
                "named_site_method_pack_row_count": self.named_site_method_pack_row_count,
                "named_site_method_pack_selector_audit_required_count": (
                    self.named_site_method_pack_selector_audit_required_count
                ),
                "source_grabbed_record_count": self.source_grabbed_record_count,
                "evidence_queue_row_count": self.evidence_queue_row_count,
                "pending_safe_edit_count": self.pending_safe_edit_count,
                "rejected_unsafe_edit_count": self.rejected_unsafe_edit_count,
                "receipt_summary_row_count": self.receipt_summary_row_count,
            }
        )
        return data


def _scan_row_dict(row: Any) -> dict[str, Any]:
    data = _value_for_dict(row)
    return {key: data[key] for key in sorted(data)}


def _registry_rows(registry: Any, attr: str) -> tuple[Mapping[str, Any], ...]:
    rows = tuple(getattr(registry, attr, ()) or ())
    return tuple(_value_for_dict(row) for row in rows)


def _queue_rows(queue: Any) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for item in tuple(getattr(queue, "items", ()) or ()):
        data = _value_for_dict(item)
        rows.append(
            {
                "item_id": data.get("item_id", ""),
                "source_url": data.get("source_url", ""),
                "title": data.get("title", ""),
                "review_status": data.get("status", ""),
                "metadata_only": True,
                "user_review_required": True,
            }
        )
    return tuple(rows)


def _named_site_method_pack_rows(collection: Any | None) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for pack in tuple(getattr(collection, "packs", ()) or ()):
        data = _value_for_dict(pack)
        rows.append(
            {
                "pack_id": data.get("pack_id", ""),
                "site_method_id": data.get("site_method_id", ""),
                "site_profile_id": data.get("site_profile_id", ""),
                "site_display_name": data.get("site_display_name", ""),
                "site_group": data.get("site_group", ""),
                "method_id": data.get("method_id", ""),
                "source_type": data.get("source_type", ""),
                "status": data.get("status", ""),
                "selector_audit_required": data.get("selector_audit_required", False),
                "live_approved_only": data.get("live_approved_only", False),
                "not_live_executed_status": data.get("not_live_executed_status", ""),
                "remaining_blocker_count": len(data.get("exact_remaining_audit_blockers", ()) or ()),
                "metadata_only": True,
                "user_review_required": True,
            }
        )
    return tuple(sorted(rows, key=lambda row: (row["site_group"], row["method_id"], row["pack_id"])))


def _grabbed_source_rows(records: tuple[Any, ...]) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for record in records:
        data = _value_for_dict(record)
        rows.append(
            {
                "grabbed_source_record_id": data.get("grabbed_source_record_id", ""),
                "source_row_id": data.get("source_row_id", ""),
                "adapter_id": data.get("adapter_id", ""),
                "capture_method_profile_id": data.get("capture_method_profile_id", ""),
                "artifact_count": data.get("artifact_count", 0),
                "selector_audit_reference_count": data.get("selector_audit_reference_count", 0),
                "database_review_receipt_reference_count": data.get(
                    "database_review_receipt_reference_count", 0
                ),
                "metadata_only": True,
                "user_review_required": True,
            }
        )
    return tuple(rows)


def _classification_dimensions_for_pending_edit(
    pending_edit: SourceDatabaseReviewPendingEditState,
) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    if pending_edit.review_queue_assignment:
        dimensions["review_queue_assignment_note_status"] = "review_note_recorded"
    if pending_edit.source_record_cross_reference_note:
        dimensions["source_record_cross_reference_note_status"] = "review_note_recorded"
    if pending_edit.total_export_inclusion_note:
        dimensions["total_export_inclusion_note_status"] = "review_note_recorded"
    return dimensions


def _pending_edit_rejection_reasons(pending_edit: SourceDatabaseReviewPendingEditState) -> tuple[str, ...]:
    reasons: list[str] = []
    if pending_edit.completed_evidence_claimed:
        reasons.append("completed_evidence_claim_rejected")
    if pending_edit.live_execution_claimed:
        reasons.append("live_execution_claim_rejected")
    if pending_edit.file_movement_claimed:
        reasons.append("file_movement_claim_rejected")
    if pending_edit.raw_payload_insertion_claimed:
        reasons.append("raw_payload_insertion_rejected")
    if pending_edit.local_absolute_path_insertion_claimed:
        reasons.append("local_absolute_path_insertion_rejected")
    if pending_edit.credential_material_claimed:
        reasons.append("credential_cookie_account_material_rejected")
    if pending_edit.protected_sensitive_classification_claimed:
        reasons.append("protected_sensitive_classification_rejected")
    if pending_edit.automatic_classification_claimed:
        reasons.append("automatic_classification_claim_rejected")
    texts = (
        pending_edit.operator_review_note,
        pending_edit.selector_audit_note,
        pending_edit.manual_observation_note,
        pending_edit.archive_fallback_note,
        pending_edit.review_queue_assignment,
        pending_edit.source_record_cross_reference_note,
        pending_edit.total_export_inclusion_note,
    )
    if any(_has_unsafe_text(text) for text in texts):
        reasons.append("credential_cookie_account_or_absolute_path_text_rejected")
    if any(_has_protected_sensitive_text(text) for text in texts):
        reasons.append("protected_sensitive_text_rejected")
    if pending_edit.status and pending_edit.status not in SAFE_REVIEW_METADATA_STATES:
        reasons.append("unsupported_status_transition_rejected")
    return tuple(sorted(set(reasons)))


def preview_source_database_review_update(
    manifest: EvidenceIndexManifest,
    pending_edit: SourceDatabaseReviewPendingEditState,
    *,
    operator_id: str = "operator_review",
    timestamp_utc: str = "1970-01-01T00:00:00Z",
) -> SourceDatabaseReviewEditPreview:
    """Build a metadata-only update preview without writing files or moving evidence."""

    reasons = _pending_edit_rejection_reasons(pending_edit)
    preview_id = "source_database_review_preview_" + _sha16(pending_edit)
    if reasons:
        rejected = SourceDatabaseReviewRejectedUpdateRow(
            rejection_id="source_database_review_rejected_" + _sha16((pending_edit, reasons)),
            item_id=pending_edit.target_item_id,
            reasons=reasons,
        )
        return SourceDatabaseReviewEditPreview(
            preview_id=preview_id,
            item_id=pending_edit.target_item_id,
            accepted_for_preview=False,
            rejected_update_row=rejected,
            errors=reasons,
        )

    patch = SourceSiteMethodAuditUpdatePatch(
        item_id=pending_edit.target_item_id,
        status=pending_edit.status,
        operator_review_note=pending_edit.operator_review_note,
        selector_audit_note=pending_edit.selector_audit_note,
        archive_manual_fallback_note=pending_edit.archive_fallback_note,
        manual_observation_note=pending_edit.manual_observation_note,
        classification_dimensions=_classification_dimensions_for_pending_edit(pending_edit),
    )
    try:
        update_result = apply_source_site_method_audit_update(
            manifest,
            patch,
            operator_id=operator_id,
            timestamp_utc=timestamp_utc,
        )
    except ValueError as error:
        rejected = SourceDatabaseReviewRejectedUpdateRow(
            rejection_id="source_database_review_rejected_" + _sha16((pending_edit, str(error))),
            item_id=pending_edit.target_item_id,
            reasons=(str(error),),
        )
        return SourceDatabaseReviewEditPreview(
            preview_id=preview_id,
            item_id=pending_edit.target_item_id,
            accepted_for_preview=False,
            rejected_update_row=rejected,
            errors=(str(error),),
        )

    receipt_row = _receipt_summary_from_update_result(update_result)
    proposal = SourceDatabaseReviewSafeUpdateProposalRow(
        proposal_id="source_database_review_proposal_" + _sha16((pending_edit, receipt_row.receipt_id)),
        item_id=pending_edit.target_item_id,
        status=pending_edit.status,
        changed_fields=receipt_row.changed_fields,
        receipt_id=receipt_row.receipt_id,
    )
    return SourceDatabaseReviewEditPreview(
        preview_id=preview_id,
        item_id=pending_edit.target_item_id,
        accepted_for_preview=True,
        proposal_row=proposal,
        receipt_summary_row=receipt_row,
    )


def _receipt_summary_from_update_result(
    update_result: EvidenceIndexUpdateResult,
) -> SourceDatabaseReviewReceiptSummaryRow:
    return SourceDatabaseReviewReceiptSummaryRow(
        receipt_id=update_result.receipt.receipt_id,
        item_id=update_result.receipt.item_id,
        changed_fields=tuple(sorted(update_result.receipt.changed_fields)),
        validation_status=update_result.receipt.validation_status,
        file_read_performed=update_result.receipt.file_read_performed,
        file_write_performed=update_result.receipt.file_write_performed,
        file_move_performed=update_result.receipt.file_move_performed,
        live_execution_performed=bool(getattr(update_result.receipt, "live_execution_performed", False)),
        completed_evidence_claimed=bool(getattr(update_result.receipt, "completed_evidence_claimed", False)),
    )


def build_source_database_review_bridge_summary(
    *,
    database_scan_row_count: int = 0,
    review_needed_row_count: int = 0,
    selector_audit_required_count: int = 0,
    pending_safe_edit_count: int = 0,
    rejected_unsafe_edit_count: int = 0,
    source_record_count: int = 0,
    evidence_queue_row_count: int = 0,
    approval_packet_count: int = 0,
    named_site_method_pack_count: int = 0,
    named_site_method_pack_selector_audit_required_count: int = 0,
) -> SourceDatabaseReviewBridgeSummary:
    payload = {
        "database_scan_row_count": database_scan_row_count,
        "review_needed_row_count": review_needed_row_count,
        "selector_audit_required_count": selector_audit_required_count,
        "pending_safe_edit_count": pending_safe_edit_count,
        "rejected_unsafe_edit_count": rejected_unsafe_edit_count,
        "source_record_count": source_record_count,
        "evidence_queue_row_count": evidence_queue_row_count,
        "approval_packet_count": approval_packet_count,
        "named_site_method_pack_count": named_site_method_pack_count,
        "named_site_method_pack_selector_audit_required_count": (
            named_site_method_pack_selector_audit_required_count
        ),
    }
    return SourceDatabaseReviewBridgeSummary(
        summary_id="source_database_review_bridge_" + _sha16(payload),
        **payload,
    )


def build_source_database_review_view_model(
    *,
    manifest: EvidenceIndexManifest,
    source_adapter_audit_registry: Any | None = None,
    source_site_method_audit_registry: Any | None = None,
    source_named_site_method_packs: Any | None = None,
    grabbed_source_records: tuple[Any, ...] = (),
    evidence_queue: Any | None = None,
    filter_state: SourceDatabaseReviewFilterState | None = None,
    selected_row_state: SourceDatabaseReviewSelectedRowState | None = None,
    pending_edit_state: SourceDatabaseReviewPendingEditState | None = None,
    safe_update_proposals: tuple[SourceDatabaseReviewSafeUpdateProposalRow, ...] = (),
    rejected_update_rows: tuple[SourceDatabaseReviewRejectedUpdateRow, ...] = (),
    receipt_summary_rows: tuple[SourceDatabaseReviewReceiptSummaryRow, ...] = (),
    approval_packet_count: int = 0,
) -> SourceDatabaseReviewViewModel:
    active_filter = filter_state or SourceDatabaseReviewFilterState()
    scan_result = scan_evidence_index_records(manifest, active_filter.to_scan_filter())
    review_needed_result = scan_review_needed_evidence_index_records(manifest, active_filter.to_scan_filter())
    site_method_result = scan_source_site_method_audit_records(manifest)
    site_method_review_needed = scan_source_site_method_review_needed_records(manifest)
    scan_rows = tuple(_scan_row_dict(row) for row in scan_result.rows)
    review_needed_rows = tuple(_scan_row_dict(row) for row in review_needed_result.rows)
    site_method_rows = _registry_rows(source_site_method_audit_registry, "rows")
    if not site_method_rows:
        site_method_rows = tuple(_scan_row_dict(row) for row in site_method_result.rows)
    adapter_rows = _registry_rows(source_adapter_audit_registry, "entries")
    named_site_pack_rows = _named_site_method_pack_rows(source_named_site_method_packs)
    grabbed_rows = _grabbed_source_rows(tuple(grabbed_source_records or ()))
    queue_rows = _queue_rows(evidence_queue)
    selector_required_count = sum(
        1 for row in site_method_rows if row.get("status") == "selector_audit_required"
    )
    bridge_summary = build_source_database_review_bridge_summary(
        database_scan_row_count=len(scan_rows),
        review_needed_row_count=len(site_method_review_needed.rows) or len(review_needed_rows),
        selector_audit_required_count=selector_required_count,
        pending_safe_edit_count=len(safe_update_proposals),
        rejected_unsafe_edit_count=len(rejected_update_rows),
        source_record_count=len(grabbed_rows),
        evidence_queue_row_count=len(queue_rows),
        approval_packet_count=approval_packet_count,
        named_site_method_pack_count=len(named_site_pack_rows),
        named_site_method_pack_selector_audit_required_count=sum(
            1 for row in named_site_pack_rows if row.get("selector_audit_required") is True
        ),
    )
    payload = {
        "manifest_id": manifest.manifest_id,
        "scan_row_count": len(scan_rows),
        "review_needed_row_count": len(review_needed_rows),
        "site_method_audit_row_count": len(site_method_rows),
        "named_site_method_pack_row_count": len(named_site_pack_rows),
        "adapter_audit_row_count": len(adapter_rows),
        "source_grabbed_record_count": len(grabbed_rows),
        "evidence_queue_row_count": len(queue_rows),
        "pending_safe_edit_count": len(safe_update_proposals),
        "rejected_unsafe_edit_count": len(rejected_update_rows),
    }
    return SourceDatabaseReviewViewModel(
        view_model_id="source_database_review_workflow_" + _sha16(payload),
        scan_rows=scan_rows,
        review_needed_rows=review_needed_rows,
        adapter_audit_rows=adapter_rows,
        site_method_audit_rows=site_method_rows,
        named_site_method_pack_rows=named_site_pack_rows,
        source_grabbed_record_rows=grabbed_rows,
        evidence_queue_rows=queue_rows,
        safe_update_proposals=tuple(safe_update_proposals),
        rejected_update_rows=tuple(rejected_update_rows),
        receipt_summary_rows=tuple(receipt_summary_rows),
        filter_state=active_filter,
        selected_row_state=selected_row_state or SourceDatabaseReviewSelectedRowState(),
        pending_edit_state=pending_edit_state,
        bridge_summary=bridge_summary,
    )


def source_database_review_view_model_to_json(view_model: SourceDatabaseReviewViewModel) -> str:
    return json.dumps(view_model.to_dict(), indent=2, sort_keys=True)
