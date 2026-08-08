from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION = "source_site_method_audit_registry_v1"

SITE_METHOD_STATUS_METADATA_AUDIT_READY = "metadata_audit_ready"
SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED = "selector_audit_required"
SITE_METHOD_STATUS_NOT_YET_EXECUTED = "not_yet_executed"
SITE_METHOD_STATUS_LIVE_APPROVED_ONLY = "live_approved_only"

SOURCE_SITE_METHOD_ALLOWED_STATUSES = (
    SITE_METHOD_STATUS_METADATA_AUDIT_READY,
    SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED,
    SITE_METHOD_STATUS_NOT_YET_EXECUTED,
    SITE_METHOD_STATUS_LIVE_APPROVED_ONLY,
)

SOURCE_SITE_METHOD_UNSAFE_FLAGS = (
    "live_execution_performed",
    "browser_automation_performed",
    "provider_call_performed",
    "archive_submission_performed",
    "download_performed",
    "file_move_performed",
    "completed_evidence_claimed",
    "automatic_classification",
    "protected_attribute_inference_performed",
)


@dataclass(frozen=True)
class SourceSiteMethodAuditRow:
    site_method_id: str
    site_profile_id: str
    site_display_name: str
    adapter_id: str
    method_id: str
    source_type: str
    selector_or_strategy: str
    comment_support: str
    transcript_support: str
    media_support: str
    expected_artifact_refs: tuple[str, ...]
    archive_fallback: str
    manual_observation_support: str
    database_mapping: tuple[str, ...]
    total_export_mapping: tuple[str, ...]
    operator_approval_requirement: str
    status: str
    execution_status: str = SITE_METHOD_STATUS_NOT_YET_EXECUTED
    selector_audit_required: bool = False
    live_approved_only: bool = False
    method_audit_metadata: Mapping[str, Any] = field(default_factory=dict)
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
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceSiteMethodAuditRegistry:
    registry_id: str
    rows: tuple[SourceSiteMethodAuditRow, ...]
    schema_version: str = SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION
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
        return sum(1 for row in self.rows if row.status == SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED)

    @property
    def metadata_audit_ready_count(self) -> int:
        return sum(1 for row in self.rows if row.status == SITE_METHOD_STATUS_METADATA_AUDIT_READY)

    @property
    def live_approved_only_count(self) -> int:
        return sum(1 for row in self.rows if row.live_approved_only)

    @property
    def not_yet_executed_count(self) -> int:
        return sum(1 for row in self.rows if row.execution_status == SITE_METHOD_STATUS_NOT_YET_EXECUTED)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["live_approved_only_count"] = self.live_approved_only_count
        data["metadata_audit_ready_count"] = self.metadata_audit_ready_count
        data["not_yet_executed_count"] = self.not_yet_executed_count
        data["row_count"] = self.row_count
        data["selector_audit_required_count"] = self.selector_audit_required_count
        return data


@dataclass(frozen=True)
class SourceSiteSelectorAuditPack:
    """Named-site audit packet derived from a source site/method row.

    The packet is still metadata-only. It gives review/export layers one durable
    object that describes the exact reference buckets a future grabbed-source
    record is expected to populate after explicit operator approval.
    """

    selector_audit_pack_id: str
    site_method_id: str
    site_profile_id: str
    site_display_name: str
    adapter_id: str
    method_id: str
    source_type: str
    selector_or_strategy: str
    expected_artifact_refs: tuple[str, ...]
    typed_grabbed_source_reference_buckets: tuple[str, ...]
    archive_fallback: str
    manual_observation_support: str
    database_mapping: tuple[str, ...]
    total_export_mapping: tuple[str, ...]
    operator_approval_requirement: str
    status: str
    execution_status: str
    selector_audit_required: bool
    live_approved_only: bool
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
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceSiteSelectorAuditPackCollection:
    collection_id: str
    packs: tuple[SourceSiteSelectorAuditPack, ...]
    schema_version: str = SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION
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
    def pack_count(self) -> int:
        return len(self.packs)

    @property
    def selector_audit_required_count(self) -> int:
        return sum(1 for pack in self.packs if pack.selector_audit_required)

    @property
    def live_approved_only_count(self) -> int:
        return sum(1 for pack in self.packs if pack.live_approved_only)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["live_approved_only_count"] = self.live_approved_only_count
        data["pack_count"] = self.pack_count
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


