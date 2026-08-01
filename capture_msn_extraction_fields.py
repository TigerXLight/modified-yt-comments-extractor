from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from capture_article import (
    ARTICLE_STATUS_EMPTY,
    ArticleExtractionResult,
    extract_article_text_from_html,
)
from capture_comments import CommentCaptureResult, CommentRecord, extract_comments_from_html
from capture_live_smoke_plan import (
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MSN_MANUAL_SMOKE_ADAPTER_FAMILY,
    MSN_MANUAL_SMOKE_APPROVED_SCOPES,
    MSN_MANUAL_SMOKE_SITE_LABEL,
    MSN_MANUAL_SMOKE_SOURCE_URL,
    ManualLiveSmokeObservationImport,
)
from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem


MSN_EXTRACTION_FIELD_SCHEMA_VERSION = "msn_extraction_fields.v1"
MSN_EXPORT_QUEUE_REVIEW_ITEM_SCHEMA_VERSION = "msn_extraction_export_review_item.v1"
MSN_EXTRACTION_FIELD_STATUS_USER_REVIEW_REQUIRED = "user_review_required"
MSN_EXPORT_QUEUE_REVIEW_STATUS_USER_REVIEW_REQUIRED = "USER_REVIEW_REQUIRED"
MSN_EXPORT_QUEUE_REVIEW_PROVENANCE_MANUAL_OPERATOR_ONLY = "MANUAL_OPERATOR_ONLY"
MSN_ARTICLE_FIELD_KIND = "article_semantic_text"
MSN_COMMENTS_FIELD_KIND = "comments_thread_records"
MSN_COMMENT_FIELD_KIND = "comment_thread_record"
MSN_MEDIA_FIELD_KIND = "manual_static_media_observation"
MSN_EXPORT_REVIEW_FIELD_KIND = "export_review_metadata"
MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT = "needs_manual_source_content"
MSN_EXTRACTION_STATUS_LOCAL_SUPPLIED_CONTENT = "local_supplied_content"
MSN_EXTRACTION_STATUS_MANUAL_OBSERVATION_LINKED = "manual_observation_linked"
MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY = "manual_observation_metadata_only"
MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT = "local_supplied_operator_content"
MSN_EXTRACTION_FIELD_SCOPE = (
    "MSN article/comment extraction field metadata for supplied local HTML and imported "
    "manual operator observations only; no fetch, browser, screenshot, OCR, archive, "
    "download, provider, credential, scraping, external process, or GUI behavior"
)

MSN_REJECTED_MANUAL_CLAIM_FIELDS = (
    "claims_archive_check",
    "claims_archive_checks",
    "claims_archive_submission",
    "claims_automated_capture",
    "claims_automatic_evidence_classification",
    "claims_browser_automation",
    "claims_completed_live_verification",
    "claims_credentials_cookies_accounts",
    "claims_downloaded_files",
    "claims_file_artifacts",
    "claims_file_exists",
    "claims_file_existence",
    "claims_network_capture",
    "claims_ocr",
    "claims_screenshot",
)

MSN_REJECTED_TRUE_REVIEW_FIELDS = (
    "archive_provider_result_claimed",
    "artifact_file_claimed",
    "artifact_files_claimed",
    "automatic_classification",
    "automatic_classification_performed",
    "browser_automation_claimed",
    "downloaded_files_claimed",
    "downloaded_media_claimed",
    "file_existence_claimed",
    "live_verification_claimed",
    "media_files_claimed",
    "muxing_claimed",
    "network_capture_claimed",
    "ocr_claimed",
    "playback_capture_claimed",
    "screenshot_claimed",
)


@dataclass(frozen=True)
class MsnCommentThreadRecordField:
    comment_id: str
    text: str
    author: str = ""
    parent_id: str = ""
    depth: int = 0
    thread_id: str = ""
    posted_at: str = ""
    observed_at: str = ""
    reaction_count: int = 0
    reply_count: int = 0
    permalink: str = ""
    source_order: int = 0
    loaded_order: int = 0
    status: str = ""
    capture_method: str = ""
    raw_reference: str = ""
    source_channel: str = "comments"
    field_kind: str = MSN_COMMENT_FIELD_KIND
    article_text_included: bool = False
    user_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_text_included": self.article_text_included,
            "author": self.author,
            "capture_method": self.capture_method,
            "comment_id": self.comment_id,
            "depth": self.depth,
            "field_kind": self.field_kind,
            "loaded_order": self.loaded_order,
            "observed_at": self.observed_at,
            "parent_id": self.parent_id,
            "permalink": self.permalink,
            "posted_at": self.posted_at,
            "raw_reference": self.raw_reference,
            "reaction_count": self.reaction_count,
            "reply_count": self.reply_count,
            "source_channel": self.source_channel,
            "source_order": self.source_order,
            "status": self.status,
            "text": self.text,
            "thread_id": self.thread_id,
            "user_review_required": self.user_review_required,
        }


