from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from source_adapters import (
    AVAILABLE_SOURCE_ADAPTERS,
    CREDENTIAL_NONE,
    MANUAL_LOCAL_IMPORT_PROFILE,
    SOURCE_METHOD_PROFILES,
    SourceAdapter,
    SourceMethodProfile,
    find_source_method_profile,
)


SOURCE_ADAPTER_AUDIT_REGISTRY_SCHEMA_VERSION = "source_adapter_audit_registry_v1"

AUDIT_STATUS_METADATA_SCAFFOLDED = "metadata_scaffolded"
AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE = "metadata_bridge_available"
AUDIT_STATUS_METADATA_AUDIT_READY = "metadata_audit_ready"
AUDIT_STATUS_AUDIT_REQUIRED = "audit_required"
EXECUTION_STATUS_NOT_YET_EXECUTED = "not_yet_executed"


@dataclass(frozen=True)
class SourceAdapterAuditEntry:
    audit_entry_id: str
    adapter_id: str
    adapter_display_name: str
    method_id: str
    method_profile_id: str
    method_display_name: str
    source_type: str
    capture_method: str
    required_artifacts: tuple[str, ...] = ()
    archive_strategy: str = "not_applicable"
    comment_support: str = "not_supported"
    transcript_support: str = "not_supported"
    media_support: str = "not_supported"
    credential_requirement: str = CREDENTIAL_NONE
    live_manual_mode: str = "manual_operator_only"
    evidence_database_mapping: tuple[str, ...] = ()
    total_export_mapping: tuple[str, ...] = ()
    operator_approval_requirements: tuple[str, ...] = ()
    audit_status: str = AUDIT_STATUS_AUDIT_REQUIRED
    execution_status: str = EXECUTION_STATUS_NOT_YET_EXECUTED
    method_audit_metadata: Mapping[str, Any] = field(default_factory=dict)
    user_review_required: bool = True
    operator_approval_required: bool = True
    metadata_only: bool = True
    local_only: bool = True
    live_execution_performed: bool = False
    provider_call_performed: bool = False
    browser_automation_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceAdapterAuditRegistry:
    registry_id: str
    entries: tuple[SourceAdapterAuditEntry, ...]
    schema_version: str = SOURCE_ADAPTER_AUDIT_REGISTRY_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    live_execution_performed: bool = False
    provider_call_performed: bool = False
    browser_automation_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def adapter_count(self) -> int:
        return len({entry.adapter_id for entry in self.entries})

    @property
    def audit_required_count(self) -> int:
        return sum(1 for entry in self.entries if entry.audit_status == AUDIT_STATUS_AUDIT_REQUIRED)

    @property
    def not_yet_executed_count(self) -> int:
        return sum(1 for entry in self.entries if entry.execution_status == EXECUTION_STATUS_NOT_YET_EXECUTED)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["adapter_count"] = self.adapter_count
        data["audit_required_count"] = self.audit_required_count
        data["entry_count"] = self.entry_count
        data["not_yet_executed_count"] = self.not_yet_executed_count
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


def _adapter_by_id(adapters: Sequence[SourceAdapter], adapter_id: str) -> SourceAdapter | None:
    for adapter in adapters:
        if adapter.source_name == adapter_id:
            return adapter
    return None


def _profile(
    profile_id: str,
    profiles: Sequence[SourceMethodProfile],
    fallback: SourceMethodProfile,
) -> SourceMethodProfile:
    return find_source_method_profile(profile_id, profiles) or fallback


