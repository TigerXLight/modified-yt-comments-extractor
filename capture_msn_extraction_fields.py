from __future__ import annotations

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


MSN_EXTRACTION_FIELD_SCHEMA_VERSION = "msn_extraction_fields.v1"
MSN_EXTRACTION_FIELD_STATUS_USER_REVIEW_REQUIRED = "user_review_required"
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
    "claims_file_exists",
    "claims_file_existence",
    "claims_network_capture",
    "claims_ocr",
    "claims_screenshot",
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


def msn_extraction_review_bundle_to_export_queue_metadata(
    bundle: MsnArticleCommentExtractionFieldBundle,
) -> dict[str, Any]:
    data = bundle.to_dict()
    return {
        "artifact_file_claimed": False,
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
    "article_result_to_msn_fields",
    "build_msn_article_comment_extraction_field_bundle",
    "build_msn_manual_observation_extraction_review_bundle",
    "comments_result_to_msn_fields",
    "extract_msn_article_comment_fields_from_supplied_html",
    "msn_extraction_review_bundle_to_export_queue_metadata",
]
