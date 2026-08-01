from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from capture_article import ArticleExtractionResult, extract_article_text_from_html
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
MSN_EXTRACTION_FIELD_SCOPE = (
    "MSN article/comment extraction field metadata for supplied local HTML and imported "
    "manual operator observations only; no fetch, browser, screenshot, OCR, archive, "
    "download, provider, credential, scraping, external process, or GUI behavior"
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
            "manual_observation_count": self.manual_observation_count,
            "manual_observation_scopes": list(self.manual_observation_scopes),
            "manual_operator_only": self.manual_operator_only,
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
    "comments_result_to_msn_fields",
    "extract_msn_article_comment_fields_from_supplied_html",
]