def _entry(
    *,
    adapter: SourceAdapter | None,
    profile: SourceMethodProfile,
    method_id: str,
    method_display_name: str,
    source_type: str,
    capture_method: str,
    required_artifacts: Iterable[str] = (),
    archive_strategy: str = "not_applicable",
    comment_support: str = "not_supported",
    transcript_support: str = "not_supported",
    media_support: str = "not_supported",
    credential_requirement: str = "",
    live_manual_mode: str = "manual_operator_only",
    evidence_database_mapping: Iterable[str] = (),
    total_export_mapping: Iterable[str] = (),
    operator_approval_requirements: Iterable[str] = (),
    audit_status: str = AUDIT_STATUS_AUDIT_REQUIRED,
    execution_status: str = EXECUTION_STATUS_NOT_YET_EXECUTED,
    method_audit_metadata: Mapping[str, Any] | None = None,
    notes: str = "",
) -> SourceAdapterAuditEntry:
    adapter_id = adapter.source_name if adapter is not None else profile.adapter_id
    adapter_display_name = (
        adapter.metadata.display_name if adapter is not None else profile.display_name
    )
    credential = credential_requirement or (
        adapter.metadata.credential_type if adapter is not None else CREDENTIAL_NONE
    )
    if credential == "api_key":
        credential = "credential_required_no_value"
    payload = {
        "adapter_id": adapter_id,
        "method_id": method_id,
        "profile_id": profile.profile_id,
        "schema_version": SOURCE_ADAPTER_AUDIT_REGISTRY_SCHEMA_VERSION,
    }
    return SourceAdapterAuditEntry(
        audit_entry_id="source_adapter_audit_" + _sha16(payload),
        adapter_id=adapter_id,
        adapter_display_name=adapter_display_name,
        method_id=method_id,
        method_profile_id=profile.profile_id,
        method_display_name=method_display_name,
        source_type=source_type,
        capture_method=capture_method,
        required_artifacts=_stable_tuple(required_artifacts or profile.expected_artifact_types),
        archive_strategy=archive_strategy,
        comment_support=comment_support,
        transcript_support=transcript_support,
        media_support=media_support,
        credential_requirement=credential,
        live_manual_mode=live_manual_mode,
        evidence_database_mapping=_stable_tuple(evidence_database_mapping),
        total_export_mapping=_stable_tuple(total_export_mapping),
        operator_approval_requirements=_stable_tuple(
            operator_approval_requirements or profile.required_operator_fields
        ),
        audit_status=audit_status,
        execution_status=execution_status,
        method_audit_metadata=dict(method_audit_metadata or {}),
        notes=notes,
    )


