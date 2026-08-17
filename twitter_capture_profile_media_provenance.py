from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from twitter_browser_capture_strategy import canonicalize_browser_capture_url


TWITTER_PROFILE_MEDIA_PROVENANCE_SCHEMA_VERSION = "twitter_profile_media_provenance.v77a"


@dataclass(frozen=True)
class TwitterProfileMediaProvenanceRecord:
    schema_version: str
    source_url: str
    canonical_url: str
    platform: str
    account_handle: str
    display_name: str
    post_id: str
    status_id: str
    post_text: str
    created_at: str
    captured_at: str
    archive_url: str
    screenshot_references: tuple[Mapping[str, Any], ...]
    media_references: tuple[Mapping[str, Any], ...]
    rendered_dom_status: str
    cursor_state: Mapping[str, Any]
    rate_limit_or_cooldown_state: Mapping[str, Any]
    uploader_account: str
    speaker: str
    clip_holder: str
    original_programme_channel_source: str
    transcripted_statement: str
    claim_subject_affiliation_review: Mapping[str, Any]
    social_media_video_provenance_review: Mapping[str, Any]
    source_role_candidate: str
    final_source_role_decision: bool
    warnings: tuple[str, ...]
    no_write_actions: bool = True
    official_x_api_used: bool = False
    credential_automation_performed: bool = False
    captcha_bypass_performed: bool = False
    proxy_or_evasion_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_status_id_from_url(source_url: str) -> str:
    match = re.search(r"/status/(\d+)", str(source_url or ""))
    return match.group(1) if match else ""


def extract_account_handle_from_url(source_url: str) -> str:
    parsed = urlsplit(str(source_url or ""))
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() not in {"i", "intent", "share"}:
        return parts[0]
    return ""


def build_twitter_profile_media_provenance(
    *,
    source_url: str,
    account_handle: str = "",
    display_name: str = "",
    post_id: str = "",
    post_text: str = "",
    created_at: str = "",
    archive_url: str = "",
    screenshot_references: Sequence[Mapping[str, Any]] = (),
    media_references: Sequence[Mapping[str, Any]] = (),
    rendered_dom_status: str = "rendered_dom_fallback_planned_or_available",
    cursor_state: Mapping[str, Any] | None = None,
    rate_limit_or_cooldown_state: Mapping[str, Any] | None = None,
    speaker: str = "",
    clip_holder: str = "",
    original_programme_channel_source: str = "",
    transcripted_statement: str = "",
    captured_at: str | None = None,
) -> TwitterProfileMediaProvenanceRecord:
    canonical = canonicalize_browser_capture_url(source_url)
    handle = account_handle or extract_account_handle_from_url(canonical)
    status_id = post_id or extract_status_id_from_url(canonical)
    warnings: list[str] = []
    if not handle:
        warnings.append("account_handle_not_captured")
    if "/status/" in canonical and not status_id:
        warnings.append("status_id_not_captured")
    if media_references and not any(str(item.get("source_url") or "") for item in media_references):
        warnings.append("media_reference_missing_source_url")
    claim_review = {
        "claim_subject_affiliation_gap": True,
        "visual_material_not_claim_support": True,
        "review_required": True,
        "note": "Screenshots/media preserve platform evidence but do not by themselves prove affiliation to a claim subject.",
    }
    social_review = {
        "uploader_account": handle,
        "speaker": speaker,
        "original_programme_channel_source": original_programme_channel_source,
        "clip_holder": clip_holder,
        "transcripted_statement": transcripted_statement,
        "archive_url": archive_url,
        "source_url": canonical,
        "platform_logo_or_watermark_proves_claim_affiliation": False,
        "review_required": True,
    }
    role = "PRIMARY_ORIGINAL_AUTHORED_SOURCE_FOR_POST_TEXT_ONLY" if handle and status_id and post_text else "REVIEW_REQUIRED_SOURCE_ROLE_CANDIDATE"
    return TwitterProfileMediaProvenanceRecord(
        schema_version=TWITTER_PROFILE_MEDIA_PROVENANCE_SCHEMA_VERSION,
        source_url=str(source_url),
        canonical_url=canonical,
        platform="X/Twitter",
        account_handle=handle,
        display_name=display_name,
        post_id=status_id,
        status_id=status_id,
        post_text=post_text,
        created_at=created_at,
        captured_at=captured_at or utc_now_iso(),
        archive_url=archive_url,
        screenshot_references=tuple(screenshot_references),
        media_references=tuple(media_references),
        rendered_dom_status=rendered_dom_status,
        cursor_state=dict(cursor_state or {}),
        rate_limit_or_cooldown_state=dict(rate_limit_or_cooldown_state or {}),
        uploader_account=handle,
        speaker=speaker,
        clip_holder=clip_holder,
        original_programme_channel_source=original_programme_channel_source,
        transcripted_statement=transcripted_statement,
        claim_subject_affiliation_review=claim_review,
        social_media_video_provenance_review=social_review,
        source_role_candidate=role,
        final_source_role_decision=False,
        warnings=tuple(warnings),
    )


def render_profile_media_provenance_summary(record: TwitterProfileMediaProvenanceRecord) -> str:
    lines = [
        "TWITTER/X PROFILE/MEDIA PROVENANCE V77A",
        f"source_url: {record.source_url}",
        f"canonical_url: {record.canonical_url}",
        f"platform: {record.platform}",
        f"account_handle: {record.account_handle}",
        f"status_id: {record.status_id}",
        f"rendered_dom_status: {record.rendered_dom_status}",
        f"source_role_candidate: {record.source_role_candidate}",
        f"final_source_role_decision: {record.final_source_role_decision}",
        f"no_write_actions: {record.no_write_actions}",
        f"official_x_api_used: {record.official_x_api_used}",
    ]
    if record.warnings:
        lines.append("warnings: " + ", ".join(record.warnings))
    else:
        lines.append("warnings: NONE")
    return "\n".join(lines)


def record_to_json_text(record: TwitterProfileMediaProvenanceRecord) -> str:
    return json.dumps(record.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