def _typed_reference_buckets_for_row(row: SourceSiteMethodAuditRow) -> tuple[str, ...]:
    buckets: set[str] = {
        "manual_observation_reference_ids",
        "selector_audit_reference_ids",
    }
    if "article" in row.source_type:
        buckets.update(
            {
                "article_reference_ids",
                "archive_url_references",
                "screenshot_reference_ids",
                "snapshot_reference_ids",
            }
        )
    if "comment" in row.source_type or "reply" in row.source_type or row.method_id.endswith("comments"):
        buckets.update(
            {
                "comment_reference_ids",
                "archive_url_references",
                "screenshot_reference_ids",
            }
        )
    if "media" in row.source_type or "video" in row.source_type:
        buckets.update({"media_reference_ids", "transcript_reference_ids"})
    if "transcript" in row.source_type:
        buckets.add("transcript_reference_ids")
    if "archive" in row.source_type or "archive" in row.method_id:
        buckets.update({"archive_url_references", "provider_receipt_reference_ids"})
    return tuple(sorted(buckets))


def _selector_pack_from_row(row: SourceSiteMethodAuditRow) -> SourceSiteSelectorAuditPack:
    payload = {
        "schema_version": SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION,
        "site_method_id": row.site_method_id,
        "typed_buckets": _typed_reference_buckets_for_row(row),
    }
    return SourceSiteSelectorAuditPack(
        selector_audit_pack_id="source_site_selector_audit_pack_" + _sha16(payload),
        site_method_id=row.site_method_id,
        site_profile_id=row.site_profile_id,
        site_display_name=row.site_display_name,
        adapter_id=row.adapter_id,
        method_id=row.method_id,
        source_type=row.source_type,
        selector_or_strategy=row.selector_or_strategy,
        expected_artifact_refs=row.expected_artifact_refs,
        typed_grabbed_source_reference_buckets=_typed_reference_buckets_for_row(row),
        archive_fallback=row.archive_fallback,
        manual_observation_support=row.manual_observation_support,
        database_mapping=row.database_mapping,
        total_export_mapping=row.total_export_mapping,
        operator_approval_requirement=row.operator_approval_requirement,
        status=row.status,
        execution_status=row.execution_status,
        selector_audit_required=row.selector_audit_required,
        live_approved_only=row.live_approved_only,
        notes=row.notes,
    )


def _row(
    *,
    site_profile_id: str,
    site_display_name: str,
    adapter_id: str,
    method_id: str,
    source_type: str,
    selector_or_strategy: str,
    comment_support: str,
    transcript_support: str = "not_supported",
    media_support: str = "not_supported",
    expected_artifact_refs: Iterable[str] = (),
    archive_fallback: str = "operator_supplied_or_future_approved_archive_metadata",
    manual_observation_support: str = "supported_metadata_only",
    database_mapping: Iterable[str] = (),
    total_export_mapping: Iterable[str] = (),
    operator_approval_requirement: str = "operator_review_required_before_live_execution",
    status: str = SITE_METHOD_STATUS_METADATA_AUDIT_READY,
    execution_status: str = SITE_METHOD_STATUS_NOT_YET_EXECUTED,
    selector_audit_required: bool = False,
    live_approved_only: bool = False,
    method_audit_metadata: Mapping[str, Any] | None = None,
    notes: str = "",
) -> SourceSiteMethodAuditRow:
    payload = {
        "method_id": method_id,
        "schema_version": SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION,
        "site_profile_id": site_profile_id,
    }
    return SourceSiteMethodAuditRow(
        site_method_id="source_site_method_audit_" + _sha16(payload),
        site_profile_id=site_profile_id,
        site_display_name=site_display_name,
        adapter_id=adapter_id,
        method_id=method_id,
        source_type=source_type,
        selector_or_strategy=selector_or_strategy,
        comment_support=comment_support,
        transcript_support=transcript_support,
        media_support=media_support,
        expected_artifact_refs=_stable_tuple(expected_artifact_refs),
        archive_fallback=str(archive_fallback or ""),
        manual_observation_support=str(manual_observation_support or ""),
        database_mapping=_stable_tuple(database_mapping),
        total_export_mapping=_stable_tuple(total_export_mapping),
        operator_approval_requirement=str(operator_approval_requirement or ""),
        status=status,
        execution_status=execution_status,
        selector_audit_required=selector_audit_required,
        live_approved_only=live_approved_only,
        method_audit_metadata=dict(method_audit_metadata or {}),
        notes=notes,
    )


