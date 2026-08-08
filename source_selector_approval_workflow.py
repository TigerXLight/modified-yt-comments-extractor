from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping

from source_site_method_audit_registry import (
    SourceSiteMethodAuditRegistry,
    build_source_site_method_audit_registry,
)


SOURCE_SELECTOR_APPROVAL_WORKFLOW_SCHEMA_VERSION = "source_selector_approval_workflow_v1"


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


@dataclass(frozen=True)
class SourceSelectorManualSmokeChecklistRow:
    checklist_row_id: str
    site_method_id: str
    scope: str
    manual_instruction: str
    expected_artifact_ref_type: str
    safety_boundary: str = "manual_operator_approval_required_no_live_execution_performed"
    result_placeholder: str = "pending_manual_operator_review"
    metadata_only: bool = True
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceSelectorNotLiveExecutedReceipt:
    receipt_id: str
    site_method_id: str
    status: str = "not_live_executed"
    reason: str = "No live/browser/network/archive/API/provider execution was performed."
    metadata_only: bool = True
    user_review_required: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    provider_call_performed: bool = False
    completed_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceSelectorApprovalPacket:
    packet_id: str
    site_method_id: str
    site_profile_id: str
    site_display_name: str
    method_id: str
    source_type: str
    status: str
    approval_status: str = "APPROVAL_REQUIRED"
    ready_for_operator_review: bool = True
    operator_approval_required: bool = True
    required_operator_inputs: tuple[str, ...] = ()
    expected_artifact_refs: tuple[str, ...] = ()
    manual_smoke_checklist_rows: tuple[SourceSelectorManualSmokeChecklistRow, ...] = ()
    not_live_executed_receipt: SourceSelectorNotLiveExecutedReceipt | None = None
    metadata_only: bool = True
    user_review_required: bool = True
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    @property
    def checklist_row_count(self) -> int:
        return len(self.manual_smoke_checklist_rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["checklist_row_count"] = self.checklist_row_count
        return data


@dataclass(frozen=True)
class SourceSelectorApprovalPacketCollection:
    collection_id: str
    schema_version: str = SOURCE_SELECTOR_APPROVAL_WORKFLOW_SCHEMA_VERSION
    packets: tuple[SourceSelectorApprovalPacket, ...] = ()
    grouped_by_site_profile: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    named_site_method_pack_summary: Mapping[str, Any] = field(default_factory=dict)
    selector_audit_required_count: int = 0
    live_approved_only_count: int = 0
    metadata_only: bool = True
    user_review_required: bool = True
    no_live_execution_performed: bool = True
    no_completed_evidence_claimed: bool = True
    no_automatic_classification_performed: bool = True

    @property
    def packet_count(self) -> int:
        return len(self.packets)

    @property
    def manual_smoke_checklist_row_count(self) -> int:
        return sum(packet.checklist_row_count for packet in self.packets)

    @property
    def not_live_executed_receipt_count(self) -> int:
        return sum(1 for packet in self.packets if packet.not_live_executed_receipt is not None)

    @property
    def ready_for_operator_review_count(self) -> int:
        return sum(1 for packet in self.packets if packet.ready_for_operator_review)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data.update(
            {
                "packet_count": self.packet_count,
                "manual_smoke_checklist_row_count": self.manual_smoke_checklist_row_count,
                "not_live_executed_receipt_count": self.not_live_executed_receipt_count,
                "ready_for_operator_review_count": self.ready_for_operator_review_count,
            }
        )
        return data


def list_selector_audit_required_rows(
    registry: SourceSiteMethodAuditRegistry | None = None,
) -> tuple[Any, ...]:
    source_registry = registry or build_source_site_method_audit_registry()
    return tuple(row for row in source_registry.rows if row.status == "selector_audit_required")


def group_selector_audit_rows_by_site_profile(
    rows: tuple[Any, ...],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row.site_profile_id, []).append(row.site_method_id)
    return {key: tuple(sorted(value)) for key, value in sorted(grouped.items())}


def _checklist_rows_for_method(row: Any) -> tuple[SourceSelectorManualSmokeChecklistRow, ...]:
    base_payload = {
        "method_id": row.method_id,
        "site_method_id": row.site_method_id,
        "site_profile_id": row.site_profile_id,
    }
    definitions = (
        (
            "selector_boundary_review",
            "Review site-specific selector boundaries and confirm article/comment separation.",
            "selector_audit_reference",
        ),
        (
            "manual_observation_fallback",
            "Confirm manual observation/import fallback remains available before live execution.",
            "manual_observation_reference",
        ),
        (
            "archive_only_fallback",
            "Confirm archive-only evidence can be reviewed without live site access.",
            "archive_reference",
        ),
        (
            "operator_approval_packet",
            "Record named-site operator approval requirements before any browser/network action.",
            "operator_approval_reference",
        ),
    )
    rows = []
    for scope, instruction, artifact_ref_type in definitions:
        payload = dict(base_payload)
        payload["scope"] = scope
        rows.append(
            SourceSelectorManualSmokeChecklistRow(
                checklist_row_id="source_selector_checklist_" + _sha16(payload),
                site_method_id=row.site_method_id,
                scope=scope,
                manual_instruction=instruction,
                expected_artifact_ref_type=artifact_ref_type,
            )
        )
    return tuple(rows)


def build_source_selector_approval_packet(row: Any) -> SourceSelectorApprovalPacket:
    checklist = _checklist_rows_for_method(row)
    receipt = SourceSelectorNotLiveExecutedReceipt(
        receipt_id="source_selector_not_live_executed_" + _sha16(
            {
                "method_id": row.method_id,
                "site_method_id": row.site_method_id,
                "status": row.status,
            }
        ),
        site_method_id=row.site_method_id,
    )
    payload = {
        "method_id": row.method_id,
        "site_method_id": row.site_method_id,
        "status": row.status,
    }
    return SourceSelectorApprovalPacket(
        packet_id="source_selector_approval_packet_" + _sha16(payload),
        site_method_id=row.site_method_id,
        site_profile_id=row.site_profile_id,
        site_display_name=row.site_display_name,
        method_id=row.method_id,
        source_type=row.source_type,
        status=row.status,
        required_operator_inputs=tuple(sorted(row.operator_approval_requirement)),
        expected_artifact_refs=tuple(sorted(row.expected_artifact_refs)),
        manual_smoke_checklist_rows=checklist,
        not_live_executed_receipt=receipt,
    )


def build_source_selector_approval_packet_collection(
    registry: SourceSiteMethodAuditRegistry | None = None,
    *,
    include_live_approved_only: bool = False,
    named_site_method_packs: Any | None = None,
) -> SourceSelectorApprovalPacketCollection:
    source_registry = registry or build_source_site_method_audit_registry()
    rows = [
        row
        for row in source_registry.rows
        if row.status == "selector_audit_required"
        or (include_live_approved_only and row.status == "live_approved_only")
    ]
    rows = sorted(rows, key=lambda item: (item.site_profile_id, item.method_id, item.site_method_id))
    packets = tuple(build_source_selector_approval_packet(row) for row in rows)
    grouped = group_selector_audit_rows_by_site_profile(tuple(rows))
    payload = {
        "named_site_method_pack_count": getattr(named_site_method_packs, "pack_count", 0),
        "packet_ids": [packet.packet_id for packet in packets],
        "selector_required": source_registry.selector_audit_required_count,
        "live_approved_only": source_registry.live_approved_only_count,
    }
    return SourceSelectorApprovalPacketCollection(
        collection_id="source_selector_approval_packets_" + _sha16(payload),
        packets=packets,
        grouped_by_site_profile=grouped,
        named_site_method_pack_summary={
            "collection_id": getattr(named_site_method_packs, "collection_id", ""),
            "pack_count": getattr(named_site_method_packs, "pack_count", 0),
            "selector_audit_required_count": getattr(
                named_site_method_packs,
                "selector_audit_required_count",
                0,
            ),
            "not_live_executed": getattr(named_site_method_packs, "not_live_executed", True),
            "metadata_only": True,
            "user_review_required": True,
        },
        selector_audit_required_count=source_registry.selector_audit_required_count,
        live_approved_only_count=source_registry.live_approved_only_count,
    )


def source_selector_approval_packet_collection_to_json(
    collection: SourceSelectorApprovalPacketCollection,
) -> str:
    return json.dumps(collection.to_dict(), indent=2, sort_keys=True)