@dataclass(frozen=True)
class MsnArticleCommentExtractionFieldBundle:
    source_url: str
    article: Mapping[str, Any]
    comments: Mapping[str, Any]
    media: Mapping[str, Any] | None = None
    export_review: Mapping[str, Any] | None = None
    manual_observation_scopes: tuple[str, ...] = ()
    manual_observation_count: int = 0
    user_review_required: bool = True
    manual_operator_only: bool = True
    automation_performed: bool = False
    network_actions_performed: str = "none"
    artifact_files_claimed: bool = False
    site_label: str = MSN_MANUAL_SMOKE_SITE_LABEL
    adapter_family: str = MSN_MANUAL_SMOKE_ADAPTER_FAMILY
    approved_manual_scopes: tuple[str, ...] = MSN_MANUAL_SMOKE_APPROVED_SCOPES
    schema_version: str = MSN_EXTRACTION_FIELD_SCHEMA_VERSION
    scope: str = MSN_EXTRACTION_FIELD_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_family": self.adapter_family,
            "approved_manual_scopes": list(self.approved_manual_scopes),
            "article": _dict_value(dict(self.article)),
            "artifact_files_claimed": self.artifact_files_claimed,
            "automation_performed": self.automation_performed,
            "comments": _dict_value(dict(self.comments)),
            "export_review": _dict_value(dict(self.export_review or {})),
            "manual_observation_count": self.manual_observation_count,
            "manual_observation_scopes": list(self.manual_observation_scopes),
            "manual_operator_only": self.manual_operator_only,
            "media": _dict_value(dict(self.media or {})),
            "network_actions_performed": self.network_actions_performed,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "site_label": self.site_label,
            "source_url": self.source_url,
            "user_review_required": self.user_review_required,
        }


@dataclass(frozen=True)
class MsnExtractionExportQueueReviewItem:
    item_id: str
    site_label: str
    source_url: str
    source_kind: str
    review_status: str
    provenance_status: str
    article_section: Mapping[str, Any]
    comments_section: Mapping[str, Any]
    media_section: Mapping[str, Any]
    export_review_section: Mapping[str, Any]
    approved_manual_scope_ids: tuple[str, ...]
    observed_manual_scope_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    manual_operator_only: bool = True
    user_review_required: bool = True
    artifact_files_claimed: bool = False
    file_existence_claimed: bool = False
    live_verification_claimed: bool = False
    automatic_classification: bool = False
    browser_automation_claimed: bool = False
    network_capture_claimed: bool = False
    archive_provider_result_claimed: bool = False
    downloaded_media_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    schema_version: str = MSN_EXPORT_QUEUE_REVIEW_ITEM_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_manual_scope_ids": list(self.approved_manual_scope_ids),
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "article_section": _dict_value(dict(self.article_section)),
            "artifact_files_claimed": self.artifact_files_claimed,
            "automatic_classification": self.automatic_classification,
            "browser_automation_claimed": self.browser_automation_claimed,
            "comments_section": _dict_value(dict(self.comments_section)),
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "export_review_section": _dict_value(dict(self.export_review_section)),
            "file_existence_claimed": self.file_existence_claimed,
            "item_id": self.item_id,
            "live_verification_claimed": self.live_verification_claimed,
            "manual_operator_only": self.manual_operator_only,
            "media_section": _dict_value(dict(self.media_section)),
            "network_capture_claimed": self.network_capture_claimed,
            "observed_manual_scope_ids": list(self.observed_manual_scope_ids),
            "ocr_claimed": self.ocr_claimed,
            "provenance_status": self.provenance_status,
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "screenshot_claimed": self.screenshot_claimed,
            "site_label": self.site_label,
            "source_kind": self.source_kind,
            "source_url": self.source_url,
            "user_review_required": self.user_review_required,
            "validation_errors": list(self.validation_errors),
            "warnings": list(self.warnings),
        }

    def to_evidence_queue_item(self) -> EvidenceQueueItem:
        return EvidenceQueueItem(
            item_id=self.item_id,
            item_role=EvidenceItemRole.MANUAL_EVIDENCE_NOTE,
            display_name=f"{self.site_label} extraction review metadata",
            source_url=self.source_url,
            local_path="",
            item_status=EvidenceItemStatus.NEEDS_REVIEW,
            created_at_utc="",
            updated_at_utc="",
            user_notes=json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )


def _dict_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_dict_value(item) for item in value]
    if isinstance(value, list):
        return [_dict_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dict_value(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _validate_msn_source_url(source_url: str) -> str:
    if source_url != MSN_MANUAL_SMOKE_SOURCE_URL:
        raise ValueError(
            "MSN extraction fields are approved only for " + MSN_MANUAL_SMOKE_SOURCE_URL
        )
    return source_url


def _accepted_manual_observation_scopes(
    manual_observation_imports: Iterable[ManualLiveSmokeObservationImport],
) -> tuple[str, ...]:
    scopes: list[str] = []
    for imported in manual_observation_imports:
        if not imported.is_accepted or imported.observation is None:
            continue
        observation = imported.observation
        if observation.source_url != MSN_MANUAL_SMOKE_SOURCE_URL:
            continue
        if observation.site_label != MSN_MANUAL_SMOKE_SITE_LABEL:
            continue
        if observation.action_scope_id not in MSN_MANUAL_SMOKE_APPROVED_SCOPES:
            continue
        scopes.append(observation.action_scope_id)
    return tuple(dict.fromkeys(scopes))


def _observation_to_mapping(value: ManualLiveSmokeObservationImport | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value, ManualLiveSmokeObservationImport):
        if not value.is_accepted or value.observation is None:
            return {}
        return value.observation.to_dict()
    return value


def _stable_json(value: Mapping[str, Any]) -> str:
    return json.dumps(_dict_value(dict(value)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_review_item_id(data: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]
    return f"msn_extraction_review_{digest}"


def _validate_manual_observation_mappings(
    manual_observation_imports: Iterable[ManualLiveSmokeObservationImport | Mapping[str, Any]],
) -> tuple[tuple[Mapping[str, Any], ...], tuple[str, ...]]:
    accepted: list[Mapping[str, Any]] = []
    errors: list[str] = []
    for index, raw in enumerate(manual_observation_imports, start=1):
        observation = _observation_to_mapping(raw)
        if not observation:
            continue
        site_label = str(observation.get("site_label") or "")
        source_url = str(observation.get("source_url") or "")
        action_scope_id = str(observation.get("action_scope_id") or "")
        if site_label != MSN_MANUAL_SMOKE_SITE_LABEL:
            errors.append(f"manual observation {index}: non-MSN site label rejected")
        if source_url != MSN_MANUAL_SMOKE_SOURCE_URL:
            errors.append(f"manual observation {index}: unapproved MSN source URL rejected")
        if action_scope_id not in MSN_MANUAL_SMOKE_APPROVED_SCOPES:
            errors.append(f"manual observation {index}: unapproved scope rejected: {action_scope_id}")
        for claim_field in MSN_REJECTED_MANUAL_CLAIM_FIELDS:
            if bool(observation.get(claim_field)):
                errors.append(f"manual observation {index}: rejected claim {claim_field}")
        accepted.append(observation)
    return tuple(accepted), tuple(errors)


def _observed_status_by_scope(
    observations: Iterable[Mapping[str, Any]],
    scope_id: str,
) -> str:
    for observation in observations:
        if observation.get("action_scope_id") == scope_id:
            return str(observation.get("result_status") or "")
    return "unknown"


def _manual_notes_for_scope(
    observations: Iterable[Mapping[str, Any]],
    scope_id: str,
) -> tuple[str, ...]:
    return tuple(
        str(observation.get("notes") or "")
        for observation in observations
        if observation.get("action_scope_id") == scope_id and observation.get("notes")
    )


def _comment_to_msn_field(comment: CommentRecord) -> MsnCommentThreadRecordField:
    return MsnCommentThreadRecordField(
        comment_id=comment.comment_id,
        text=comment.text,
        author=comment.author,
        parent_id=comment.parent_id,
        depth=comment.depth,
        thread_id=comment.thread_id,
        posted_at=comment.posted_at,
        observed_at=comment.observed_at,
        reaction_count=comment.reaction_count,
        reply_count=comment.reply_count,
        permalink=comment.permalink,
        source_order=comment.source_order,
        loaded_order=comment.loaded_order,
        status=comment.status,
        capture_method=comment.capture_method,
        raw_reference=comment.raw_reference,
    )


def article_result_to_msn_fields(
    result: ArticleExtractionResult,
    *,
    source_url: str = MSN_MANUAL_SMOKE_SOURCE_URL,
) -> dict[str, Any]:
    source_url = _validate_msn_source_url(source_url)
    return {
        "comments_region_status": "excluded_from_article_text",
        "confidence": result.confidence,
        "contamination_signals": list(result.contamination_signals),
        "excluded_region_counts": dict(result.excluded_region_counts or {}),
        "field_kind": MSN_ARTICLE_FIELD_KIND,
        "manual_operator_only": True,
        "method": result.method,
        "network_actions_performed": "none",
        "separated_from_comments": True,
        "source_channel": "webpage_article",
        "source_url": source_url,
        "status": result.status,
        "text": result.text,
        "title": result.title,
        "user_review_required": True,
        "warnings": list(result.warnings),
    }


def comments_result_to_msn_fields(
    result: CommentCaptureResult,
    *,
    source_url: str = MSN_MANUAL_SMOKE_SOURCE_URL,
) -> dict[str, Any]:
    source_url = _validate_msn_source_url(source_url)
    thread_records = tuple(_comment_to_msn_field(comment) for comment in result.comments)
    return {
        "article_text_included": False,
        "capture_routes": list(result.capture_routes),
        "challenge_required": result.challenge_required,
        "comment_count": len(thread_records),
        "completeness": result.completeness,
        "cursor": result.cursor,
        "duplicate_comment_ids": list(result.duplicate_comment_ids),
        "field_kind": MSN_COMMENTS_FIELD_KIND,
        "incremental_batches": result.incremental_batches,
        "login_required": result.login_required,
        "manual_operator_only": True,
        "network_actions_performed": "none",
        "separated_from_article": True,
        "source_channel": "comments_module",
        "source_url": source_url,
        "status": result.status,
        "stop_reason": result.stop_reason,
        "thread_records": [field.to_dict() for field in thread_records],
        "user_review_required": True,
        "warnings": list(result.warnings),
    }


def _metadata_only_article_fields(
    *,
    source_url: str,
    observations: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    return {
        "comments_region_status": "not_extracted",
        "content_source": MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY,
        "field_kind": MSN_ARTICLE_FIELD_KIND,
        "manual_notes": list(_manual_notes_for_scope(observations, MANUAL_ACTION_SCOPE_WEBPAGE)),
        "manual_observation_status": _observed_status_by_scope(
            observations,
            MANUAL_ACTION_SCOPE_WEBPAGE,
        ),
        "manual_operator_only": True,
        "network_actions_performed": "none",
        "requires_manual_source_content": True,
        "separated_from_comments": True,
        "source_channel": "webpage_article",
        "source_url": source_url,
        "status": MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT,
        "text": "",
        "title": "",
        "user_review_required": True,
        "warnings": [
            "Manual MSN webpage observation exists, but no local supplied article HTML/text was provided.",
        ],
    }


def _metadata_only_comments_fields(
    *,
    source_url: str,
    observations: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    comments_status = _observed_status_by_scope(observations, MANUAL_ACTION_SCOPE_COMMENTS)
    return {
        "article_text_included": False,
        "comment_count": 0,
        "comments_present_observed": comments_status == "observed",
        "content_source": MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY,
        "field_kind": MSN_COMMENTS_FIELD_KIND,
        "manual_notes": list(_manual_notes_for_scope(observations, MANUAL_ACTION_SCOPE_COMMENTS)),
        "manual_observation_status": comments_status,
        "manual_operator_only": True,
        "network_actions_performed": "none",
        "requires_manual_source_content": True,
        "separated_from_article": True,
        "source_channel": "comments_module",
        "source_url": source_url,
        "status": MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT,
        "thread_records": [],
        "user_review_required": True,
        "warnings": [
            "Manual MSN comments observation exists, but no local supplied comment records/HTML were provided.",
        ],
    }


def _media_review_fields(observations: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    media_status = _observed_status_by_scope(observations, MANUAL_ACTION_SCOPE_MEDIA)
    return {
        "downloaded_files_claimed": False,
        "field_kind": MSN_MEDIA_FIELD_KIND,
        "manual_notes": list(_manual_notes_for_scope(observations, MANUAL_ACTION_SCOPE_MEDIA)),
        "manual_observation_status": media_status,
        "manual_operator_only": True,
        "media_status": MSN_EXTRACTION_STATUS_MANUAL_OBSERVATION_LINKED,
        "network_actions_performed": "none",
        "playback_capture_claimed": False,
        "static_media_observed": media_status == "observed",
        "user_review_required": True,
    }


def _export_review_fields(observations: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    return {
        "artifact_file_claimed": False,
        "automatic_classification_performed": False,
        "export_queue_status": MSN_EXTRACTION_FIELD_STATUS_USER_REVIEW_REQUIRED,
        "field_kind": MSN_EXPORT_REVIEW_FIELD_KIND,
        "file_existence_claimed": False,
        "manual_notes": list(_manual_notes_for_scope(observations, MANUAL_ACTION_SCOPE_EXPORT_QUEUE)),
        "manual_observation_status": _observed_status_by_scope(
            observations,
            MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
        ),
        "manual_operator_only": True,
        "network_actions_performed": "none",
        "user_review_required": True,
    }


def _article_fields_from_supplied_text(
    *,
    supplied_article_text: str,
    source_url: str,
) -> dict[str, Any]:
    text = str(supplied_article_text or "").strip()
    result = ArticleExtractionResult(
        source_url=source_url,
        status=MSN_EXTRACTION_STATUS_LOCAL_SUPPLIED_CONTENT if text else ARTICLE_STATUS_EMPTY,
        text=text,
        method="local_supplied_operator_text",
        confidence=1.0 if text else 0.0,
        warnings=() if text else ("No local supplied article text was provided.",),
    )
    fields = article_result_to_msn_fields(result, source_url=source_url)
    fields["content_source"] = MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    fields["requires_manual_source_content"] = False if text else True
    return fields


def _comments_fields_from_supplied_records(
    *,
    supplied_comment_records: Iterable[CommentRecord | Mapping[str, Any]],
    source_url: str,
) -> dict[str, Any]:
    comments: list[CommentRecord] = []
    for index, record in enumerate(supplied_comment_records, start=1):
        if isinstance(record, CommentRecord):
            comments.append(record)
            continue
        comments.append(
            CommentRecord(
                comment_id=str(record.get("comment_id") or record.get("id") or f"comment-{index}"),
                text=str(record.get("text") or ""),
                author=str(record.get("author") or ""),
                parent_id=str(record.get("parent_id") or ""),
                depth=int(record.get("depth") or 0),
                thread_id=str(record.get("thread_id") or ""),
                posted_at=str(record.get("posted_at") or ""),
                observed_at=str(record.get("observed_at") or ""),
                reaction_count=int(record.get("reaction_count") or 0),
                reply_count=int(record.get("reply_count") or 0),
                permalink=str(record.get("permalink") or ""),
                source_order=int(record.get("source_order") or index),
                loaded_order=int(record.get("loaded_order") or index),
                status=str(record.get("status") or ""),
                capture_method=str(record.get("capture_method") or "local_supplied_operator_content"),
                raw_reference=str(record.get("raw_reference") or ""),
            )
        )
    result = CommentCaptureResult(
        source_url=source_url,
        status=MSN_EXTRACTION_STATUS_LOCAL_SUPPLIED_CONTENT,
        completeness="user_review_required",
        comments=tuple(comments),
        capture_routes=("local_supplied_operator_content",),
        warnings=(),
    )
    fields = comments_result_to_msn_fields(result, source_url=source_url)
    fields["content_source"] = MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    fields["requires_manual_source_content"] = False
    fields["comments_present_observed"] = bool(comments)
    return fields


def build_msn_article_comment_extraction_field_bundle(
    article_result: ArticleExtractionResult,
    comments_result: CommentCaptureResult,
    *,
    source_url: str = MSN_MANUAL_SMOKE_SOURCE_URL,
    manual_observation_imports: Iterable[ManualLiveSmokeObservationImport] = (),
) -> MsnArticleCommentExtractionFieldBundle:
    source_url = _validate_msn_source_url(source_url)
    accepted_scopes = _accepted_manual_observation_scopes(manual_observation_imports)
    return MsnArticleCommentExtractionFieldBundle(
        source_url=source_url,
        article=article_result_to_msn_fields(article_result, source_url=source_url),
        comments=comments_result_to_msn_fields(comments_result, source_url=source_url),
        manual_observation_scopes=accepted_scopes,
        manual_observation_count=len(accepted_scopes),
    )


def build_msn_manual_observation_extraction_review_bundle(
    *,
    manual_observation_imports: Iterable[ManualLiveSmokeObservationImport | Mapping[str, Any]],
    source_url: str = MSN_MANUAL_SMOKE_SOURCE_URL,
    site_label: str = MSN_MANUAL_SMOKE_SITE_LABEL,
    supplied_html: str = "",
    supplied_article_text: str = "",
    supplied_comments_html: str = "",
    supplied_comment_records: Iterable[CommentRecord | Mapping[str, Any]] = (),
) -> MsnArticleCommentExtractionFieldBundle:
    """Link imported MSN manual observations to extraction/review metadata.

    Manual observations alone never become extracted article/comment content.
    Local supplied HTML/text/comment records can populate the existing
    extraction fields, but the resulting bundle remains manual-operator-only
    and user-review-required.
    """

    if site_label != MSN_MANUAL_SMOKE_SITE_LABEL:
        raise ValueError("MSN manual observation integration rejects non-MSN site labels")
    source_url = _validate_msn_source_url(source_url)
    observations, errors = _validate_manual_observation_mappings(manual_observation_imports)
    if errors:
        raise ValueError("; ".join(errors))
    accepted_scopes = tuple(
        dict.fromkeys(str(observation.get("action_scope_id") or "") for observation in observations)
    )
    invalid_scopes = tuple(scope for scope in accepted_scopes if scope not in MSN_MANUAL_SMOKE_APPROVED_SCOPES)
    if invalid_scopes:
        raise ValueError("MSN manual observation integration rejects unapproved scopes")

    article: dict[str, Any]
    comments: dict[str, Any]
    if supplied_html:
        article = article_result_to_msn_fields(
            extract_article_text_from_html(supplied_html, source_url=source_url),
            source_url=source_url,
        )
        article["content_source"] = MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
        article["requires_manual_source_content"] = False
        comments_source = supplied_comments_html or supplied_html
        comments = comments_result_to_msn_fields(
            extract_comments_from_html(comments_source, source_url=source_url),
            source_url=source_url,
        )
        comments["content_source"] = MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
        comments["requires_manual_source_content"] = False
        comments["comments_present_observed"] = bool(comments.get("thread_records"))
    else:
        article = (
            _article_fields_from_supplied_text(
                supplied_article_text=supplied_article_text,
                source_url=source_url,
            )
            if supplied_article_text
            else _metadata_only_article_fields(source_url=source_url, observations=observations)
        )
        supplied_records_tuple = tuple(supplied_comment_records)
        comments = (
            _comments_fields_from_supplied_records(
                supplied_comment_records=supplied_records_tuple,
                source_url=source_url,
            )
            if supplied_records_tuple
            else _metadata_only_comments_fields(source_url=source_url, observations=observations)
        )

    return MsnArticleCommentExtractionFieldBundle(
        source_url=source_url,
        article=article,
        comments=comments,
        media=_media_review_fields(observations),
        export_review=_export_review_fields(observations),
        manual_observation_scopes=accepted_scopes,
        manual_observation_count=len(accepted_scopes),
    )


def _tri_state_from_manual_status(status: str) -> bool | str:
    if status == "observed":
        return True
    if status == "not_observed":
        return False
    return "unknown"


def _has_article_text(article: Mapping[str, Any]) -> bool:
    return bool(str(article.get("text") or "").strip())


def _has_extracted_comments(comments: Mapping[str, Any]) -> bool:
    return int(comments.get("comment_count") or 0) > 0 and bool(comments.get("thread_records") or ())


def _section_content_source(section: Mapping[str, Any]) -> str:
    return str(section.get("content_source") or MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY)


def _article_review_section(article: Mapping[str, Any]) -> dict[str, Any]:
    has_text = _has_article_text(article)
    requires_manual = bool(article.get("requires_manual_source_content") or not has_text)
    missing = []
    if requires_manual:
        missing.append("local_supplied_article_source_content")
    return {
        "article_content_source": _section_content_source(article),
        "article_requires_manual_source_content": requires_manual,
        "article_status": str(article.get("status") or ""),
        "field_kind": str(article.get("field_kind") or MSN_ARTICLE_FIELD_KIND),
        "has_article_text": has_text,
        "local_supplied_content_present": _section_content_source(article)
        == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
        and has_text,
        "missing_content_indicators": missing,
        "separated_from_comments": bool(article.get("separated_from_comments", True)),
        "user_review_required": True,
    }


def _comments_review_section(comments: Mapping[str, Any]) -> dict[str, Any]:
    has_comments = _has_extracted_comments(comments)
    requires_manual = bool(comments.get("requires_manual_source_content") or not has_comments)
    missing = []
    if requires_manual:
        missing.append("local_supplied_comment_source_content")
    observed_value = comments.get("comments_present_observed")
    if observed_value is True:
        observed: bool | str = True
    elif observed_value is False and comments.get("manual_observation_status") == "not_observed":
        observed = False
    else:
        observed = "unknown"
    return {
        "article_text_included": bool(comments.get("article_text_included", False)),
        "comment_count": int(comments.get("comment_count") or 0) if has_comments else 0,
        "comments_content_source": _section_content_source(comments),
        "comments_panel_observed": observed,
        "comments_requires_manual_source_content": requires_manual,
        "comments_status": str(comments.get("status") or ""),
        "field_kind": str(comments.get("field_kind") or MSN_COMMENTS_FIELD_KIND),
        "has_extracted_comments": has_comments,
        "local_supplied_content_present": _section_content_source(comments)
        == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
        and has_comments,
        "missing_content_indicators": missing,
        "separated_from_article": bool(comments.get("separated_from_article", True)),
        "user_review_required": True,
    }


def _media_review_section(media: Mapping[str, Any]) -> dict[str, Any]:
    manual_status = str(media.get("manual_observation_status") or "")
    return {
        "downloaded_media_claimed": False,
        "field_kind": str(media.get("field_kind") or MSN_MEDIA_FIELD_KIND),
        "manual_observation_status": manual_status or "unknown",
        "media_downloaded": False,
        "media_files_claimed": False,
        "muxing_claimed": False,
        "playback_capture_claimed": False,
        "static_media_observed": _tri_state_from_manual_status(manual_status),
        "user_review_required": True,
    }


def _export_review_section(export_review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_files_claimed": False,
        "automatic_classification": False,
        "field_kind": str(export_review.get("field_kind") or MSN_EXPORT_REVIEW_FIELD_KIND),
        "file_existence_claimed": False,
        "live_verification_claimed": False,
        "manual_operator_only": True,
        "queue_status": MSN_EXPORT_QUEUE_REVIEW_STATUS_USER_REVIEW_REQUIRED,
        "user_review_required": True,
    }


def _validate_bundle_for_export_review_item(
    bundle: MsnArticleCommentExtractionFieldBundle,
) -> tuple[str, ...]:
    data = bundle.to_dict()
    errors: list[str] = []
    if data["site_label"] != MSN_MANUAL_SMOKE_SITE_LABEL:
        errors.append("MSN export review item rejects non-MSN site labels")
    if data["source_url"] != MSN_MANUAL_SMOKE_SOURCE_URL:
        errors.append("MSN export review item rejects unapproved source URL")
    for scope in data["manual_observation_scopes"]:
        if scope not in MSN_MANUAL_SMOKE_APPROVED_SCOPES:
            errors.append(f"MSN export review item rejects unapproved scope: {scope}")
    if bool(data.get("artifact_files_claimed")):
        errors.append("MSN export review item rejects artifact file claims")

    def scan_claims(value: Any, path: str = "bundle") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if (
                    key in MSN_REJECTED_MANUAL_CLAIM_FIELDS
                    or key in MSN_REJECTED_TRUE_REVIEW_FIELDS
                ) and bool(item):
                    errors.append(f"MSN export review item rejects unsafe claim {path}.{key}")
                scan_claims(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                scan_claims(item, f"{path}[{index}]")

    scan_claims(data)
    return tuple(dict.fromkeys(errors))


def build_export_review_item_from_msn_extraction_bundle(
    bundle: MsnArticleCommentExtractionFieldBundle,
    *,
    validation_errors: Iterable[str] = (),
) -> MsnExtractionExportQueueReviewItem:
    validation = tuple(validation_errors) + _validate_bundle_for_export_review_item(bundle)
    if validation:
        raise ValueError("; ".join(tuple(dict.fromkeys(validation))))

    data = bundle.to_dict()
    article_section = _article_review_section(data["article"])
    comments_section = _comments_review_section(data["comments"])
    media_section = _media_review_section(data["media"])
    export_review_section = _export_review_section(data["export_review"])
    observed_scopes = tuple(sorted(str(scope) for scope in data["manual_observation_scopes"]))
    approved_scopes = tuple(sorted(str(scope) for scope in data["approved_manual_scopes"]))
    stable_basis = {
        "approved_manual_scope_ids": approved_scopes,
        "article_section": article_section,
        "comments_section": comments_section,
        "export_review_section": export_review_section,
        "media_section": media_section,
        "observed_manual_scope_ids": observed_scopes,
        "site_label": data["site_label"],
        "source_kind": "msn_article_manual_operator_extraction_review",
        "source_url": data["source_url"],
    }
    warnings = (
        "USER_REVIEW_REQUIRED",
        "MANUAL_OPERATOR_ONLY",
        "Metadata-only manual observations do not prove extracted article/comment content.",
    )
    return MsnExtractionExportQueueReviewItem(
        item_id=_stable_review_item_id(stable_basis),
        site_label=data["site_label"],
        source_url=data["source_url"],
        source_kind="msn_article_manual_operator_extraction_review",
        review_status=MSN_EXPORT_QUEUE_REVIEW_STATUS_USER_REVIEW_REQUIRED,
        provenance_status=MSN_EXPORT_QUEUE_REVIEW_PROVENANCE_MANUAL_OPERATOR_ONLY,
        article_section=article_section,
        comments_section=comments_section,
        media_section=media_section,
        export_review_section=export_review_section,
        approved_manual_scope_ids=approved_scopes,
        observed_manual_scope_ids=observed_scopes,
        warnings=tuple(sorted(warnings)),
    )


def convert_msn_extraction_bundle_to_export_queue_review_item(
    bundle: MsnArticleCommentExtractionFieldBundle,
) -> MsnExtractionExportQueueReviewItem:
    return build_export_review_item_from_msn_extraction_bundle(bundle)


def msn_extraction_review_bundle_to_evidence_queue_item(
    bundle: MsnArticleCommentExtractionFieldBundle,
) -> EvidenceQueueItem:
    return build_export_review_item_from_msn_extraction_bundle(bundle).to_evidence_queue_item()


def msn_extraction_review_bundle_to_export_queue_metadata(
    bundle: MsnArticleCommentExtractionFieldBundle,
) -> dict[str, Any]:
    data = bundle.to_dict()
    review_item = build_export_review_item_from_msn_extraction_bundle(bundle)
    return {
        "artifact_file_claimed": False,
        "artifact_files_claimed": False,
        "article_status": data["article"].get("status", ""),
        "automatic_classification_performed": False,
        "browser_or_download_command": "",
        "comments_status": data["comments"].get("status", ""),
        "export_queue_status": MSN_EXTRACTION_FIELD_STATUS_USER_REVIEW_REQUIRED,
        "file_existence_claimed": False,
        "manual_observation_scopes": data["manual_observation_scopes"],
        "manual_operator_only": True,
        "network_actions_performed": "none",
        "provider_or_archive_action": "none",
        "queue_review_item": review_item.to_dict(),
        "source_url": data["source_url"],
        "user_review_required": True,
    }


def extract_msn_article_comment_fields_from_supplied_html(
    *,
    article_html: str,
    comments_html: str = "",
    source_url: str = MSN_MANUAL_SMOKE_SOURCE_URL,
    manual_observation_imports: Iterable[ManualLiveSmokeObservationImport] = (),
) -> MsnArticleCommentExtractionFieldBundle:
    """Build MSN extraction fields from caller-supplied HTML only.

    This helper intentionally performs no network request, browser launch,
    screenshot/OCR, archive lookup, download, or external command.  It is a
    deterministic field-shaping layer for the existing supplied-HTML article
    and comments extractors plus imported manual operator metadata.
    """
    source_url = _validate_msn_source_url(source_url)
    comments_source_html = comments_html if comments_html else article_html
    article_result = extract_article_text_from_html(article_html, source_url=source_url)
    comments_result = extract_comments_from_html(comments_source_html, source_url=source_url)
    return build_msn_article_comment_extraction_field_bundle(
        article_result,
        comments_result,
        source_url=source_url,
        manual_observation_imports=manual_observation_imports,
    )


__all__ = [
    "MSN_ARTICLE_FIELD_KIND",
    "MSN_COMMENT_FIELD_KIND",
    "MSN_COMMENTS_FIELD_KIND",
    "MSN_EXTRACTION_FIELD_SCHEMA_VERSION",
    "MSN_EXTRACTION_FIELD_SCOPE",
    "MSN_EXTRACTION_FIELD_STATUS_USER_REVIEW_REQUIRED",
    "MsnArticleCommentExtractionFieldBundle",
    "MsnCommentThreadRecordField",
    "MsnExtractionExportQueueReviewItem",
    "article_result_to_msn_fields",
    "build_export_review_item_from_msn_extraction_bundle",
    "build_msn_article_comment_extraction_field_bundle",
    "build_msn_manual_observation_extraction_review_bundle",
    "comments_result_to_msn_fields",
    "convert_msn_extraction_bundle_to_export_queue_review_item",
    "extract_msn_article_comment_fields_from_supplied_html",
    "msn_extraction_review_bundle_to_evidence_queue_item",
    "msn_extraction_review_bundle_to_export_queue_metadata",
]
