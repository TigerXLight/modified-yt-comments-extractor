from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

R42GG_MARKER = "YTCE_R42GG_UNIVERSAL_SOURCE_MAP_RECONCILIATION"
R42GG_PASS_STATUS = "PASS_R42GG_UNIVERSAL_SOURCE_MAP_RECONCILIATION"
R42GG_BLOCKED_STATUS = "BLOCKED_R42GG_WITH_EXACT_BLOCKER"
R42GG_SCHEMA_VERSION = "universal_source_map.r42gg.v1"

SIDE_EFFECT_BOUNDARY = (
    "no network fetch, no live browser launch, no media download, no extension execution, "
    "no CAPTCHA/security bypass, no credential/cookie/token harvesting, no source-role/counter/no-jump mutation"
)

STATUS_IMPLEMENTED = "implemented"
STATUS_CLOSED_GREEN = "closed_green"
STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN = "public_download_capable_when_rss_ytdlp_browser_or_receipt_works"
STATUS_METADATA_ONLY_UNTIL_CAPTURED = "metadata_only_until_marker_gated_capture"
STATUS_REVIEW_REQUIRED = "review_required"
STATUS_MANUAL_RECEIPT_IMPORT = "manual_receipt_import_supported"
STATUS_HUMAN_CHAIN_REQUIRED = "human_chain_required"
STATUS_RATE_LIMIT_PAUSE_RECOVERY = "dynamic_rate_limit_pause_recovery_supported"
STATUS_SOURCE_EVIDENCE_FOLDER = "source_evidence_folder_format_supported"
STATUS_UNSUPPORTED = "unsupported"
STATUS_PROHIBITED_NO_BYPASS = "prohibited_no_bypass"
STATUS_NOT_YET_IMPLEMENTED = "not_yet_implemented"
STATUS_REFERENCE_ONLY = "reference_only"
STATUS_NOT_APPLICABLE = "not_applicable"

METHOD_DIMENSIONS: tuple[str, ...] = (
    "metadata",
    "article_text",
    "post_thread_timeline_text",
    "comments_replies",
    "live_chat",
    "media_discovery",
    "media_download_materialization",
    "screenshot_rendered_capture",
    "archive_wayback_archive_today",
    "rss_enclosure",
    "api3128_jdownloader",
    "yt_dlp",
    "webview2_visible_browser",
    "local_exporter_import",
    "extension_manual_receipt_import",
    "human_chain_required",
    "rate_limit_pause_recovery",
    "unsupported_prohibited_no_bypass",
)

SOURCE_GROUPS: tuple[str, ...] = (
    "social_comment_platforms",
    "video_media_platforms",
    "live_streaming_live_chat",
    "creator_owned_independent_video_hubs",
    "short_form_mobile_entertainment_apps",
    "text_microblogging_platforms",
    "image_photo_visual_platforms",
    "community_forums_qa_link_aggregators",
    "news_websites_comment_systems",
    "professional_jobs_portfolio_expert_platforms",
    "workplace_chat_collaboration_platforms",
    "podcast_audio_platforms",
    "archive_source_preservation_platforms",
    "generic_web_article_media_pages",
    "local_files_imported_evidence_export_receipts",
)

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_NAMES = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "spm",
    "ref_src",
    "ref_url",
    "feature",
    "s",
    "si",
}

TWITTER_X_DYNAMIC_BENCHMARK: Mapping[str, object] = {
    "url": "https://x.com/examaddaorg",
    "observed_records": "6.7k",
    "observed_bytes": "8.9 MB",
    "pause_recovery_observed_around": "01:07",
    "completed_around": "08:13",
    "interpretation": (
        "Observed gradual discovery and dynamic rate-limit pause/recovery behavior. "
        "This is not a hard-coded threshold, maximum, or completion guarantee."
    ),
    "hard_coded_record_limit": None,
}


@dataclass(frozen=True)
class SourceMapFamily:
    family_id: str
    display_name: str
    source_groups: tuple[str, ...]
    platform_aliases: tuple[str, ...]
    route_hint: str
    method_statuses: Mapping[str, str]
    review_bridge: str = "produces_review_strings_for_existing_review_window"
    source_role_effect: str = "none_registry_only"
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "family_id": self.family_id,
            "method_statuses": dict(self.method_statuses),
            "notes": list(self.notes),
            "platform_aliases": list(self.platform_aliases),
            "review_bridge": self.review_bridge,
            "route_hint": self.route_hint,
            "source_groups": list(self.source_groups),
            "source_role_effect": self.source_role_effect,
        }


