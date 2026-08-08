from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_site_method_audit_registry import (
    SourceSiteMethodAuditRegistry,
    build_source_site_method_audit_registry,
)


SOURCE_NAMED_SITE_PRIORITY_PLAN_SCHEMA_VERSION = "source_named_site_priority_plan_v1"


@dataclass(frozen=True)
class SourceNamedSitePriorityRow:
    priority_id: str
    priority_rank: int
    site_label: str
    method_id: str
    adapter_id: str
    approval_status: str
    planned_operator_inputs: tuple[str, ...]
    expected_artifact_refs: tuple[str, ...]
    safety_boundary: str
    status: str
    next_action: str
    metadata_only: bool = True
    user_review_required: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceNamedSitePriorityPlan:
    plan_id: str
    rows: tuple[SourceNamedSitePriorityRow, ...]
    review_workflow_summary: Mapping[str, Any] = field(default_factory=dict)
    selector_approval_packet_summary: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SOURCE_NAMED_SITE_PRIORITY_PLAN_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    approval_status: str = "APPROVAL_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def approval_required_count(self) -> int:
        return sum(1 for row in self.rows if row.approval_status == "APPROVAL_REQUIRED")

    @property
    def selector_audit_required_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "selector_audit_required")

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["approval_required_count"] = self.approval_required_count
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


def _summary_from(value: Any, *keys: str) -> dict[str, Any]:
    data = value.to_dict() if hasattr(value, "to_dict") and callable(value.to_dict) else _value_for_dict(value)
    if not isinstance(data, dict):
        return {}
    return {key: data.get(key) for key in keys if key in data}


PRIORITY_METHOD_ORDER = (
    "msn_article",
    "msn_shadow_dom_comments",
    "twitter_x_public_post_archive_manual_import",
    "twitter_x_reply_thread_archive_manual_import",
    "youtube_media_transcript",
    "youtube_comments",
    "generic_article_html",
    "generic_comments_site_specific_selector",
    "archive_only_import",
)


def _operator_inputs_for_method(method_id: str) -> tuple[str, ...]:
    common = ("named_site_or_source_label", "approved_source_url_or_local_import_metadata")
    if method_id in {"twitter_x_public_post_archive_manual_import", "twitter_x_reply_thread_archive_manual_import"}:
        return common + ("operator_supplied_archive_or_export_reference", "thread_boundary_note")
    if method_id == "generic_comments_site_specific_selector":
        return common + ("site_specific_selector_review_note", "manual_or_archive_fallback_note")
    if method_id == "archive_only_import":
        return common + ("archive_url", "original_url", "archive_provider_type")
    return common + ("manual_observation_note",)


def build_source_named_site_priority_plan(
    registry: SourceSiteMethodAuditRegistry | None = None,
    *,
    database_review_workflow: Any | None = None,
    source_record_review_workflow: Any | None = None,
    selector_approval_packets: Any | None = None,
) -> SourceNamedSitePriorityPlan:
    source_registry = registry or build_source_site_method_audit_registry()
    by_method = {row.method_id: row for row in source_registry.rows}
    rows: list[SourceNamedSitePriorityRow] = []
    for rank, method_id in enumerate(PRIORITY_METHOD_ORDER, start=1):
        row = by_method.get(method_id)
        if row is None:
            continue
        payload = {
            "method_id": method_id,
            "rank": rank,
            "schema_version": SOURCE_NAMED_SITE_PRIORITY_PLAN_SCHEMA_VERSION,
            "site_method_id": row.site_method_id,
        }
        rows.append(
            SourceNamedSitePriorityRow(
                priority_id="source_named_site_priority_" + _sha16(payload),
                priority_rank=rank,
                site_label=row.site_display_name,
                method_id=row.method_id,
                adapter_id=row.adapter_id,
                approval_status="APPROVAL_REQUIRED",
                planned_operator_inputs=_stable_tuple(_operator_inputs_for_method(row.method_id)),
                expected_artifact_refs=row.expected_artifact_refs,
                safety_boundary="manual_operator_approval_required_before_live_or_destructive_execution",
                status=row.status,
                next_action=(
                    "perform_named_site_selector_audit_with_explicit_approval"
                    if row.selector_audit_required
                    else "prepare_manual_live_smoke_inputs_when_approved"
                ),
            )
        )
    payload = {
        "priority_ids": [row.priority_id for row in rows],
        "schema_version": SOURCE_NAMED_SITE_PRIORITY_PLAN_SCHEMA_VERSION,
    }
    return SourceNamedSitePriorityPlan(
        plan_id="source_named_site_priority_plan_" + _sha16(payload),
        rows=tuple(rows),
        review_workflow_summary={
            "database_review": _summary_from(
                database_review_workflow,
                "view_model_id",
                "summary_id",
                "database_scan_row_count",
                "scan_row_count",
                "review_needed_row_count",
                "pending_safe_edit_count",
                "rejected_unsafe_edit_count",
            ),
            "source_record_review": _summary_from(
                source_record_review_workflow,
                "workflow_id",
                "source_record_count",
                "selector_audit_cross_link_count",
            ),
            "live_execution_performed": False,
            "completed_evidence_claimed": False,
        },
        selector_approval_packet_summary=_summary_from(
            selector_approval_packets,
            "collection_id",
            "packet_count",
            "manual_smoke_checklist_row_count",
            "not_live_executed_receipt_count",
        ),
    )


def validate_source_named_site_priority_plan(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_NAMED_SITE_PRIORITY_PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported named-site priority plan schema version")
    for required_true in ("metadata_only", "local_only", "sensitive_inference_prohibited"):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe named-site priority plan flag: {required_true}")
    for required_false in (
        "live_execution_performed",
        "browser_automation_performed",
        "provider_call_performed",
        "archive_submission_performed",
        "download_performed",
        "completed_evidence_claimed",
        "automatic_classification",
        "protected_attribute_inference_performed",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe named-site priority plan flag: {required_false}")
    rows = data.get("rows", ())
    if not isinstance(rows, list) or not rows:
        raise ValueError("Named-site priority plan must contain rows")
    ranks = [row.get("priority_rank") for row in rows if isinstance(row, dict)]
    if ranks != sorted(ranks):
        raise ValueError("Named-site priority rows must be rank ordered")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Named-site priority rows must be JSON objects")
        for required in ("priority_id", "site_label", "method_id", "approval_status", "safety_boundary"):
            if not row.get(required):
                raise ValueError(f"Named-site priority row missing required field: {required}")
        if row.get("approval_status") != "APPROVAL_REQUIRED":
            raise ValueError("Named-site priority rows must remain approval-required")
        for unsafe in (
            "live_execution_performed",
            "browser_automation_performed",
            "provider_call_performed",
            "archive_submission_performed",
            "download_performed",
            "completed_evidence_claimed",
            "automatic_classification",
            "protected_attribute_inference_performed",
        ):
            if row.get(unsafe) is not False:
                raise ValueError(f"Unsafe named-site priority row flag: {unsafe}")


def source_named_site_priority_plan_to_json(plan: SourceNamedSitePriorityPlan) -> str:
    return _stable_json(plan.to_dict(), pretty=True)
