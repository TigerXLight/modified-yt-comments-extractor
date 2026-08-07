from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from capture_msn_manual_article_extraction import MSNManualArticleExtraction
from capture_msn_manual_comments_extraction import MSNManualCommentsExtraction


MSN_MANUAL_CAPTURE_BUNDLE_SCHEMA_VERSION = "msn_manual_capture_bundle_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _host_hint(url: str) -> str:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/", 1)[0].lower()
    return host[:80] or "unknown-host"


@dataclass(frozen=True)
class MSNManualCaptureBundle:
    schema_version: str
    source_url: str
    source_url_host_hint: str
    title: str
    article_text: str
    comments: tuple[dict[str, Any], ...]
    article_artifact_file_name: str
    comments_artifact_file_name: str | None
    article_artifact_sha256: str
    comments_artifact_sha256: str | None
    article_text_sha256: str
    comments_text_sha256: str | None
    comment_count: int
    bundle_sha256: str
    data_extraction_implemented: bool = True
    ready_for_total_export_review: bool = True
    review_required: bool = True
    manual_operator_artifacts_supplied: bool = True
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    credential_value_read: bool = False
    raw_html_payload_included: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_msn_manual_capture_bundle(
    *,
    article: MSNManualArticleExtraction,
    comments: MSNManualCommentsExtraction | None = None,
) -> MSNManualCaptureBundle:
    if comments is not None and comments.source_url != article.source_url:
        raise ValueError("article and comments source_url values must match")
    comment_dicts = tuple(comment.to_dict() for comment in comments.comments) if comments else ()
    base_payload = {
        "source_url": article.source_url,
        "title": article.title,
        "article_text": article.article_text,
        "comments": comment_dicts,
        "article_artifact_sha256": article.artifact_sha256,
        "comments_artifact_sha256": comments.artifact_sha256 if comments else None,
    }
    return MSNManualCaptureBundle(
        schema_version=MSN_MANUAL_CAPTURE_BUNDLE_SCHEMA_VERSION,
        source_url=article.source_url,
        source_url_host_hint=_host_hint(article.source_url),
        title=article.title,
        article_text=article.article_text,
        comments=comment_dicts,
        article_artifact_file_name=article.artifact_file_name,
        comments_artifact_file_name=comments.artifact_file_name if comments else None,
        article_artifact_sha256=article.artifact_sha256,
        comments_artifact_sha256=comments.artifact_sha256 if comments else None,
        article_text_sha256=article.article_text_sha256,
        comments_text_sha256=comments.comments_text_sha256 if comments else None,
        comment_count=comments.comment_count if comments else 0,
        bundle_sha256=_sha256_json(base_payload),
    )


def msn_manual_capture_bundle_to_json(bundle: MSNManualCaptureBundle) -> str:
    return _json_bytes(bundle.to_dict()).decode("utf-8")