@dataclass(frozen=True)
class SanitizedSourceInput:
    raw_input: str
    extracted_url: str
    normalized_url: str
    source_line: str = ""
    family_hint: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CapturePlan:
    sanitized_input: SanitizedSourceInput
    family_id: str
    route_hint: str
    method_statuses: Mapping[str, str]
    planned_dimensions: tuple[str, ...]
    review_strings: tuple[str, ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "method_statuses": dict(self.method_statuses),
            "planned_dimensions": list(self.planned_dimensions),
            "review_strings": list(self.review_strings),
            "route_hint": self.route_hint,
            "sanitized_input": self.sanitized_input.to_dict(),
            "side_effect_boundary": self.side_effect_boundary,
        }


@dataclass(frozen=True)
class EvidenceRecord:
    family_id: str
    source_url: str
    canonical_url: str
    raw_url: str = ""
    normalized_url: str = ""
    display_name: str = ""
    handle: str = ""
    post_id: str = ""
    text_body: str = ""
    created_at_text: str = ""
    views: str = ""
    comments: str = ""
    reposts: str = ""
    likes: str = ""
    bookmarks: str = ""
    capture_time: str = ""
    capture_timezone: str = "UTC"
    media_folder: str = ""
    comments_folder: str = ""
    replies_folder: str = ""
    media_relative_paths: tuple[str, ...] = ()
    source_fingerprint: str = ""
    evidence_status: str = STATUS_METADATA_ONLY_UNTIL_CAPTURED

    def with_review_fingerprint(self) -> "EvidenceRecord":
        if self.source_fingerprint:
            return self
        payload = "|".join(
            [
                self.family_id,
                self.canonical_url,
                self.handle,
                self.post_id,
                _normalize_text_for_review(self.text_body),
                ",".join(self.media_relative_paths),
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:24]
        return _replace_dataclass(self, source_fingerprint=f"sha256:{digest}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self.with_review_fingerprint())
        data["media_relative_paths"] = list(data["media_relative_paths"])
        data["review_strings"] = build_review_strings(self)
        return data


@dataclass(frozen=True)
class R42GGReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    family_count: int
    source_group_count: int
    method_dimension_count: int
    checks: tuple[Mapping[str, str], ...]
    sample_plans: tuple[CapturePlan, ...]
    twitter_x_dynamic_benchmark: Mapping[str, object]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GG_PASS_STATUS and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "family_count": self.family_count,
            "generated_at": self.generated_at,
            "marker": self.marker,
            "method_dimension_count": self.method_dimension_count,
            "passed": self.passed,
            "sample_plans": [plan.to_dict() for plan in self.sample_plans],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_group_count": self.source_group_count,
            "source_root": self.source_root,
            "status": self.status,
            "twitter_x_dynamic_benchmark": dict(self.twitter_x_dynamic_benchmark),
        }


def _replace_dataclass(value: Any, **changes: Any) -> Any:
    data = asdict(value)
    data.update(changes)
    return type(value)(**data)


def _methods(**overrides: str) -> Mapping[str, str]:
    statuses: dict[str, str] = {dimension: STATUS_NOT_YET_IMPLEMENTED for dimension in METHOD_DIMENSIONS}
    statuses.update(overrides)
    return statuses


SOURCE_MAP_FAMILIES: tuple[SourceMapFamily, ...] = (
    SourceMapFamily(
        "youtube",
        "YouTube video/channel/live source",
        ("social_comment_platforms", "video_media_platforms", "live_streaming_live_chat"),
        ("youtube", "youtu.be"),
        "existing_youtube_adapter_and_jdownloader_api3128_when_public_media_is_selected",
        _methods(
            metadata=STATUS_IMPLEMENTED,
            post_thread_timeline_text=STATUS_IMPLEMENTED,
            comments_replies=STATUS_IMPLEMENTED,
            live_chat=STATUS_IMPLEMENTED,
            media_discovery=STATUS_IMPLEMENTED,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            api3128_jdownloader=STATUS_CLOSED_GREEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "twitter_x",
        "X/Twitter status/account/timeline source",
        ("social_comment_platforms", "text_microblogging_platforms"),
        ("x.com", "twitter.com", "twitter", "x"),
        "r42gf_closed_specialist_family_with_r42gg_method_slots",
        _methods(
            metadata=STATUS_IMPLEMENTED,
            post_thread_timeline_text=STATUS_IMPLEMENTED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            screenshot_rendered_capture=STATUS_HUMAN_CHAIN_REQUIRED,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
            extension_manual_receipt_import=STATUS_MANUAL_RECEIPT_IMPORT,
            human_chain_required=STATUS_HUMAN_CHAIN_REQUIRED,
            rate_limit_pause_recovery=STATUS_RATE_LIMIT_PAUSE_RECOVERY,
        ),
        notes=(
            "R42GF remains the specialist closeout; R42GG exposes the universal registry slots.",
            "Dynamic benchmark records gradual discovery and pause/recovery behavior, not fixed thresholds.",
        ),
    ),
    SourceMapFamily(
        "instagram",
        "Instagram post/reel/profile source",
        ("social_comment_platforms", "image_photo_visual_platforms", "short_form_mobile_entertainment_apps"),
        ("instagram", "instagram.com"),
        "manual_receipt_or_visible_browser_material_then_review_bridge",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            extension_manual_receipt_import=STATUS_MANUAL_RECEIPT_IMPORT,
            human_chain_required=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "short_form_video",
        "Short-form/mobile entertainment apps",
        ("social_comment_platforms", "video_media_platforms", "short_form_mobile_entertainment_apps"),
        ("tiktok", "musical.ly", "clapper", "triller", "likee", "snapchat", "lemon8"),
        "user_supplied_public_url_then_visible_browser_or_public_download_tool_if_supported",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            human_chain_required=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "live_streaming",
        "Live streaming and live chat platforms",
        ("video_media_platforms", "live_streaming_live_chat"),
        ("twitch", "kick", "rumble_live", "youtube_live", "facebook_live"),
        "public_vod_livechat_receipt_or_visible_browser_capture_when_available",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            live_chat=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            human_chain_required=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "creator_owned_video_hubs",
        "Creator-owned and independent video hubs",
        ("video_media_platforms", "creator_owned_independent_video_hubs"),
        ("vimeo", "dailymotion", "rumble", "peertube", "odysee", "lbry", "dtube", "nebula", "floatplane", "bitchute"),
        "generic_video_hub_public_url_then_ytdlp_or_visible_browser_if_supported",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            article_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "microblog_fediverse",
        "Text and microblogging platforms",
        ("social_comment_platforms", "text_microblogging_platforms"),
        ("threads", "bluesky", "bsky.app", "mastodon", "fediverse", "truthsocial", "gab", "parler", "tumblr"),
        "public_post_or_export_receipt_then_review_string_bridge",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
            extension_manual_receipt_import=STATUS_MANUAL_RECEIPT_IMPORT,
        ),
    ),
    SourceMapFamily(
        "image_photo_visual",
        "Image/photo/visual platforms",
        ("social_comment_platforms", "image_photo_visual_platforms"),
        ("pinterest", "flickr", "500px", "pixelfed", "vsco", "glass", "behance", "dribbble", "vero", "bereal", "locket"),
        "public_visual_page_or_receipt_import_then_metadata_review",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "community_forums",
        "Community/forums/Q&A/link aggregators",
        ("social_comment_platforms", "community_forums_qa_link_aggregators"),
        ("reddit", "quora", "stackoverflow", "stackexchange", "hackernews", "news.ycombinator.com", "lobsters", "lemmy", "kbin", "discuit", "tildes", "4chan", "forum"),
        "public_thread_text_comments_then_review_bridge",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            archive_wayback_archive_today=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
        ),
    ),
    SourceMapFamily(
        "news_websites",
        "News websites and comment systems",
        ("news_websites_comment_systems", "generic_web_article_media_pages"),
        ("metro.co.uk", "bbc.co.uk", "theguardian.com", "telegraph.co.uk", "msn.com", "disqus", "coral_talk"),
        "r42gd_generic_article_lane_with_comment_systems_as_review_required",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            article_text=STATUS_CLOSED_GREEN,
            comments_replies=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_CLOSED_GREEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            screenshot_rendered_capture=STATUS_CLOSED_GREEN,
            archive_wayback_archive_today=STATUS_CLOSED_GREEN,
            api3128_jdownloader=STATUS_CLOSED_GREEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "professional_platforms",
        "Professional/jobs/portfolio/expert platforms",
        ("professional_jobs_portfolio_expert_platforms", "image_photo_visual_platforms"),
        ("linkedin", "xing", "github", "researchgate", "academia.edu", "wellfound", "hired", "blind", "fishbowl", "alignable", "lunchclub"),
        "profile_or_portfolio_receipt_import_then_review_bridge",
        _methods(
            metadata=STATUS_REVIEW_REQUIRED,
            article_text=STATUS_REVIEW_REQUIRED,
            post_thread_timeline_text=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_REVIEW_REQUIRED,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "workplace_chat",
        "Workplace/chat/collaboration platforms",
        ("workplace_chat_collaboration_platforms", "local_files_imported_evidence_export_receipts"),
        ("slack", "discord", "telegram", "teams", "microsoft_teams", "google_chat", "webex", "mattermost", "rocket.chat", "zulip", "matrix", "element", "wire", "guild", "flock"),
        "local_export_or_manual_receipt_import_only",
        _methods(
            metadata=STATUS_MANUAL_RECEIPT_IMPORT,
            post_thread_timeline_text=STATUS_MANUAL_RECEIPT_IMPORT,
            comments_replies=STATUS_MANUAL_RECEIPT_IMPORT,
            media_discovery=STATUS_MANUAL_RECEIPT_IMPORT,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
            extension_manual_receipt_import=STATUS_MANUAL_RECEIPT_IMPORT,
            unsupported_prohibited_no_bypass=STATUS_PROHIBITED_NO_BYPASS,
        ),
    ),
    SourceMapFamily(
        "podcast_rss",
        "Podcast RSS and public enclosure source",
        ("podcast_audio_platforms",),
        ("rss", "podcast_rss", "enclosure"),
        "r42ge_rss_enclosure_public_audio_when_present",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            article_text=STATUS_REVIEW_REQUIRED,
            media_discovery=STATUS_CLOSED_GREEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            rss_enclosure=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
        ),
    ),
    SourceMapFamily(
        "apple_podcasts",
        "Apple Podcasts public episode source",
        ("podcast_audio_platforms",),
        ("podcasts.apple.com", "apple_podcasts"),
        "r42ge_podcast_route_rss_ytdlp_browser_or_receipt_when_available",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            media_discovery=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            rss_enclosure=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
        ),
        notes=("Not metadata-only by default; public-download-capable when RSS, yt-dlp, browser-backed source evidence, or local receipt works.",),
    ),
    SourceMapFamily(
        "spotify_podcast",
        "Spotify podcast episode source",
        ("podcast_audio_platforms",),
        ("open.spotify.com/episode", "spotify_podcast"),
        "r42ge_podcast_route_public_podcast_source_evidence_when_available",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            media_discovery=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            rss_enclosure=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            local_exporter_import=STATUS_MANUAL_RECEIPT_IMPORT,
        ),
        notes=("Spotify podcasts are not metadata-only by default; Spotify music/DRM is a separate prohibited family.",),
    ),
    SourceMapFamily(
        "spotify_music_drm",
        "Spotify music/DRM source",
        ("podcast_audio_platforms", "video_media_platforms"),
        ("open.spotify.com/track", "open.spotify.com/album", "spotify_music", "spotify_drm"),
        "unsupported_drm_no_bypass",
        _methods(
            metadata=STATUS_METADATA_ONLY_UNTIL_CAPTURED,
            unsupported_prohibited_no_bypass=STATUS_PROHIBITED_NO_BYPASS,
        ),
        notes=("No DRM bypass, credential harvesting, or media materialization.",),
    ),
    SourceMapFamily(
        "bbc_sounds",
        "BBC Sounds / BBC podcast source",
        ("podcast_audio_platforms", "news_websites_comment_systems"),
        ("bbc.co.uk/sounds", "bbc_sounds"),
        "r42ge_bbc_sounds_ytdlp_ffmpeg_copy_when_public",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            media_discovery=STATUS_CLOSED_GREEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "archive_preservation",
        "Archive/source preservation platforms",
        ("archive_source_preservation_platforms",),
        ("web.archive.org", "archive.org", "archive.ph", "archive.today", "archive.is", "perma.cc", "local_warc", "wacz"),
        "archive_target_resolution_and_preservation_metadata_no_locator_promotion",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            article_text=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            media_discovery=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            screenshot_rendered_capture=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            archive_wayback_archive_today=STATUS_CLOSED_GREEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
            human_chain_required=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
        notes=("Archive locators remain preservation metadata unless reviewing the preserved target material.",),
    ),
    SourceMapFamily(
        "generic_web_article_media",
        "Generic web/article/media page",
        ("generic_web_article_media_pages", "news_websites_comment_systems"),
        ("generic_article", "generic_web", "html", "pdf", "direct_image", "direct_video"),
        "r42gd_generic_article_lane_and_r42gb_api3128_jdownloader_for_selected_media",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            article_text=STATUS_CLOSED_GREEN,
            media_discovery=STATUS_CLOSED_GREEN,
            media_download_materialization=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            screenshot_rendered_capture=STATUS_CLOSED_GREEN,
            archive_wayback_archive_today=STATUS_CLOSED_GREEN,
            api3128_jdownloader=STATUS_CLOSED_GREEN,
            yt_dlp=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            webview2_visible_browser=STATUS_HUMAN_CHAIN_REQUIRED,
        ),
    ),
    SourceMapFamily(
        "local_files_imported_evidence",
        "Local files/imported evidence/export receipts",
        ("local_files_imported_evidence_export_receipts",),
        ("local_file", "txt", "json", "ndjson", "csv", "export_receipt", "source_export"),
        "local_import_review_string_bridge",
        _methods(
            metadata=STATUS_CLOSED_GREEN,
            article_text=STATUS_CLOSED_GREEN,
            post_thread_timeline_text=STATUS_CLOSED_GREEN,
            comments_replies=STATUS_CLOSED_GREEN,
            media_discovery=STATUS_CLOSED_GREEN,
            local_exporter_import=STATUS_CLOSED_GREEN,
            extension_manual_receipt_import=STATUS_MANUAL_RECEIPT_IMPORT,
        ),
    ),
)

