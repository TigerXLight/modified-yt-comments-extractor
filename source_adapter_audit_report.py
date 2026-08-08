from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_adapter_audit_registry import (
    SourceAdapterAuditRegistry,
    build_source_adapter_audit_registry,
)
from source_site_method_audit_registry import (
    SourceSiteMethodAuditRegistry,
    SourceSiteSelectorAuditPackCollection,
    build_source_site_method_audit_registry,
    build_source_site_selector_audit_pack_collection,
)


SOURCE_ADAPTER_AUDIT_REPORT_SCHEMA_VERSION = "source_adapter_audit_report_v1"


@dataclass(frozen=True)
class SourceAdapterAuditReportRow:
    row_id: str
    row_kind: str
    display_name: str
    adapter_id: str
    method_id: str
    status: str
    execution_status: str
    selector_audit_required: bool = False
    live_approved_only: bool = False
    operator_approval_requirement: str = ""
    next_review_action: str = "review_metadata_only"
    metadata_only: bool = True
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceAdapterAuditReport:
    report_id: str
    adapter_registry_id: str
    site_method_registry_id: str
    selector_pack_collection_id: str
    rows: tuple[SourceAdapterAuditReportRow, ...]
    workflow_sidecar_filenames: tuple[str, ...] = ()
    schema_version: str = SOURCE_ADAPTER_AUDIT_REPORT_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def selector_audit_required_count(self) -> int:
        return sum(1 for row in self.rows if row.selector_audit_required)

    @property
    def live_approved_only_count(self) -> int:
        return sum(1 for row in self.rows if row.live_approved_only)

    @property
    def not_yet_executed_count(self) -> int:
        return sum(1 for row in self.rows if row.execution_status == "not_yet_executed")

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["live_approved_only_count"] = self.live_approved_only_count
        data["not_yet_executed_count"] = self.not_yet_executed_count
        data["row_count"] = self.row_count
        data["selector_audit_required_count"] = self.selector_audit_required_count
        return data


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


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


def _adapter_rows(registry: SourceAdapterAuditRegistry) -> tuple[SourceAdapterAuditReportRow, ...]:
    rows: list[SourceAdapterAuditReportRow] = []
    for entry in registry.entries:
        rows.append(
            SourceAdapterAuditReportRow(
                row_id=entry.audit_entry_id,
                row_kind="adapter_method_profile",
                display_name=entry.method_display_name,
                adapter_id=entry.adapter_id,
                method_id=entry.method_profile_id,
                status=entry.audit_status,
                execution_status=entry.execution_status,
                operator_approval_requirement="; ".join(entry.operator_approval_requirements),
                next_review_action="review_adapter_method_profile_metadata",
            )
        )
    return tuple(rows)


def _site_method_rows(registry: SourceSiteMethodAuditRegistry) -> tuple[SourceAdapterAuditReportRow, ...]:
    rows: list[SourceAdapterAuditReportRow] = []
    for row in registry.rows:
        next_action = "site_specific_selector_audit_required" if row.selector_audit_required else "review_site_method_metadata"
        rows.append(
            SourceAdapterAuditReportRow(
                row_id=row.site_method_id,
                row_kind="site_method_profile",
                display_name=row.site_display_name,
                adapter_id=row.adapter_id,
                method_id=row.method_id,
                status=row.status,
                execution_status=row.execution_status,
                selector_audit_required=row.selector_audit_required,
                live_approved_only=row.live_approved_only,
                operator_approval_requirement=row.operator_approval_requirement,
                next_review_action=next_action,
            )
        )
    return tuple(rows)


def build_source_adapter_audit_report(
    *,
    adapter_registry: SourceAdapterAuditRegistry | None = None,
    site_method_registry: SourceSiteMethodAuditRegistry | None = None,
    selector_pack_collection: SourceSiteSelectorAuditPackCollection | None = None,
    workflow_sidecar_filenames: Iterable[str] = (),
) -> SourceAdapterAuditReport:
    adapters = adapter_registry or build_source_adapter_audit_registry()
    site_methods = site_method_registry or build_source_site_method_audit_registry()
    packs = selector_pack_collection or build_source_site_selector_audit_pack_collection(site_methods)
    rows = tuple(sorted(_adapter_rows(adapters) + _site_method_rows(site_methods), key=lambda row: (row.row_kind, row.adapter_id, row.method_id)))
    payload = {
        "adapter_registry_id": adapters.registry_id,
        "row_ids": [row.row_id for row in rows],
        "schema_version": SOURCE_ADAPTER_AUDIT_REPORT_SCHEMA_VERSION,
        "site_method_registry_id": site_methods.registry_id,
    }
    return SourceAdapterAuditReport(
        report_id="source_adapter_audit_report_" + _sha16(payload),
        adapter_registry_id=adapters.registry_id,
        site_method_registry_id=site_methods.registry_id,
        selector_pack_collection_id=packs.collection_id,
        rows=rows,
        workflow_sidecar_filenames=_stable_tuple(workflow_sidecar_filenames),
    )


def validate_source_adapter_audit_report(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_ADAPTER_AUDIT_REPORT_SCHEMA_VERSION:
        raise ValueError("Unsupported source adapter audit report schema version")
    for required_true in ("metadata_only", "local_only", "sensitive_inference_prohibited"):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe source adapter audit report flag: {required_true}")
    for required_false in (
        "live_execution_performed",
        "browser_automation_performed",
        "provider_call_performed",
        "archive_submission_performed",
        "download_performed",
        "file_move_performed",
        "completed_evidence_claimed",
        "automatic_classification",
        "protected_attribute_inference_performed",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe source adapter audit report flag: {required_false}")
    rows = data.get("rows", ())
    if not isinstance(rows, list) or not rows:
        raise ValueError("Source adapter audit report must contain rows")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Source adapter audit report rows must be JSON objects")
        for required in ("row_id", "row_kind", "adapter_id", "method_id", "status"):
            if not row.get(required):
                raise ValueError(f"Source adapter audit report row missing required field: {required}")
        if row.get("live_execution_performed") is not False:
            raise ValueError("Source adapter audit report row cannot claim live execution")
        if row.get("completed_evidence_claimed") is not False:
            raise ValueError("Source adapter audit report row cannot claim completed evidence")


def source_adapter_audit_report_to_json(report: SourceAdapterAuditReport) -> str:
    return _stable_json(report.to_dict(), pretty=True)