def build_source_adapter_audit_registry(
    *,
    adapters: Sequence[SourceAdapter] = AVAILABLE_SOURCE_ADAPTERS,
    profiles: Sequence[SourceMethodProfile] = SOURCE_METHOD_PROFILES,
) -> SourceAdapterAuditRegistry:
    """Build the durable adapter audit table for review-only Source Evidence work."""

    adapter_lookup = {adapter.source_name: adapter for adapter in adapters}
    msn_profile = _profile("msn_article_comments_shadow_manual_import", profiles, profiles[0])
    twitter_profile = _profile("twitter_x_post_reply_archive_fallback", profiles, profiles[1])
    twitter_public_profile = _profile("twitter_x_public_post_archive", profiles, twitter_profile)
    twitter_reply_profile = _profile("twitter_x_reply_thread_archive", profiles, twitter_profile)
    youtube_profile = _profile("youtube_media_transcript_comment", profiles, profiles[2])
    generic_profile = _profile("generic_article_comment_manual", profiles, profiles[3])
    generic_html_profile = _profile("generic_article_html", profiles, generic_profile)
    generic_comments_profile = _profile("generic_article_comments", profiles, generic_profile)
    manual_profile = _profile("manual_local_file_import", profiles, MANUAL_LOCAL_IMPORT_PROFILE)
    archive_only_profile = _profile("archive_only_import", profiles, manual_profile)

    shared_db_mapping = (
        "adapter_id",
        "capture_method_profile_id",
        "review_state",
        "source_url",
        "site_profile_id",
    )
    shared_export_mapping = (
        "planned_artifact_metadata",
        "review_manifest_metadata",
        "queue_review_metadata",
        "total_export_asset_metadata",
    )
    entries = (
        _entry(
            adapter=adapter_lookup.get("msn"),
            profile=msn_profile,
            method_id="msn_article_comments_shadow_manual_import",
            method_display_name="MSN article/comments manual observation",
            source_type="news_article",
            capture_method="manual_observation_and_fixture_metadata",
            required_artifacts=("ARTICLE_TEXT", "COMMENTS_JSONL", "RAW_HTML", "ARCHIVE_RESULT"),
            archive_strategy="wayback_archive_today_fallback_metadata_only",
            comment_support="manual_observation_supported",
            transcript_support="not_supported",
            media_support="manual_media_observation_metadata",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE,
            notes="MSN manual observation and extraction bundle metadata are wired; live capture remains approval-gated.",
        ),
        _entry(
            adapter=adapter_lookup.get("twitter_x"),
            profile=twitter_public_profile,
            method_id="twitter_x_public_post_archive",
            method_display_name="X/Twitter public post archive/import",
            source_type="public_microblog_post",
            capture_method="local_export_or_archive_reference_metadata",
            required_artifacts=("RAW_SIDECAR", "ARCHIVE_RESULT", "SCREENSHOT", "DOM_SNAPSHOT"),
            archive_strategy="operator_supplied_or_future_approved_wayback_archive_today_metadata",
            comment_support="reply_thread_separate_method",
            media_support="metadata_only_no_download",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_AUDIT_READY,
            method_audit_metadata={
                "archive_receipt_reference_policy": "archive_receipts and archive_url_references are typed grabbed-source references",
                "archive_submission_performed": False,
                "canonical_url_expectation": "https://x.com/{handle}/status/{status_id} or https://twitter.com/{handle}/status/{status_id} normalized without query/fragment",
                "evidence_database_dimensions": (
                    "adapter_id",
                    "method_id",
                    "audit_status",
                    "execution_status",
                    "archive_strategy",
                ),
                "manual_observation_reference_policy": "manual observation refs record operator-supplied post visibility/status notes only",
                "screenshot_snapshot_reference_policy": "screenshot/snapshot refs are accepted as metadata references only; capture is not performed",
                "total_export_sidecars": (
                    "source_adapter_audit_registry.json",
                    "source_grabbed_record.json",
                    "source_evidence_database_scan_result.json",
                ),
                "url_normalization_expectations": (
                    "http/https only",
                    "x.com/twitter.com host only",
                    "drop query and fragment",
                ),
            },
            notes="Public post/archive method audit is metadata-backed and audit-ready; no live X/Twitter, browser, archive, screenshot, download, or API execution is performed.",
        ),
        _entry(
            adapter=adapter_lookup.get("twitter_x"),
            profile=twitter_reply_profile,
            method_id="twitter_x_reply_thread_archive",
            method_display_name="X/Twitter reply thread archive/import",
            source_type="public_microblog_reply_thread",
            capture_method="local_export_or_archive_reference_metadata",
            required_artifacts=("COMMENTS_JSONL", "RAW_SIDECAR", "ARCHIVE_RESULT", "DOM_SNAPSHOT"),
            archive_strategy="operator_supplied_or_future_approved_archive_metadata",
            comment_support="manual_or_local_export_thread_metadata",
            media_support="metadata_only_no_download",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_AUDIT_READY,
            method_audit_metadata={
                "archive_fallback": "archive URLs may document parent/reply views as operator-supplied metadata only",
                "manual_observation_metadata": (
                    "visible reply count",
                    "deleted_or_unavailable_reply_state",
                    "sort/filter context",
                    "operator note",
                ),
                "parent_post_reference_policy": "parent post URL/status ID must be recorded when known",
                "reply_ids_policy": "reply IDs are accepted only as explicit supplied IDs; no automatic discovery",
                "thread_boundary_policy": "record parent status ID, included reply IDs, omitted/unknown range notes, and user_review_required completeness",
                "typed_reference_policy": "comment_reference_ids for reply/thread records, archive_url_references for archive views, manual_observation_reference_ids for operator notes",
            },
            notes="Reply-thread/archive method audit is metadata-backed and audit-ready; thread completeness remains user-review-required and not live-executed.",
        ),
        _entry(
            adapter=adapter_lookup.get("youtube"),
            profile=youtube_profile,
            method_id="youtube_media_transcript",
            method_display_name="YouTube media/transcript existing-output bridge",
            source_type="video_social_media",
            capture_method="existing_runtime_output_metadata_bridge",
            required_artifacts=("MEDIA_INVENTORY", "TRANSCRIPT"),
            archive_strategy="not_applicable_in_metadata_bridge",
            comment_support="separate_youtube_comments_method",
            transcript_support="existing_output_metadata_only",
            media_support="existing_output_metadata_only",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE,
            notes="Existing YouTube output status/counts can be represented; this method does not run YouTube runtime/API.",
        ),
        _entry(
            adapter=adapter_lookup.get("youtube"),
            profile=youtube_profile,
            method_id="youtube_comments",
            method_display_name="YouTube comments existing-output bridge",
            source_type="video_social_comments",
            capture_method="existing_runtime_output_metadata_bridge",
            required_artifacts=("COMMENTS_JSONL", "LIVECHAT_JSONL"),
            archive_strategy="not_applicable_in_metadata_bridge",
            comment_support="existing_output_metadata_only",
            transcript_support="not_supported",
            media_support="not_supported",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE,
            notes="Existing YouTube output status/counts can be represented; no runtime/API call is performed.",
        ),
        _entry(
            adapter=adapter_lookup.get("news_website"),
            profile=generic_html_profile,
            method_id="generic_article_html",
            method_display_name="Generic article HTML manual/import",
            source_type="generic_article_html",
            capture_method="manual_or_fixture_supplied_html_metadata",
            required_artifacts=("RAW_HTML", "FINAL_DOM", "ARTICLE_TEXT", "PAGE_OUTLINE", "SCREENSHOT", "ARCHIVE_RESULT"),
            archive_strategy="operator_supplied_or_future_approved_archive_check_metadata",
            comment_support="separate_generic_article_comments_method",
            media_support="metadata_only_no_download",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_AUDIT_READY,
            method_audit_metadata={
                "archive_fallback": "archive refs remain operator-supplied or future approval-gated provider receipts",
                "canonical_url_policy": "http/https canonical URL expected from adapter normalization or operator-supplied source URL",
                "html_snapshot_reference_policy": "raw/final DOM refs are metadata references; no browser capture is performed",
                "review_status": "USER_REVIEW_REQUIRED",
                "screenshot_snapshot_reference_policy": "screenshot and snapshot refs are typed metadata references only",
                "text_extraction_receipt_policy": "article text extraction refs are placeholder/receipt metadata until supplied content or site-specific extractor review",
            },
            notes="Generic article HTML method audit is metadata-backed and audit-ready; generic live scraping remains unimplemented.",
        ),
        _entry(
            adapter=adapter_lookup.get("news_website"),
            profile=generic_comments_profile,
            method_id="generic_article_comments",
            method_display_name="Generic article comments manual/import",
            source_type="generic_article_comments",
            capture_method="manual_or_fixture_supplied_comments_metadata",
            required_artifacts=("COMMENTS_TEXT", "COMMENTS_JSONL", "ARCHIVE_RESULT"),
            archive_strategy="operator_supplied_or_future_approved_archive_check_metadata",
            comment_support="manual_or_fixture_only_site_specific_selectors_audit_required",
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_AUDIT_READY,
            method_audit_metadata={
                "archive_fallback": "archive refs can be recorded as metadata; provider checks/submissions remain approval-gated",
                "comment_tree_boundary_policy": "record visible root/reply boundary and unknown/omitted ranges as review notes",
                "manual_observation_support": "operator-supplied comment presence/count/tree notes only",
                "selector_profile_notes": "site-specific selectors, shadow DOM, pagination, login/challenge and recycled-node handling remain audit_required before live execution",
                "site_specific_selector_status": "audit_required",
                "source_boundary_policy": "comments are separate from article text and must not be silently mixed into ARTICLE_TEXT",
            },
            notes="Generic comments method audit is metadata-backed and audit-ready, but site-specific selectors remain audit_required before any live execution.",
        ),
        _entry(
            adapter=None,
            profile=manual_profile,
            method_id="manual_local_import",
            method_display_name="Manual local file/imported-export review",
            source_type="manual_local_import",
            capture_method="user_supplied_local_file_metadata",
            required_artifacts=("RAW_SIDECAR", "EXTRACTED_TEXT", "MEDIA", "ARCHIVE_RESULT"),
            archive_strategy="operator_supplied_archive_reference_only",
            comment_support="format_specific_import_metadata",
            transcript_support="local_file_metadata_only",
            media_support="local_file_metadata_only",
            credential_requirement=CREDENTIAL_NONE,
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_SCAFFOLDED,
            notes="Manual/local imports are represented as review metadata without reading/moving evidence files.",
        ),
        _entry(
            adapter=None,
            profile=archive_only_profile,
            method_id="archive_only_import",
            method_display_name="Archive-only URL/reference import",
            source_type="archive_reference",
            capture_method="operator_supplied_archive_reference_metadata",
            required_artifacts=("ARCHIVE_RESULT", "RAW_SIDECAR"),
            archive_strategy="operator_supplied_no_provider_call",
            comment_support="not_supported",
            transcript_support="not_supported",
            media_support="not_supported",
            credential_requirement=CREDENTIAL_NONE,
            evidence_database_mapping=shared_db_mapping,
            total_export_mapping=shared_export_mapping,
            audit_status=AUDIT_STATUS_METADATA_AUDIT_READY,
            method_audit_metadata={
                "archive_url_required": True,
                "evidence_database_mapping": "original URL, archive URL, source archive type, retrieved metadata refs, and review/signoff state remain metadata-only dimensions",
                "no_live_site_requirement": True,
                "original_url_required": True,
                "provider_source_archive_type_policy": "operator supplied: wayback, archive_today, archivebox, WARC/WACZ, or other reviewed archive reference",
                "retrieved_metadata_reference_policy": "metadata reference only; importer does not retrieve archive content",
                "review_signoff_status": "USER_REVIEW_REQUIRED",
            },
            notes="Archive-only import method audit is metadata-backed and audit-ready; no provider lookup, live site retrieval, submission, or file movement is performed.",
        ),
    )
    sorted_entries = tuple(sorted(entries, key=lambda item: (item.adapter_id, item.method_id)))
    registry_payload = {
        "entry_ids": tuple(entry.audit_entry_id for entry in sorted_entries),
        "schema_version": SOURCE_ADAPTER_AUDIT_REGISTRY_SCHEMA_VERSION,
    }
    return SourceAdapterAuditRegistry(
        registry_id="source_adapter_audit_registry_" + _sha16(registry_payload),
        entries=sorted_entries,
    )