SOURCE_FAMILY_BY_ID: Mapping[str, SourceMapFamily] = {family.family_id: family for family in SOURCE_MAP_FAMILIES}


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


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _normalize_text_for_review(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _unwrap_markdown_or_angle(value: str) -> str:
    raw = str(value or "").strip()
    markdown = re.search(r"\[[^\]]*]\(([^)]+)\)", raw)
    if markdown:
        raw = markdown.group(1).strip()
    angle = re.search(r"<((?:https?://|x\.com/|twitter\.com/)[^>]+)>", raw, flags=re.I)
    if angle:
        raw = angle.group(1).strip()
    bare = re.search(r"(?:https?://|x\.com/|twitter\.com/)[^\s<>)\]}\"']+", raw, flags=re.I)
    if bare:
        raw = bare.group(0).strip()
    return raw


def sanitize_source_url(value: str) -> str:
    raw = _unwrap_markdown_or_angle(value)
    raw = raw.replace("\\_", "_").replace("\\/", "/").replace("\\\\", "\\")
    raw = raw.strip().strip("`'\"[]{}<>")
    raw = raw.rstrip(".,;:!?)\u201d\u2019\"'")
    if raw and not re.match(r"^[a-z][a-z0-9+.-]*://", raw, flags=re.I):
        if re.match(r"^(?:www\.)?(?:x|twitter)\.com/", raw, flags=re.I):
            raw = "https://" + raw
        elif "." in raw.split("/", 1)[0]:
            raw = "https://" + raw
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return raw
    host = (parsed.hostname or parsed.netloc).lower().removeprefix("www.")
    if host == "twitter.com":
        host = "x.com"
    path = re.sub(r"/+", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    path = quote(path, safe="/:@%+-._~")
    kept_query = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_NAMES or lowered.startswith(TRACKING_QUERY_PREFIXES):
            continue
        kept_query.append((key, val))
    query = urlencode(kept_query, doseq=True)
    return urlunsplit(("https", host, path, query, ""))


def sanitize_source_input(value: str, *, source_line: str = "") -> SanitizedSourceInput:
    extracted = _unwrap_markdown_or_angle(value)
    normalized = sanitize_source_url(extracted)
    return SanitizedSourceInput(
        raw_input=str(value or ""),
        extracted_url=extracted,
        normalized_url=normalized,
        source_line=source_line or str(value or ""),
        family_hint=detect_source_family(normalized),
    )


def sanitize_source_inputs(values: str | Iterable[str]) -> tuple[SanitizedSourceInput, ...]:
    if isinstance(values, str):
        lines = values.splitlines()
    else:
        lines = [str(item) for item in values]
    output: list[SanitizedSourceInput] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.search(r"(?:https?://|x\.com/|twitter\.com/)", stripped, flags=re.I):
            output.append(sanitize_source_input(stripped, source_line=line))
    return tuple(output)


def _host_path(url: str) -> tuple[str, str]:
    parsed = urlsplit(sanitize_source_url(url))
    return (parsed.hostname or parsed.netloc).lower(), parsed.path.lower()


def detect_source_family(url: str) -> str:
    normalized = sanitize_source_url(url)
    host, path = _host_path(normalized)
    host_path = f"{host}{path}"
    if host in {"x.com", "twitter.com"}:
        return "twitter_x"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    if any(name in host for name in ("tiktok.com", "clapperapp.com", "triller.co", "likee.video", "snapchat.com", "lemon8-app.com")):
        return "short_form_video"
    if any(name in host for name in ("twitch.tv", "kick.com")):
        return "live_streaming"
    if any(name in host for name in ("vimeo.com", "dailymotion.com", "rumble.com", "odysee.com", "bitchute.com", "peertube")):
        return "creator_owned_video_hubs"
    if any(name in host for name in ("threads.net", "bsky.app", "mastodon", "tumblr.com", "gab.com", "truthsocial.com")):
        return "microblog_fediverse"
    if any(name in host for name in ("pinterest.", "flickr.com", "500px.com", "pixelfed", "vsco.co", "behance.net", "dribbble.com")):
        return "image_photo_visual"
    if any(name in host for name in ("reddit.com", "quora.com", "stackoverflow.com", "stackexchange.com", "news.ycombinator.com", "lobste.rs", "lemmy", "kbin")):
        return "community_forums"
    if any(name in host for name in ("linkedin.com", "github.com", "researchgate.net", "academia.edu", "xing.com", "wellfound.com")):
        return "professional_platforms"
    if any(name in host for name in ("slack.com", "discord.com", "telegram.org", "teams.microsoft.com", "chat.google.com", "mattermost", "zulip")):
        return "workplace_chat"
    if "podcasts.apple.com" in host:
        return "apple_podcasts"
    if "open.spotify.com" in host and "/episode" in path:
        return "spotify_podcast"
    if "open.spotify.com" in host and ("/track" in path or "/album" in path):
        return "spotify_music_drm"
    if "bbc.co.uk" in host and "/sounds" in path:
        return "bbc_sounds"
    if host in {"web.archive.org", "archive.org", "archive.ph", "archive.today", "archive.is", "perma.cc"}:
        return "archive_preservation"
    if any(name in host for name in ("metro.co.uk", "bbc.co.uk", "theguardian.com", "telegraph.co.uk", "msn.com")):
        return "news_websites"
    if re.search(r"\.(?:mp4|mov|webm|m4a|mp3|wav|jpg|jpeg|png|gif|webp|pdf)$", path):
        return "generic_web_article_media"
    return "generic_web_article_media"


def family_for_url(url: str) -> SourceMapFamily:
    family_id = detect_source_family(url)
    return SOURCE_FAMILY_BY_ID.get(family_id, SOURCE_FAMILY_BY_ID["generic_web_article_media"])


def build_capture_plan(value: str) -> CapturePlan:
    sanitized = sanitize_source_input(value)
    family = family_for_url(sanitized.normalized_url)
    planned_dimensions = tuple(
        dimension
        for dimension, status in family.method_statuses.items()
        if status not in {STATUS_NOT_YET_IMPLEMENTED, STATUS_NOT_APPLICABLE, STATUS_UNSUPPORTED, STATUS_PROHIBITED_NO_BYPASS}
    )
    return CapturePlan(
        sanitized_input=sanitized,
        family_id=family.family_id,
        route_hint=family.route_hint,
        method_statuses=family.method_statuses,
        planned_dimensions=planned_dimensions,
        review_strings=tuple(_dedupe([sanitized.normalized_url, sanitized.extracted_url, family.family_id])),
    )


def build_timeline_export_layout(family: str, account_or_site: str, capture_timestamp: str) -> Mapping[str, Any]:
    safe_family = re.sub(r"[^a-zA-Z0-9_.-]+", "_", family).strip("_") or "source"
    safe_account = re.sub(r"[^a-zA-Z0-9_.-]+", "_", account_or_site).strip("_") or "account"
    safe_stamp = re.sub(r"[^0-9TtZz_.-]+", "_", capture_timestamp).strip("_") or "capture"
    root = f"source_exports/{safe_family}/{safe_account}/capture_{safe_stamp}"
    return {
        "root": root,
        "manifest": f"{root}/manifest.json",
        "timeline_markdown": f"{root}/timeline.md",
        "timeline_ndjson": f"{root}/timeline.ndjson",
        "progress_events": f"{root}/progress_events.ndjson",
        "media_index": f"{root}/media_index.json",
        "review_strings": f"{root}/review_strings.txt",
        "post_template": {
            "post_markdown": f"{root}/posts/<post_id>/post.md",
            "post_json": f"{root}/posts/<post_id>/post.json",
            "media_dir": f"{root}/posts/<post_id>/media/",
            "comments_dir": f"{root}/posts/<post_id>/comments/",
            "replies_dir": f"{root}/posts/<post_id>/replies/",
        },
    }


def build_review_strings(record: EvidenceRecord) -> tuple[str, ...]:
    record = record.with_review_fingerprint()
    stats = " ".join(
        item
        for item in (
            f"views {record.views}" if record.views else "",
            f"comments {record.comments}" if record.comments else "",
            f"reposts {record.reposts}" if record.reposts else "",
            f"likes {record.likes}" if record.likes else "",
            f"bookmarks {record.bookmarks}" if record.bookmarks else "",
        )
        if item
    )
    snippet = _normalize_text_for_review(record.text_body)
    if len(snippet) > 240:
        snippet = snippet[:237].rstrip() + "..."
    values = [
        record.canonical_url,
        record.raw_url,
        record.normalized_url,
        record.source_url,
        record.handle,
        record.display_name,
        record.post_id,
        record.created_at_text,
        snippet,
        stats,
        *record.media_relative_paths,
        record.source_fingerprint,
    ]
    return tuple(_dedupe(value for value in values if value))


def render_single_post_card(record: EvidenceRecord) -> str:
    record = record.with_review_fingerprint()
    lines = [
        f"# {record.display_name or record.handle or record.post_id or 'Source post'}",
        "",
        f"- Handle: {record.handle or 'unknown'}",
        f"- Timestamp: {record.created_at_text or 'unknown'}",
        f"- Captured: {record.capture_time or 'unknown'} {record.capture_timezone}",
        f"- Source URL: {record.canonical_url}",
        f"- Views: {record.views or 'unknown'}",
        f"- Comments: {record.comments or 'unknown'}",
        f"- Reposts: {record.reposts or 'unknown'}",
        f"- Likes: {record.likes or 'unknown'}",
        f"- Bookmarks: {record.bookmarks or 'unknown'}",
        f"- Media folder: {record.media_folder or 'none'}",
        f"- Comments folder: {record.comments_folder or 'none'}",
        f"- Replies folder: {record.replies_folder or 'none'}",
        f"- Source fingerprint: {record.source_fingerprint}",
        "",
        record.text_body or "",
        "",
        "## Review strings",
    ]
    lines.extend(f"- {item}" for item in build_review_strings(record))
    return "\n".join(lines).rstrip() + "\n"


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def source_map_as_dict() -> Mapping[str, Any]:
    return {
        "families": [family.to_dict() for family in SOURCE_MAP_FAMILIES],
        "marker": R42GG_MARKER,
        "method_dimensions": list(METHOD_DIMENSIONS),
        "source_groups": list(SOURCE_GROUPS),
        "twitter_x_dynamic_benchmark": dict(TWITTER_X_DYNAMIC_BENCHMARK),
    }


def validate_universal_source_map(source_root: str | Path = ".") -> R42GGReport:
    family_ids = {family.family_id for family in SOURCE_MAP_FAMILIES}
    covered_groups = {group for family in SOURCE_MAP_FAMILIES for group in family.source_groups}
    method_complete = all(set(family.method_statuses) == set(METHOD_DIMENSIONS) for family in SOURCE_MAP_FAMILIES)
    aliases = {alias for family in SOURCE_MAP_FAMILIES for alias in family.platform_aliases}
    required_aliases = {
        "youtube",
        "x.com",
        "twitter.com",
        "instagram",
        "tiktok",
        "twitch",
        "vimeo",
        "reddit",
        "quora",
        "linkedin",
        "slack",
        "podcasts.apple.com",
        "open.spotify.com/episode",
        "open.spotify.com/track",
        "web.archive.org",
        "archive.ph",
        "generic_article",
        "source_export",
    }
    twitter = SOURCE_FAMILY_BY_ID["twitter_x"]
    apple = SOURCE_FAMILY_BY_ID["apple_podcasts"]
    spotify_podcast = SOURCE_FAMILY_BY_ID["spotify_podcast"]
    spotify_music = SOURCE_FAMILY_BY_ID["spotify_music_drm"]
    checks = (
        _check("all_required_source_groups_covered", set(SOURCE_GROUPS).issubset(covered_groups), ",".join(sorted(set(SOURCE_GROUPS) - covered_groups))),
        _check("all_method_dimensions_present_for_each_family", method_complete),
        _check("required_platform_aliases_present", required_aliases.issubset(aliases), ",".join(sorted(required_aliases - aliases))),
        _check("generic_article_lane_present", "generic_web_article_media" in family_ids and "news_websites" in family_ids),
        _check("podcasts_not_metadata_only_by_default", apple.method_statuses["media_download_materialization"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN and spotify_podcast.method_statuses["media_download_materialization"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN),
        _check("spotify_music_drm_prohibited", spotify_music.method_statuses["unsupported_prohibited_no_bypass"] == STATUS_PROHIBITED_NO_BYPASS),
        _check("twitter_x_dynamic_slots_exposed", all(twitter.method_statuses[item] in {STATUS_RATE_LIMIT_PAUSE_RECOVERY, STATUS_MANUAL_RECEIPT_IMPORT, STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN, STATUS_HUMAN_CHAIN_REQUIRED, STATUS_IMPLEMENTED} for item in ("rate_limit_pause_recovery", "local_exporter_import", "extension_manual_receipt_import", "media_discovery", "webview2_visible_browser"))),
        _check("twitter_x_benchmark_not_a_hard_limit", TWITTER_X_DYNAMIC_BENCHMARK.get("hard_coded_record_limit") is None),
        _check("side_effect_boundary_declared", "no network fetch" in SIDE_EFFECT_BOUNDARY and "no source-role" in SIDE_EFFECT_BOUNDARY),
    )
    status = R42GG_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GG_BLOCKED_STATUS
    samples = (
        build_capture_plan("https://x.com/examaddaorg?utm_source=test"),
        build_capture_plan("[Metro](https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/?utm_campaign=x)"),
        build_capture_plan("https://podcasts.apple.com/gb/podcast/example/id123456789"),
        build_capture_plan("https://open.spotify.com/track/123"),
    )
    return R42GGReport(
        marker=R42GG_MARKER,
        schema_version=R42GG_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(Path(source_root)),
        status=status,
        family_count=len(SOURCE_MAP_FAMILIES),
        source_group_count=len(SOURCE_GROUPS),
        method_dimension_count=len(METHOD_DIMENSIONS),
        checks=checks,
        sample_plans=samples,
        twitter_x_dynamic_benchmark=TWITTER_X_DYNAMIC_BENCHMARK,
    )


def _write_report(output_root: Path, report: R42GGReport) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "R42GG_UNIVERSAL_SOURCE_MAP_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    map_json = json.dumps(source_map_as_dict(), indent=2, sort_keys=True)
    (output_root / "R42GG_UNIVERSAL_SOURCE_MAP.json").write_text(map_json, encoding="utf-8")
    lines = [
        f"# {R42GG_MARKER}",
        "",
        f"Status: {report.status}",
        f"Generated: {report.generated_at}",
        f"Families: {report.family_count}",
        f"Method dimensions: {report.method_dimension_count}",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['status'].upper()} {check['name']}: {check.get('detail', '')}" for check in report.checks)
    lines.extend(
        [
            "",
            "## Side Effect Boundary",
            SIDE_EFFECT_BOUNDARY,
            "",
            "## Dynamic X Benchmark",
            json.dumps(dict(TWITTER_X_DYNAMIC_BENCHMARK), indent=2, sort_keys=True),
        ]
    )
    (output_root / "R42GG_UNIVERSAL_SOURCE_MAP_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GG_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gg_universal_source_map")
    args = parser.parse_args(argv)
    report = validate_universal_source_map(args.source_root)
    _write_report(Path(args.output_root), report)
    print(R42GG_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "CapturePlan",
    "EvidenceRecord",
    "METHOD_DIMENSIONS",
    "R42GG_BLOCKED_STATUS",
    "R42GG_MARKER",
    "R42GG_PASS_STATUS",
    "R42GGReport",
    "SanitizedSourceInput",
    "SOURCE_GROUPS",
    "SOURCE_MAP_FAMILIES",
    "SOURCE_FAMILY_BY_ID",
    "SourceMapFamily",
    "TWITTER_X_DYNAMIC_BENCHMARK",
    "build_capture_plan",
    "build_review_strings",
    "build_timeline_export_layout",
    "detect_source_family",
    "family_for_url",
    "render_single_post_card",
    "sanitize_source_input",
    "sanitize_source_inputs",
    "sanitize_source_url",
    "source_map_as_dict",
    "validate_universal_source_map",
]


if __name__ == "__main__":
    raise SystemExit(main())
