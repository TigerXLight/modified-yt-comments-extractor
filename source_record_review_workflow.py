from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping


SOURCE_RECORD_REVIEW_WORKFLOW_SCHEMA_VERSION = "source_record_review_workflow_v1"

REFERENCE_BUCKETS = (
    "article_reference_ids",
    "comment_reference_ids",
    "media_reference_ids",
    "transcript_reference_ids",
    "archive_url_references",
    "screenshot_reference_ids",
    "snapshot_reference_ids",
    "manual_observation_reference_ids",
    "provider_receipt_reference_ids",
    "selector_audit_reference_ids",
    "database_review_receipt_reference_ids",
    "release_action_receipt_reference_ids",
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


def _record_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict") and callable(record.to_dict):
        return record.to_dict()
    return _value_for_dict(record)


def _registry_row_by_site_method_id(registry: Any | None) -> dict[str, Mapping[str, Any]]:
    rows = tuple(getattr(registry, "rows", ()) or ())
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        data = _value_for_dict(row)
        site_method_id = str(data.get("site_method_id", ""))
        if site_method_id:
            result[site_method_id] = data
    return result


@dataclass(frozen=True)
class SourceRecordReferenceSummary:
    bucket_name: str
    reference_ids: tuple[str, ...] = ()
    reference_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceRecordReviewAnnotationReceipt:
    receipt_id: str
    grabbed_source_record_id: str
    operator_note: str = ""
    cross_linked_audit_row_ids: tuple[str, ...] = ()
    metadata_only: bool = True
    user_review_required: bool = True
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceRecordReviewRow:
    grabbed_source_record_id: str
    source_row_id: str = ""
    adapter_id: str = ""
    capture_method_profile_id: str = ""
    canonical_url: str = ""
    reference_summaries: tuple[SourceRecordReferenceSummary, ...] = ()
    selector_audit_cross_links: tuple[Mapping[str, Any], ...] = ()
    annotation_receipts: tuple[SourceRecordReviewAnnotationReceipt, ...] = ()
    metadata_only: bool = True
    user_review_required: bool = True
    file_move_performed: bool = False
    live_execution_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification_performed: bool = False

    @property
    def reference_bucket_count(self) -> int:
        return len(self.reference_summaries)

    @property
    def reference_count(self) -> int:
        return sum(summary.reference_count for summary in self.reference_summaries)

    @property
    def selector_audit_cross_link_count(self) -> int:
        return len(self.selector_audit_cross_links)

    @property
    def annotation_receipt_count(self) -> int:
        return len(self.annotation_receipts)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data.update(
            {
                "reference_bucket_count": self.reference_bucket_count,
                "reference_count": self.reference_count,
                "selector_audit_cross_link_count": self.selector_audit_cross_link_count,
                "annotation_receipt_count": self.annotation_receipt_count,
            }
        )
        return data


@dataclass(frozen=True)
class SourceRecordReviewWorkflow:
    workflow_id: str
    schema_version: str = SOURCE_RECORD_REVIEW_WORKFLOW_SCHEMA_VERSION
    rows: tuple[SourceRecordReviewRow, ...] = ()
    metadata_only: bool = True
    user_review_required: bool = True
    no_file_movement_performed: bool = True
    no_live_execution_performed: bool = True
    no_completed_evidence_claimed: bool = True
    no_automatic_classification_performed: bool = True

    @property
    def source_record_count(self) -> int:
        return len(self.rows)

    @property
    def reference_bucket_count(self) -> int:
        return sum(row.reference_bucket_count for row in self.rows)

    @property
    def reference_count(self) -> int:
        return sum(row.reference_count for row in self.rows)

    @property
    def selector_audit_cross_link_count(self) -> int:
        return sum(row.selector_audit_cross_link_count for row in self.rows)

    @property
    def annotation_receipt_count(self) -> int:
        return sum(row.annotation_receipt_count for row in self.rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data.update(
            {
                "source_record_count": self.source_record_count,
                "reference_bucket_count": self.reference_bucket_count,
                "reference_count": self.reference_count,
                "selector_audit_cross_link_count": self.selector_audit_cross_link_count,
                "annotation_receipt_count": self.annotation_receipt_count,
            }
        )
        return data


def build_source_record_review_annotation_receipt(
    *,
    grabbed_source_record_id: str,
    operator_note: str = "",
    cross_linked_audit_row_ids: tuple[str, ...] = (),
) -> SourceRecordReviewAnnotationReceipt:
    payload = {
        "cross_linked_audit_row_ids": sorted(set(cross_linked_audit_row_ids)),
        "grabbed_source_record_id": grabbed_source_record_id,
        "operator_note": operator_note.strip(),
    }
    return SourceRecordReviewAnnotationReceipt(
        receipt_id="source_record_review_receipt_" + _sha16(payload),
        grabbed_source_record_id=grabbed_source_record_id,
        operator_note=operator_note.strip(),
        cross_linked_audit_row_ids=tuple(sorted(set(cross_linked_audit_row_ids))),
    )


def _reference_summaries(record_data: Mapping[str, Any]) -> tuple[SourceRecordReferenceSummary, ...]:
    summaries: list[SourceRecordReferenceSummary] = []
    for bucket in REFERENCE_BUCKETS:
        values = tuple(str(value) for value in record_data.get(bucket, ()) if str(value))
        summaries.append(
            SourceRecordReferenceSummary(
                bucket_name=bucket,
                reference_ids=tuple(sorted(set(values))),
                reference_count=len(set(values)),
            )
        )
    return tuple(summaries)


def _selector_audit_cross_links(
    record_data: Mapping[str, Any],
    site_method_registry: Any | None,
) -> tuple[Mapping[str, Any], ...]:
    registry_rows = _registry_row_by_site_method_id(site_method_registry)
    links: list[Mapping[str, Any]] = []
    for reference_id in tuple(record_data.get("selector_audit_reference_ids", ()) or ()):
        row = registry_rows.get(str(reference_id))
        links.append(
            {
                "selector_audit_reference_id": str(reference_id),
                "site_method_id": row.get("site_method_id", "") if row else "",
                "site_profile_id": row.get("site_profile_id", "") if row else "",
                "method_id": row.get("method_id", "") if row else "",
                "status": row.get("status", "review_required") if row else "review_required",
                "metadata_only": True,
                "user_review_required": True,
            }
        )
    return tuple(sorted(links, key=lambda item: item["selector_audit_reference_id"]))


def build_source_record_review_row(
    record: Any,
    *,
    site_method_registry: Any | None = None,
    annotation_receipts: tuple[SourceRecordReviewAnnotationReceipt, ...] = (),
) -> SourceRecordReviewRow:
    record_data = _record_dict(record)
    grabbed_source_record_id = str(record_data.get("grabbed_source_record_id", ""))
    receipts = tuple(
        receipt for receipt in annotation_receipts if receipt.grabbed_source_record_id == grabbed_source_record_id
    )
    return SourceRecordReviewRow(
        grabbed_source_record_id=grabbed_source_record_id,
        source_row_id=str(record_data.get("source_row_id", "")),
        adapter_id=str(record_data.get("adapter_id", "")),
        capture_method_profile_id=str(record_data.get("capture_method_profile_id", "")),
        canonical_url=str(record_data.get("canonical_url", "")),
        reference_summaries=_reference_summaries(record_data),
        selector_audit_cross_links=_selector_audit_cross_links(record_data, site_method_registry),
        annotation_receipts=receipts,
    )


def build_source_record_review_workflow(
    records: tuple[Any, ...] = (),
    *,
    site_method_registry: Any | None = None,
    annotation_receipts: tuple[SourceRecordReviewAnnotationReceipt, ...] = (),
) -> SourceRecordReviewWorkflow:
    rows = tuple(
        build_source_record_review_row(
            record,
            site_method_registry=site_method_registry,
            annotation_receipts=annotation_receipts,
        )
        for record in records
        if record is not None
    )
    payload = {
        "annotation_receipt_count": sum(row.annotation_receipt_count for row in rows),
        "record_ids": [row.grabbed_source_record_id for row in rows],
        "selector_link_count": sum(row.selector_audit_cross_link_count for row in rows),
    }
    return SourceRecordReviewWorkflow(
        workflow_id="source_record_review_workflow_" + _sha16(payload),
        rows=rows,
    )


def source_record_review_workflow_to_json(workflow: SourceRecordReviewWorkflow) -> str:
    return json.dumps(workflow.to_dict(), indent=2, sort_keys=True)