def build_source_site_method_audit_registry() -> SourceSiteMethodAuditRegistry:
    """Build named-site/source-method audit rows for selector and manual-review readiness."""

    common_db_mapping = (
        "site_method_id",
        "site_profile_id",
        "source_type",
        "selector_audit_status",
        "review_state",
    )
    common_export_mapping = (
        "source_site_method_audit_registry_sidecar",
        "review_manifest_metadata",
        "total_export_metadata_only_asset",
    )
    rows = (
        _row(
            site_profile_id="msn_article",
            site_display_name="MSN article",
            adapter_id="msn",
            method_id="msn_article",
            source_type="article",
            selector_or_strategy="fixture_or_operator_supplied_article_dom_metadata",
            comment_support="separate_msn_shadow_dom_comments_row",
            expected_artifact_refs=("ARTICLE_TEXT", "FINAL_DOM", "RAW_HTML", "SCREENSHOT", "ARCHIVE_RESULT"),
            archive_fallback="operator_supplied_or_future_approved_archive_metadata",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
            notes="MSN article metadata is audit-ready; live selector execution remains separately approved.",
        ),
        _row(
            site_profile_id="msn_shadow_dom_comments",
            site_display_name="MSN shadow-DOM comments",
            adapter_id="msn",
            method_id="msn_shadow_dom_comments",
            source_type="comments",
            selector_or_strategy="shadow_dom_fixture_or_manual_observation_metadata",
            comment_support="shadow_dom_comments_fixture_and_manual_observation_metadata",
            expected_artifact_refs=("COMMENTS_JSONL", "COMMENTS_SUMMARY", "SCREENSHOT", "ARCHIVE_RESULT"),
            archive_fallback="archive_metadata_fallback_plus_manual_observation",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
            notes="Shadow-DOM selector profile is metadata-only until named-site live approval.",
        ),
        _row(
            site_profile_id="twitter_x_public_post_archive_manual",
            site_display_name="X/Twitter public post archive/manual import",
            adapter_id="twitter_x",
            method_id="twitter_x_public_post_archive_manual_import",
            source_type="social_post",
            selector_or_strategy="operator_supplied_archive_or_local_export_metadata",
            comment_support="reply_count_or_local_export_metadata_only",
            media_support="post_media_metadata_only",
            expected_artifact_refs=("ARCHIVE_URL", "MANUAL_OBSERVATION", "SCREENSHOT_REFERENCE"),
            archive_fallback="operator_supplied_archive_url_no_provider_call",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="twitter_x_reply_thread_archive_manual",
            site_display_name="X/Twitter reply-thread archive/manual import",
            adapter_id="twitter_x",
            method_id="twitter_x_reply_thread_archive_manual_import",
            source_type="reply_thread",
            selector_or_strategy="parent_post_reply_ids_thread_boundary_manual_or_archive_metadata",
            comment_support="reply_thread_metadata_only",
            media_support="thread_media_metadata_only",
            expected_artifact_refs=("PARENT_POST_REF", "REPLY_IDS", "THREAD_BOUNDARY", "ARCHIVE_URL", "MANUAL_OBSERVATION"),
            archive_fallback="operator_supplied_archive_url_no_provider_call",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="youtube_media_transcript",
            site_display_name="YouTube media/transcript",
            adapter_id="youtube",
            method_id="youtube_media_transcript",
            source_type="video_media_transcript",
            selector_or_strategy="existing_runtime_output_or_operator_supplied_metadata",
            comment_support="separate_youtube_comments_row",
            transcript_support="existing_output_metadata_or_local_transcript",
            media_support="existing_output_metadata_only",
            expected_artifact_refs=("MEDIA_METADATA", "TRANSCRIPT_REFERENCE", "YOUTUBE_RUNTIME_STATUS"),
            archive_fallback="manual_archive_note_only",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="youtube_comments",
            site_display_name="YouTube comments",
            adapter_id="youtube",
            method_id="youtube_comments",
            source_type="comments",
            selector_or_strategy="existing_runtime_output_status_count_metadata",
            comment_support="existing_output_status_count_metadata",
            expected_artifact_refs=("COMMENTS_STATUS_COUNTS", "REPLY_STATUS_COUNTS"),
            archive_fallback="manual_archive_note_only",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="generic_article_html",
            site_display_name="Generic article HTML",
            adapter_id="news_website",
            method_id="generic_article_html",
            source_type="article",
            selector_or_strategy="canonical_url_html_snapshot_text_extraction_receipt_metadata",
            comment_support="not_supported_in_article_html_row",
            expected_artifact_refs=("CANONICAL_URL", "HTML_SNAPSHOT", "TEXT_EXTRACTION_RECEIPT", "SCREENSHOT_REFERENCE", "ARCHIVE_URL"),
            archive_fallback="operator_supplied_or_future_approved_archive_metadata",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="generic_comments_manual_import",
            site_display_name="Generic comments manual observation/import",
            adapter_id="news_website",
            method_id="generic_comments_manual_import",
            source_type="comments",
            selector_or_strategy="operator_supplied_manual_observation_or_local_import_metadata",
            comment_support="manual_observation_or_local_import_available_now",
            expected_artifact_refs=("COMMENT_TREE_SUMMARY", "MANUAL_OBSERVATION", "ARCHIVE_URL"),
            archive_fallback="archive_only_comment_evidence_review_available",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
            notes="Manual observation/import is available now without claiming universal selectors.",
        ),
        _row(
            site_profile_id="generic_comments_site_selector",
            site_display_name="Generic comments site-specific selector",
            adapter_id="news_website",
            method_id="generic_comments_site_specific_selector",
            source_type="comments",
            selector_or_strategy="named_site_selector_required_before_live_execution",
            comment_support="selector_audit_required_before_live_comment_capture",
            expected_artifact_refs=("SELECTOR_AUDIT_NOTE", "COMMENT_BOUNDARY_NOTE", "MANUAL_OBSERVATION"),
            archive_fallback="manual_or_archive_only_comment_evidence_until_selector_approved",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
            operator_approval_requirement="named_site_selector_audit_and_operator_live_approval_required",
            status=SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED,
            selector_audit_required=True,
            live_approved_only=True,
            method_audit_metadata={
                "site_specific_selector_required_before_live_execution": True,
                "manual_observation_import_available_now": True,
                "archive_only_comment_evidence_review_available_now": True,
                "universal_selector_support_claimed": False,
            },
            notes="Tracked nested generic comment selector gap; live execution remains blocked.",
        ),
        _row(
            site_profile_id="generic_comments_archive_only",
            site_display_name="Generic comments archive-only import",
            adapter_id="news_website",
            method_id="generic_comments_archive_only_import",
            source_type="comments",
            selector_or_strategy="operator_supplied_archive_comment_metadata_only",
            comment_support="archive_only_review_available_now",
            expected_artifact_refs=("ARCHIVE_URL", "ORIGINAL_URL", "ARCHIVE_METADATA", "COMMENT_BOUNDARY_NOTE"),
            archive_fallback="archive_is_primary_source_metadata_no_provider_call",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
        _row(
            site_profile_id="archive_only_import",
            site_display_name="Archive-only import",
            adapter_id="manual_local_import",
            method_id="archive_only_import",
            source_type="archive_import",
            selector_or_strategy="operator_supplied_archive_url_and_original_url_metadata",
            comment_support="archive_metadata_only_when_supplied",
            transcript_support="archive_metadata_only_when_supplied",
            media_support="archive_metadata_only_when_supplied",
            expected_artifact_refs=("ARCHIVE_URL", "ORIGINAL_URL", "ARCHIVE_PROVIDER_TYPE", "REVIEW_SIGNOFF"),
            archive_fallback="no_live_site_required",
            database_mapping=common_db_mapping,
            total_export_mapping=common_export_mapping,
        ),
    )
    registry_payload = {
        "row_ids": [row.site_method_id for row in rows],
        "schema_version": SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION,
    }
    return SourceSiteMethodAuditRegistry(
        registry_id="source_site_method_audit_registry_" + _sha16(registry_payload),
        rows=rows,
    )


def source_site_method_audit_row_by_method(
    registry: SourceSiteMethodAuditRegistry,
    method_id: str,
) -> SourceSiteMethodAuditRow | None:
    for row in registry.rows:
        if row.method_id == method_id:
            return row
    return None


def source_site_method_audit_rows_by_status(
    registry: SourceSiteMethodAuditRegistry,
    status: str,
) -> tuple[SourceSiteMethodAuditRow, ...]:
    return tuple(row for row in registry.rows if row.status == status)


def build_source_site_selector_audit_pack_collection(
    registry: SourceSiteMethodAuditRegistry | None = None,
) -> SourceSiteSelectorAuditPackCollection:
    source_registry = registry or build_source_site_method_audit_registry()
    packs = tuple(_selector_pack_from_row(row) for row in source_registry.rows)
    payload = {
        "pack_ids": [pack.selector_audit_pack_id for pack in packs],
        "schema_version": SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION,
    }
    return SourceSiteSelectorAuditPackCollection(
        collection_id="source_site_selector_audit_packs_" + _sha16(payload),
        packs=packs,
    )


def source_site_selector_audit_pack_by_method(
    collection: SourceSiteSelectorAuditPackCollection,
    method_id: str,
) -> SourceSiteSelectorAuditPack | None:
    for pack in collection.packs:
        if pack.method_id == method_id:
            return pack
    return None


def validate_source_site_selector_audit_pack_collection(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported source site selector audit pack schema version")
    for flag in SOURCE_SITE_METHOD_UNSAFE_FLAGS:
        if data.get(flag) is not False:
            raise ValueError(f"Unsafe source site selector audit pack collection flag: {flag}")
    packs = data.get("packs", ())
    if not isinstance(packs, list) or not packs:
        raise ValueError("Source site selector audit pack collection must contain packs")
    seen: set[str] = set()
    for pack in packs:
        if not isinstance(pack, dict):
            raise ValueError("Source site selector audit packs must be JSON objects")
        for required in (
            "selector_audit_pack_id",
            "site_method_id",
            "method_id",
            "typed_grabbed_source_reference_buckets",
            "status",
        ):
            if not pack.get(required):
                raise ValueError(f"Source site selector audit pack missing required field: {required}")
        if pack["selector_audit_pack_id"] in seen:
            raise ValueError("Duplicate source site selector audit pack id")
        seen.add(str(pack["selector_audit_pack_id"]))
        if pack.get("status") not in SOURCE_SITE_METHOD_ALLOWED_STATUSES:
            raise ValueError(f"Unsupported source site selector audit pack status: {pack.get('status')}")
        for flag in SOURCE_SITE_METHOD_UNSAFE_FLAGS:
            if pack.get(flag) is not False:
                raise ValueError(f"Unsafe source site selector audit pack flag: {flag}")


def validate_source_site_method_audit_registry(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_SITE_METHOD_AUDIT_REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported source site/method audit registry schema version")
    for flag in SOURCE_SITE_METHOD_UNSAFE_FLAGS:
        if data.get(flag) is not False:
            raise ValueError(f"Unsafe source site/method audit registry flag: {flag}")
    rows = data.get("rows", ())
    if not isinstance(rows, list) or not rows:
        raise ValueError("Source site/method audit registry must contain rows")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Source site/method audit rows must be JSON objects")
        for required in (
            "site_method_id",
            "site_profile_id",
            "method_id",
            "source_type",
            "selector_or_strategy",
            "status",
        ):
            if not row.get(required):
                raise ValueError(f"Source site/method audit row missing required field: {required}")
        if row["site_method_id"] in seen:
            raise ValueError("Duplicate source site/method audit row id")
        seen.add(str(row["site_method_id"]))
        if row.get("status") not in SOURCE_SITE_METHOD_ALLOWED_STATUSES:
            raise ValueError(f"Unsupported source site/method audit status: {row.get('status')}")
        for flag in SOURCE_SITE_METHOD_UNSAFE_FLAGS:
            if row.get(flag) is not False:
                raise ValueError(f"Unsafe source site/method audit row flag: {flag}")
        metadata = row.get("method_audit_metadata", {})
        if isinstance(metadata, dict):
            for flag in SOURCE_SITE_METHOD_UNSAFE_FLAGS:
                if metadata.get(flag) is True:
                    raise ValueError(f"Unsafe source site/method audit metadata flag: {flag}")


def source_site_method_audit_registry_to_json(registry: SourceSiteMethodAuditRegistry) -> str:
    return _stable_json(registry.to_dict(), pretty=True)


def source_site_selector_audit_pack_collection_to_json(
    collection: SourceSiteSelectorAuditPackCollection,
) -> str:
    return _stable_json(collection.to_dict(), pretty=True)