def source_adapter_audit_entries_requiring_review(
    registry: SourceAdapterAuditRegistry,
) -> tuple[SourceAdapterAuditEntry, ...]:
    return tuple(entry for entry in registry.entries if entry.audit_status == AUDIT_STATUS_AUDIT_REQUIRED)


def source_adapter_audit_entry_by_method(
    registry: SourceAdapterAuditRegistry,
    method_id: str,
) -> SourceAdapterAuditEntry | None:
    normalized = str(method_id or "").strip().lower()
    for entry in registry.entries:
        if entry.method_id.lower() == normalized:
            return entry
    return None


def validate_source_adapter_audit_registry(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_ADAPTER_AUDIT_REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported Source Adapter audit registry schema version")
    for required_true in ("metadata_only", "local_only", "sensitive_inference_prohibited"):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe Source Adapter audit registry flag: {required_true}")
    for required_false in (
        "live_execution_performed",
        "provider_call_performed",
        "browser_automation_performed",
        "archive_submission_performed",
        "download_performed",
        "file_move_performed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe Source Adapter audit registry flag: {required_false}")
    entries = data.get("entries", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("Source Adapter audit registry requires entries")
    seen_methods: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("Source Adapter audit entry must be an object")
        for required in ("audit_entry_id", "adapter_id", "method_id", "source_type", "capture_method"):
            if not str(entry.get(required) or "").strip():
                raise ValueError(f"Source Adapter audit entry missing required field: {required}")
        method_id = str(entry.get("method_id"))
        if method_id in seen_methods:
            raise ValueError(f"Duplicate Source Adapter audit method_id: {method_id}")
        seen_methods.add(method_id)
        for required_false in (
            "live_execution_performed",
            "provider_call_performed",
            "browser_automation_performed",
            "archive_submission_performed",
            "download_performed",
            "file_move_performed",
            "automatic_classification",
        ):
            if entry.get(required_false) is not False:
                raise ValueError(f"Unsafe Source Adapter audit entry flag: {required_false}")
        if entry.get("sensitive_inference_prohibited") is not True:
            raise ValueError("Source Adapter audit entry must prohibit sensitive inference")
        metadata = entry.get("method_audit_metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Source Adapter audit entry method metadata must be an object")
        for unsafe_key in (
            "live_execution_performed",
            "provider_call_performed",
            "browser_automation_performed",
            "archive_submission_performed",
            "download_performed",
            "file_move_performed",
            "automatic_classification",
        ):
            if metadata.get(unsafe_key) is True:
                raise ValueError(f"Unsafe Source Adapter audit method metadata flag: {unsafe_key}")


def source_adapter_audit_registry_to_json(registry: SourceAdapterAuditRegistry) -> str:
    return _stable_json(registry.to_dict(), pretty=True)
