from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_source_map_raw_url_audio_catchup_r42gh import (
    GLOBAL_PLAYER_LBC_FIXTURE_URL,
    GLOBAL_PLAYER_METHOD_METADATA,
    R42GH_PASS_STATUS,
    build_lbc_global_player_evidence_record,
    validate_source_map_raw_url_audio_catchup,
)
from profile_media_universal_source_map_r42gg import (
    SIDE_EFFECT_BOUNDARY,
    STATUS_CLOSED_GREEN,
    STATUS_HUMAN_CHAIN_REQUIRED,
    STATUS_MANUAL_RECEIPT_IMPORT,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_NOT_YET_IMPLEMENTED,
    STATUS_PROHIBITED_NO_BYPASS,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
    STATUS_REVIEW_REQUIRED,
    build_capture_plan,
    sanitize_source_url,
)

R42GI_MARKER = "YTCE_R42GI_UNIVERSAL_MEDIA_DISCOVERY_METHOD_MATRIX"
R42GI_PASS_STATUS = "PASS_R42GI_UNIVERSAL_MEDIA_DISCOVERY_METHOD_MATRIX"
R42GI_BLOCKED_STATUS = "BLOCKED_R42GI_WITH_EXACT_BLOCKER"
R42GI_SCHEMA_VERSION = "universal_media_method_matrix.r42gi.v1"

STATUS_IMPLEMENTED = "implemented"
STATUS_BLOCKED_ACCESS_CONTROL = "blocked_access_control"
STATUS_BLOCKED_PRIVATE_OR_PROTECTED = "blocked_private_or_protected"
STATUS_BLOCKED_DRM = "blocked_drm"
STATUS_BLOCKED_LOGIN_REQUIRED = "blocked_login_required"
STATUS_SKIPPED_LOW_PRIORITY = "skipped_low_priority"
STATUS_SKIPPED_DUPLICATE = "skipped_duplicate"
STATUS_FAILED_WITH_EXACT_ERROR = "failed_with_exact_error"

MEDIA_KINDS: tuple[str, ...] = (
    "image",
    "video",
    "audio",
    "animated_gif",
    "thumbnail",
    "poster",
    "avatar",
    "banner",
    "article_image",
    "post_media",
    "quoted_post_media",
    "link_preview_media",
    "embedded_player_media",
    "rss_enclosure",
    "podcast_audio",
    "broadcast_catchup_audio",
    "subtitle_or_caption",
    "transcript",
    "screenshot",
    "page_snapshot",
    "sidecar_metadata",
    "unknown_binary",
)

DISCOVERY_METHODS: tuple[str, ...] = (
    "dom_img_src",
    "dom_img_srcset",
    "dom_picture_source",
    "dom_video_source",
    "dom_audio_source",
    "dom_video_poster",
    "dom_anchor_download",
    "dom_anchor_direct_media",
    "opengraph_image",
    "opengraph_video",
    "opengraph_audio",
    "twitter_card_image",
    "twitter_card_player",
    "json_ld_media",
    "rss_enclosure",
    "browser_network_observed_media",
    "browser_download_event",
    "webview2_visible_browser_observed",
    "api3128_jdownloader",
    "yt_dlp_python_module",
    "extension_manual_receipt_import",
    "local_exporter_import",
    "local_file_import",
    "manual_user_selected_media",
    "archive_replay_media",
    "screenshot_capture",
)

MEDIA_ROLES: tuple[str, ...] = (
    "primary_post_media",
    "article_body_media",
    "article_header_media",
    "link_preview_media",
    "quoted_post_media",
    "comment_media",
    "reply_media",
    "avatar",
    "banner",
    "thumbnail",
    "poster_frame",
    "embedded_player",
    "podcast_episode_audio",
    "broadcast_episode_audio",
    "source_screenshot",
    "archive_snapshot",
    "metadata_sidecar",
    "transcript_or_caption",
    "manual_receipt_file",
    "unknown",
)

CAPTURE_STATUSES: tuple[str, ...] = (
    STATUS_CLOSED_GREEN,
    STATUS_IMPLEMENTED,
    STATUS_NOT_YET_IMPLEMENTED,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
    STATUS_MANUAL_RECEIPT_IMPORT,
    STATUS_HUMAN_CHAIN_REQUIRED,
    STATUS_REVIEW_REQUIRED,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_BLOCKED_ACCESS_CONTROL,
    STATUS_BLOCKED_PRIVATE_OR_PROTECTED,
    STATUS_BLOCKED_DRM,
    STATUS_BLOCKED_LOGIN_REQUIRED,
    STATUS_PROHIBITED_NO_BYPASS,
    STATUS_SKIPPED_LOW_PRIORITY,
    STATUS_SKIPPED_DUPLICATE,
    STATUS_FAILED_WITH_EXACT_ERROR,
)

BLOCKED_OR_METADATA_STATUSES = {
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_REVIEW_REQUIRED,
    STATUS_BLOCKED_ACCESS_CONTROL,
    STATUS_BLOCKED_PRIVATE_OR_PROTECTED,
    STATUS_BLOCKED_DRM,
    STATUS_BLOCKED_LOGIN_REQUIRED,
    STATUS_PROHIBITED_NO_BYPASS,
}

MEDIA_CANDIDATE_SCHEMA_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "parent_record_id",
    "source_family",
    "source_url",
    "canonical_source_url",
    "record_type",
    "media_kind",
    "media_role",
    "discovered_from",
    "raw_media_url",
    "canonical_media_url",
    "relative_output_path",
    "suggested_filename",
    "extension_hint",
    "mime_hint",
    "content_type_hint",
    "width",
    "height",
    "duration_seconds",
    "byte_size_hint",
    "quality_label",
    "thumbnail_url",
    "poster_url",
    "download_priority",
    "is_default_selected",
    "requires_human_chain",
    "requires_manual_receipt",
    "requires_login",
    "access_status",
    "method_status",
    "preferred_method",
    "fallback_methods",
    "dedupe_key",
    "sha256_if_materialized",
    "capture_method_id",
    "sidecar_paths",
    "review_strings",
    "notes",
)

MATERIALIZATION_PLAN_SCHEMA_FIELDS: tuple[str, ...] = (
    "plan_id",
    "candidate_id",
    "parent_record_id",
    "source_family",
    "media_kind",
    "media_role",
    "preferred_method",
    "fallback_methods",
    "queue_group",
    "host_group",
    "priority",
    "rate_limit_bucket",
    "resume_key",
    "output_root",
    "relative_output_path",
    "sidecar_paths",
    "expected_artifacts",
    "preserve_native_container",
    "conversion_policy",
    "status",
    "blocked_reason",
    "side_effect_boundary",
)

FAST_QUEUE_POLICY: tuple[str, ...] = (
    "text_record_capture_first",
    "discover_media_candidates_while_loading_scrolling_processing",
    "link_candidate_to_parent_record_immediately",
    "prioritize_high_confidence_primary_media_over_avatars_banners_link_previews_decorative_images",
    "dedupe_by_canonical_media_url_parent_record_role_optional_digest",
    "group_by_host_provider_family",
    "support_pause_recovery_resume_keys",
    "support_human_chain_required_states_without_challenge_bypass",
    "allow_selected_media_only_mode_for_large_pages_accounts",
    "allow_deferred_low_priority_media_materialization",
)

TWITTER_X_DYNAMIC_BENCHMARK: Mapping[str, object] = {
    "url": "https://x.com/examaddaorg",
    "observed_records": "6.7k",
    "observed_bytes": "8.9 MB",
    "pause_recovery_observed_around": "01:07",
    "completed_around": "08:13",
    "hard_coded_limit": None,
}


@dataclass(frozen=True)
class MediaMethodSlot:
    source_family: str
    media_kinds: tuple[str, ...]
    media_roles: tuple[str, ...]
    discovery_methods: tuple[str, ...]
    materialization_methods: tuple[str, ...]
    statuses: Mapping[str, str]
    queue_group: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery_methods": list(self.discovery_methods),
            "materialization_methods": list(self.materialization_methods),
            "media_kinds": list(self.media_kinds),
            "media_roles": list(self.media_roles),
            "notes": list(self.notes),
            "queue_group": self.queue_group,
            "source_family": self.source_family,
            "statuses": dict(self.statuses),
        }


@dataclass(frozen=True)
class MediaCandidate:
    candidate_id: str
    parent_record_id: str
    source_family: str
    source_url: str
    canonical_source_url: str
    record_type: str
    media_kind: str
    media_role: str
    discovered_from: str
    raw_media_url: str = ""
    canonical_media_url: str = ""
    relative_output_path: str = ""
    suggested_filename: str = ""
    extension_hint: str = ""
    mime_hint: str = ""
    content_type_hint: str = ""
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    byte_size_hint: int | None = None
    quality_label: str = ""
    thumbnail_url: str = ""
    poster_url: str = ""
    download_priority: int = 50
    is_default_selected: bool = False
    requires_human_chain: bool = False
    requires_manual_receipt: bool = False
    requires_login: bool = False
    access_status: str = STATUS_METADATA_ONLY_UNTIL_CAPTURED
    method_status: str = STATUS_REVIEW_REQUIRED
    preferred_method: str = ""
    fallback_methods: tuple[str, ...] = ()
    dedupe_key: str = ""
    sha256_if_materialized: str | None = None
    capture_method_id: str = ""
    sidecar_paths: tuple[str, ...] = ()
    review_strings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def with_derived_fields(self) -> "MediaCandidate":
        canonical_source = sanitize_source_url(self.canonical_source_url or self.source_url)
        canonical_media = sanitize_source_url(self.canonical_media_url or self.raw_media_url) if (self.canonical_media_url or self.raw_media_url) else ""
        dedupe_source = "|".join([canonical_source, self.parent_record_id, self.media_role, canonical_media, self.relative_output_path])
        dedupe = self.dedupe_key or f"sha256:{hashlib.sha256(dedupe_source.encode('utf-8', errors='replace')).hexdigest()[:24]}"
        review = self.review_strings or tuple(
            _dedupe(
                [
                    canonical_source,
                    self.source_url,
                    self.parent_record_id,
                    self.candidate_id,
                    canonical_media,
                    self.raw_media_url,
                    self.relative_output_path,
                    self.suggested_filename,
                    self.media_role,
                    self.media_kind,
                    self.thumbnail_url,
                    self.poster_url,
                    *self.sidecar_paths,
                    dedupe,
                ]
            )
        )
        data = asdict(self)
        data.update(
            {
                "canonical_source_url": canonical_source,
                "canonical_media_url": canonical_media,
                "dedupe_key": dedupe,
                "review_strings": review,
            }
        )
        return MediaCandidate(**data)

    def to_dict(self) -> dict[str, Any]:
        item = self.with_derived_fields()
        data = asdict(item)
        for key in ("fallback_methods", "sidecar_paths", "review_strings", "notes"):
            data[key] = list(data[key])
        return data


@dataclass(frozen=True)
class MediaMaterializationPlan:
    plan_id: str
    candidate_id: str
    parent_record_id: str
    source_family: str
    media_kind: str
    media_role: str
    preferred_method: str
    fallback_methods: tuple[str, ...]
    queue_group: str
    host_group: str
    priority: int
    rate_limit_bucket: str
    resume_key: str
    output_root: str
    relative_output_path: str
    sidecar_paths: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    preserve_native_container: bool
    conversion_policy: str
    status: str
    blocked_reason: str = ""
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("fallback_methods", "sidecar_paths", "expected_artifacts"):
            data[key] = list(data[key])
        return data


@dataclass(frozen=True)
class R42GIReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    checks: tuple[Mapping[str, str], ...]
    media_kind_count: int
    discovery_method_count: int
    media_role_count: int
    method_slots: tuple[Mapping[str, Any], ...]
    sample_candidates: tuple[Mapping[str, Any], ...]
    sample_plans: tuple[Mapping[str, Any], ...]
    fast_queue_policy: tuple[str, ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GI_PASS_STATUS and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "discovery_method_count": self.discovery_method_count,
            "fast_queue_policy": list(self.fast_queue_policy),
            "generated_at": self.generated_at,
            "marker": self.marker,
            "media_kind_count": self.media_kind_count,
            "media_role_count": self.media_role_count,
            "method_slots": [dict(slot) for slot in self.method_slots],
            "passed": self.passed,
            "sample_candidates": [dict(item) for item in self.sample_candidates],
            "sample_plans": [dict(item) for item in self.sample_plans],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_root": self.source_root,
            "status": self.status,
        }


MEDIA_METHOD_SLOTS: tuple[MediaMethodSlot, ...] = (
    MediaMethodSlot(
        source_family="universal_media_registry_reference",
        media_kinds=MEDIA_KINDS,
        media_roles=MEDIA_ROLES,
        discovery_methods=DISCOVERY_METHODS,
        materialization_methods=(),
        statuses={
            "schema_coverage": STATUS_CLOSED_GREEN,
            "runtime_effect": STATUS_METADATA_ONLY_UNTIL_CAPTURED,
        },
        queue_group="universal_media_schema_reference",
        notes=(
            "Registry coverage slot only; this is not a runtime capture route.",
            "Specific families below declare their implemented/review/blocked method routes.",
        ),
    ),
    MediaMethodSlot(
        source_family="twitter_x",
        media_kinds=("image", "video", "animated_gif", "thumbnail", "post_media", "quoted_post_media"),
        media_roles=("primary_post_media", "quoted_post_media", "link_preview_media", "thumbnail"),
        discovery_methods=("browser_network_observed_media", "webview2_visible_browser_observed", "extension_manual_receipt_import", "local_exporter_import"),
        materialization_methods=("browser_download_event", "extension_manual_receipt_import", "local_exporter_import"),
        statuses={
            "media_discovery": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "media_download_materialization": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "rate_limit_pause_recovery": "dynamic_supported_not_hard_coded",
            "protected_private_login_limited": STATUS_PROHIBITED_NO_BYPASS,
        },
        queue_group="twitter_x_gradual_media",
        notes=("Extension/manual receipt imports are supported as user-supplied outputs only; no extension execution in R42GI.",),
    ),
    MediaMethodSlot(
        source_family="news_websites",
        media_kinds=("image", "video", "audio", "article_image", "embedded_player_media", "thumbnail", "poster", "screenshot"),
        media_roles=("article_body_media", "article_header_media", "embedded_player", "link_preview_media", "source_screenshot"),
        discovery_methods=("dom_img_src", "dom_img_srcset", "dom_picture_source", "dom_video_source", "dom_audio_source", "opengraph_image", "opengraph_video", "twitter_card_image", "json_ld_media", "api3128_jdownloader", "webview2_visible_browser_observed", "screenshot_capture"),
        materialization_methods=("api3128_jdownloader", "browser_download_event", "manual_user_selected_media", "screenshot_capture"),
        statuses={
            "article_body_images": STATUS_CLOSED_GREEN,
            "embedded_media": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "comments_replies": STATUS_REVIEW_REQUIRED,
            "api3128_jdownloader": STATUS_CLOSED_GREEN,
        },
        queue_group="generic_article_selected_media",
    ),
    MediaMethodSlot(
        source_family="public_broadcast_catchup_audio",
        media_kinds=("audio", "broadcast_catchup_audio", "thumbnail", "sidecar_metadata"),
        media_roles=("broadcast_episode_audio", "metadata_sidecar", "thumbnail"),
        discovery_methods=("yt_dlp_python_module", "opengraph_image", "twitter_card_image", "browser_network_observed_media", "manual_user_selected_media"),
        materialization_methods=("yt_dlp_python_module", "manual_user_selected_media", "local_file_import"),
        statuses={
            "media_discovery": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "media_download_materialization": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "yt_dlp": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
            "drm_private_login_blocked_audio": STATUS_PROHIBITED_NO_BYPASS,
        },
        queue_group="public_audio_native_preservation",
        notes=("Global Player/LBC fixture preserves native M4A and sidecars; no yt-dlp execution in R42GI.",),
    ),
    MediaMethodSlot(
        source_family="podcast_audio",
        media_kinds=("audio", "podcast_audio", "rss_enclosure", "thumbnail", "sidecar_metadata"),
        media_roles=("podcast_episode_audio", "metadata_sidecar", "thumbnail"),
        discovery_methods=("rss_enclosure", "yt_dlp_python_module", "opengraph_audio", "opengraph_image", "manual_user_selected_media"),
        materialization_methods=("rss_enclosure", "yt_dlp_python_module", "local_file_import"),
        statuses={
            "rss_enclosure": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            "yt_dlp": STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            "manual_receipt": STATUS_MANUAL_RECEIPT_IMPORT,
            "drm": STATUS_PROHIBITED_NO_BYPASS,
        },
        queue_group="podcast_audio_preservation",
    ),
    MediaMethodSlot(
        source_family="video_platforms",
        media_kinds=("video", "audio", "thumbnail", "poster", "subtitle_or_caption", "transcript"),
        media_roles=("primary_post_media", "thumbnail", "poster_frame", "transcript_or_caption"),
        discovery_methods=("yt_dlp_python_module", "api3128_jdownloader", "browser_network_observed_media", "webview2_visible_browser_observed", "extension_manual_receipt_import"),
        materialization_methods=("yt_dlp_python_module", "api3128_jdownloader", "manual_user_selected_media"),
        statuses={
            "youtube": STATUS_CLOSED_GREEN,
            "vimeo_tiktok_dailymotion_rumble_peertube_odysee_dtube_bilibili_youku": STATUS_NOT_YET_IMPLEMENTED,
            "twitch_kick_youtube_live": STATUS_HUMAN_CHAIN_REQUIRED,
        },
        queue_group="video_platform_selected_media",
    ),
    MediaMethodSlot(
        source_family="visual_photo_platforms",
        media_kinds=("image", "video", "thumbnail", "avatar", "banner", "post_media"),
        media_roles=("primary_post_media", "avatar", "banner", "thumbnail", "link_preview_media"),
        discovery_methods=("dom_img_src", "opengraph_image", "twitter_card_image", "browser_network_observed_media", "extension_manual_receipt_import"),
        materialization_methods=("manual_user_selected_media", "extension_manual_receipt_import", "browser_download_event"),
        statuses={
            "instagram_pinterest_flickr_pixelfed_vsco_bereal_lemon8_locket_vero_glass": STATUS_REVIEW_REQUIRED,
            "private_or_login_limited": STATUS_PROHIBITED_NO_BYPASS,
        },
        queue_group="visual_platform_review_media",
    ),
    MediaMethodSlot(
        source_family="community_forums",
        media_kinds=("image", "video", "animated_gif", "link_preview_media", "avatar", "thumbnail"),
        media_roles=("primary_post_media", "comment_media", "reply_media", "link_preview_media", "avatar"),
        discovery_methods=("dom_img_src", "dom_anchor_direct_media", "opengraph_image", "json_ld_media", "browser_network_observed_media", "archive_replay_media"),
        materialization_methods=("manual_user_selected_media", "browser_download_event", "local_exporter_import"),
        statuses={
            "reddit_lemmy_hackernews_lobsters_4chan_quora_tumblr_forums": STATUS_REVIEW_REQUIRED,
            "comment_systems": STATUS_REVIEW_REQUIRED,
        },
        queue_group="community_thread_media",
    ),
    MediaMethodSlot(
        source_family="professional_workplace",
        media_kinds=("image", "video", "avatar", "banner", "manual_receipt_file", "unknown_binary"),
        media_roles=("avatar", "banner", "manual_receipt_file", "metadata_sidecar", "unknown"),
        discovery_methods=("local_exporter_import", "extension_manual_receipt_import", "local_file_import", "manual_user_selected_media"),
        materialization_methods=("local_exporter_import", "local_file_import", "manual_user_selected_media"),
        statuses={
            "linkedin_github_researchgate_behance_dribbble": STATUS_REVIEW_REQUIRED,
            "teams_googlechat_matrix_mattermost_zulip": STATUS_MANUAL_RECEIPT_IMPORT,
            "credentials_sessions_private_material": STATUS_PROHIBITED_NO_BYPASS,
        },
        queue_group="professional_workplace_receipts",
    ),
)


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def is_plain_machine_field(value: str) -> bool:
    text = str(value or "").strip()
    return not text.startswith("[") and "](" not in text


def build_global_player_media_candidate() -> MediaCandidate:
    evidence = build_lbc_global_player_evidence_record()
    canonical = sanitize_source_url(evidence.canonical_url)
    candidate = MediaCandidate(
        candidate_id=f"media:public_broadcast_catchup_audio:{evidence.episode_id}:original_m4a",
        parent_record_id=f"episode:{evidence.episode_id}",
        source_family="public_broadcast_catchup_audio",
        source_url=evidence.raw_url,
        canonical_source_url=canonical,
        record_type="episode",
        media_kind="broadcast_catchup_audio",
        media_role="broadcast_episode_audio",
        discovered_from="yt_dlp_python_module",
        raw_media_url=canonical,
        canonical_media_url=canonical,
        relative_output_path=evidence.media_relative_path,
        suggested_filename="original.m4a",
        extension_hint="m4a",
        mime_hint="audio/mp4",
        content_type_hint="audio/mp4",
        duration_seconds=None,
        quality_label="native format 0",
        download_priority=10,
        is_default_selected=True,
        access_status=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
        method_status=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
        preferred_method="yt_dlp_python_module",
        fallback_methods=("manual_user_selected_media", "local_file_import"),
        capture_method_id="global_player_lbc_r42gh_native_m4a",
        sidecar_paths=evidence.sidecar_paths,
        notes=("Preserve native M4A as original media; no conversion for preservation.",),
    )
    return candidate.with_derived_fields()


def build_global_player_materialization_plan(output_root: str = "source_exports/public_broadcast_catchup_audio/lbc/capture_20260912T000000Z") -> MediaMaterializationPlan:
    candidate = build_global_player_media_candidate()
    return MediaMaterializationPlan(
        plan_id=f"plan:{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        parent_record_id=candidate.parent_record_id,
        source_family=candidate.source_family,
        media_kind=candidate.media_kind,
        media_role=candidate.media_role,
        preferred_method="yt_dlp_python_module",
        fallback_methods=("manual_user_selected_media", "local_file_import"),
        queue_group="public_audio_native_preservation",
        host_group="globalplayer.com",
        priority=10,
        rate_limit_bucket="globalplayer_public_audio",
        resume_key=f"{candidate.source_family}:{candidate.parent_record_id}:format0",
        output_root=output_root,
        relative_output_path="media/original.m4a",
        sidecar_paths=("sidecars/info.json", "sidecars/description.txt", "sidecars/thumbnail.*"),
        expected_artifacts=("media/original.m4a", "sidecars/info.json", "sidecars/description.txt", "sidecars/thumbnail.*"),
        preserve_native_container=True,
        conversion_policy="preserve_native_no_transcode_for_preservation",
        status=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
    )


def build_twitter_sample_media_candidate() -> MediaCandidate:
    source_url = sanitize_source_url("https://x.com/examaddaorg")
    candidate = MediaCandidate(
        candidate_id="media:twitter_x:examaddaorg:dynamic_placeholder",
        parent_record_id="account:examaddaorg",
        source_family="twitter_x",
        source_url=source_url,
        canonical_source_url=source_url,
        record_type="timeline_media_candidate",
        media_kind="post_media",
        media_role="primary_post_media",
        discovered_from="browser_network_observed_media",
        download_priority=20,
        access_status=STATUS_REVIEW_REQUIRED,
        method_status=STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
        preferred_method="browser_network_observed_media",
        fallback_methods=("extension_manual_receipt_import", "local_exporter_import"),
        requires_human_chain=True,
        notes=("Dynamic discovery/pause recovery required; benchmark is not a hard-coded limit.",),
    )
    return candidate.with_derived_fields()


def build_generic_article_sample_media_candidate() -> MediaCandidate:
    source_url = sanitize_source_url("https://metro.co.uk/example/")
    candidate = MediaCandidate(
        candidate_id="media:news_websites:metro_example:article_image_1",
        parent_record_id="article:metro_example",
        source_family="news_websites",
        source_url=source_url,
        canonical_source_url=source_url,
        record_type="article_media_candidate",
        media_kind="article_image",
        media_role="article_body_media",
        discovered_from="dom_img_src",
        raw_media_url="https://metro.co.uk/example/image.jpg",
        canonical_media_url="https://metro.co.uk/example/image.jpg",
        relative_output_path="media/article/image_1.jpg",
        suggested_filename="image_1.jpg",
        extension_hint="jpg",
        download_priority=30,
        access_status=STATUS_METADATA_ONLY_UNTIL_CAPTURED,
        method_status=STATUS_CLOSED_GREEN,
        preferred_method="api3128_jdownloader",
        fallback_methods=("webview2_visible_browser_observed", "manual_user_selected_media"),
        notes=("Article media candidate remains metadata/review until captured and marker-gated.",),
    )
    return candidate.with_derived_fields()


def build_materialization_plan_for_candidate(candidate: MediaCandidate, *, output_root: str) -> MediaMaterializationPlan:
    item = candidate.with_derived_fields()
    host = urlsplit(item.canonical_media_url or item.canonical_source_url).hostname or item.source_family
    status = item.method_status
    blocked_reason = ""
    if item.access_status in BLOCKED_OR_METADATA_STATUSES:
        status = item.access_status
        blocked_reason = "candidate_not_accepted_evidence_until_source_route_or_marker_gate_completes"
    return MediaMaterializationPlan(
        plan_id=f"plan:{item.candidate_id}",
        candidate_id=item.candidate_id,
        parent_record_id=item.parent_record_id,
        source_family=item.source_family,
        media_kind=item.media_kind,
        media_role=item.media_role,
        preferred_method=item.preferred_method,
        fallback_methods=item.fallback_methods,
        queue_group=f"{item.source_family}:{item.media_role}",
        host_group=host,
        priority=item.download_priority,
        rate_limit_bucket=f"{item.source_family}:{host}",
        resume_key=f"{item.source_family}:{item.parent_record_id}:{item.dedupe_key}",
        output_root=output_root,
        relative_output_path=item.relative_output_path,
        sidecar_paths=item.sidecar_paths,
        expected_artifacts=tuple(path for path in (item.relative_output_path, *item.sidecar_paths) if path),
        preserve_native_container=item.media_kind in {"audio", "video", "broadcast_catchup_audio", "podcast_audio"},
        conversion_policy="preserve_native_no_transcode_for_preservation",
        status=status,
        blocked_reason=blocked_reason,
    )


def build_media_export_layout(family: str, account_or_site: str, capture_timestamp: str) -> Mapping[str, Any]:
    safe_family = re.sub(r"[^a-zA-Z0-9_.-]+", "_", family).strip("_") or "source"
    safe_account = re.sub(r"[^a-zA-Z0-9_.-]+", "_", account_or_site).strip("_") or "account"
    safe_stamp = re.sub(r"[^0-9TtZz_.-]+", "_", capture_timestamp).strip("_") or "capture"
    root = f"source_exports/{safe_family}/{safe_account}/capture_{safe_stamp}"
    return {
        "root": root,
        "manifest": f"{root}/manifest.json",
        "timeline_markdown": f"{root}/timeline.md",
        "timeline_ndjson": f"{root}/timeline.ndjson",
        "media_index": f"{root}/media_index.json",
        "media_candidates": f"{root}/media_candidates.ndjson",
        "media_download_plan": f"{root}/media_download_plan.json",
        "progress_events": f"{root}/progress_events.ndjson",
        "review_strings": f"{root}/review_strings.txt",
        "post_template": {
            "post_markdown": f"{root}/posts/<post_id>/post.md",
            "post_json": f"{root}/posts/<post_id>/post.json",
            "media_dir": f"{root}/posts/<post_id>/media/",
            "comments_dir": f"{root}/posts/<post_id>/comments/",
            "replies_dir": f"{root}/posts/<post_id>/replies/",
        },
        "global_media": f"{root}/media/global/",
        "sidecars": f"{root}/sidecars/",
    }


def build_public_audio_export_layout() -> Mapping[str, Any]:
    root = "source_exports/public_broadcast_catchup_audio/lbc/capture_20260912T000000Z"
    return {
        "root": root,
        "manifest": f"{root}/manifest.json",
        "episode_markdown": f"{root}/episode.md",
        "episode_json": f"{root}/episode.json",
        "media_original": f"{root}/media/original.m4a",
        "sidecars": {
            "info_json": f"{root}/sidecars/info.json",
            "description": f"{root}/sidecars/description.txt",
            "thumbnail_glob": f"{root}/sidecars/thumbnail.*",
        },
        "media_index": f"{root}/media_index.json",
        "media_candidates": f"{root}/media_candidates.ndjson",
        "media_download_plan": f"{root}/media_download_plan.json",
        "review_strings": f"{root}/review_strings.txt",
    }


def build_generic_article_export_layout() -> Mapping[str, Any]:
    root = "source_exports/news_websites/metro.co.uk/capture_20260912T000000Z"
    return {
        "root": root,
        "manifest": f"{root}/manifest.json",
        "article_markdown": f"{root}/article.md",
        "article_json": f"{root}/article.json",
        "article_text": f"{root}/article_text.txt",
        "media_article": f"{root}/media/article/",
        "media_embedded": f"{root}/media/embedded/",
        "screenshots": f"{root}/screenshots/",
        "media_index": f"{root}/media_index.json",
        "media_candidates": f"{root}/media_candidates.ndjson",
        "media_download_plan": f"{root}/media_download_plan.json",
        "review_strings": f"{root}/review_strings.txt",
    }


def build_sample_candidates() -> tuple[MediaCandidate, ...]:
    return (
        build_global_player_media_candidate(),
        build_twitter_sample_media_candidate(),
        build_generic_article_sample_media_candidate(),
    )


def build_sample_plans() -> tuple[MediaMaterializationPlan, ...]:
    global_candidate, twitter_candidate, article_candidate = build_sample_candidates()
    return (
        build_global_player_materialization_plan(),
        build_materialization_plan_for_candidate(twitter_candidate, output_root="source_exports/twitter_x/examaddaorg/capture_20260912T000000Z"),
        build_materialization_plan_for_candidate(article_candidate, output_root="source_exports/news_websites/metro.co.uk/capture_20260912T000000Z"),
    )


def _machine_fields_are_plain(candidates: Sequence[MediaCandidate], plans: Sequence[MediaMaterializationPlan]) -> tuple[bool, str]:
    failures: list[str] = []
    for candidate in candidates:
        item = candidate.with_derived_fields()
        for field in ("source_url", "canonical_source_url", "raw_media_url", "canonical_media_url", "relative_output_path"):
            value = str(getattr(item, field))
            if value and not is_plain_machine_field(value):
                failures.append(f"{item.candidate_id}:{field}={value}")
        for value in item.review_strings:
            if ("://" in value or "/" in value) and not is_plain_machine_field(value):
                failures.append(f"{item.candidate_id}:review={value}")
    for plan in plans:
        for field in ("relative_output_path",):
            value = str(getattr(plan, field))
            if value and not is_plain_machine_field(value):
                failures.append(f"{plan.plan_id}:{field}={value}")
    return (not failures, "; ".join(failures))


def _blocked_or_metadata_not_promoted(candidates: Sequence[MediaCandidate], plans: Sequence[MediaMaterializationPlan]) -> bool:
    plan_by_candidate = {plan.candidate_id: plan for plan in plans}
    for candidate in candidates:
        item = candidate.with_derived_fields()
        if item.access_status in BLOCKED_OR_METADATA_STATUSES:
            plan = plan_by_candidate.get(item.candidate_id)
            if plan and plan.status not in BLOCKED_OR_METADATA_STATUSES:
                return False
    return True


def validate_universal_media_method_matrix(source_root: str | Path = ".") -> R42GIReport:
    candidates = build_sample_candidates()
    plans = build_sample_plans()
    plain_ok, plain_detail = _machine_fields_are_plain(candidates, plans)
    slot_by_family = {slot.source_family: slot for slot in MEDIA_METHOD_SLOTS}
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    all_discovery = {method for slot in MEDIA_METHOD_SLOTS for method in slot.discovery_methods}
    all_roles = {role for slot in MEDIA_METHOD_SLOTS for role in slot.media_roles}
    all_kinds = {kind for slot in MEDIA_METHOD_SLOTS for kind in slot.media_kinds}
    checks = (
        _check("all_media_kinds_present", set(MEDIA_KINDS).issubset(all_kinds), f"covered={len(all_kinds)} required={len(MEDIA_KINDS)}"),
        _check("all_discovery_methods_present", set(DISCOVERY_METHODS).issubset(all_discovery), f"covered={len(all_discovery)} required={len(DISCOVERY_METHODS)}"),
        _check("all_media_roles_present", set(MEDIA_ROLES).issubset(all_roles), f"covered={len(all_roles)} required={len(MEDIA_ROLES)}"),
        _check("candidate_schema_complete", set(MEDIA_CANDIDATE_SCHEMA_FIELDS).issubset(set(MediaCandidate.__dataclass_fields__))),
        _check("materialization_plan_schema_complete", set(MATERIALIZATION_PLAN_SCHEMA_FIELDS).issubset(set(MediaMaterializationPlan.__dataclass_fields__))),
        _check("fast_queue_policy_present", len(FAST_QUEUE_POLICY) >= 10 and "support_pause_recovery_resume_keys" in FAST_QUEUE_POLICY),
        _check("twitter_x_media_slots_present", "twitter_x" in slot_by_family and "browser_network_observed_media" in slot_by_family["twitter_x"].discovery_methods),
        _check("generic_article_media_slots_present", "news_websites" in slot_by_family and "api3128_jdownloader" in slot_by_family["news_websites"].materialization_methods),
        _check("public_audio_media_slots_present", "public_broadcast_catchup_audio" in slot_by_family and "yt_dlp_python_module" in slot_by_family["public_broadcast_catchup_audio"].materialization_methods),
        _check("global_player_fixture_preserved", build_global_player_media_candidate().canonical_source_url == sanitize_source_url(GLOBAL_PLAYER_LBC_FIXTURE_URL) and build_global_player_materialization_plan().preferred_method == "yt_dlp_python_module"),
        _check("raw_machine_urls_not_markdown", plain_ok, plain_detail),
        _check("review_string_bridge_present", all(candidate.with_derived_fields().review_strings for candidate in candidates)),
        _check("no_metadata_or_review_required_promotion", _blocked_or_metadata_not_promoted(candidates, plans)),
        _check("side_effect_boundary_declared", "no media download" in SIDE_EFFECT_BOUNDARY and "no source-role" in SIDE_EFFECT_BOUNDARY),
        _check("r42gg_r42gh_still_green", r42gh.status == R42GH_PASS_STATUS, r42gh.status),
    )
    status = R42GI_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GI_BLOCKED_STATUS
    return R42GIReport(
        marker=R42GI_MARKER,
        schema_version=R42GI_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(Path(source_root)),
        status=status,
        checks=checks,
        media_kind_count=len(MEDIA_KINDS),
        discovery_method_count=len(DISCOVERY_METHODS),
        media_role_count=len(MEDIA_ROLES),
        method_slots=tuple(slot.to_dict() for slot in MEDIA_METHOD_SLOTS),
        sample_candidates=tuple(candidate.to_dict() for candidate in candidates),
        sample_plans=tuple(plan.to_dict() for plan in plans),
        fast_queue_policy=FAST_QUEUE_POLICY,
    )


def source_matrix_as_dict() -> Mapping[str, Any]:
    return {
        "capture_statuses": list(CAPTURE_STATUSES),
        "discovery_methods": list(DISCOVERY_METHODS),
        "fast_queue_policy": list(FAST_QUEUE_POLICY),
        "media_candidate_schema_fields": list(MEDIA_CANDIDATE_SCHEMA_FIELDS),
        "media_kinds": list(MEDIA_KINDS),
        "media_roles": list(MEDIA_ROLES),
        "method_slots": [slot.to_dict() for slot in MEDIA_METHOD_SLOTS],
        "r42gi_marker": R42GI_MARKER,
        "twitter_x_dynamic_benchmark": dict(TWITTER_X_DYNAMIC_BENCHMARK),
    }


def _write_report(output_root: Path, report: R42GIReport) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "R42GI_UNIVERSAL_MEDIA_METHOD_MATRIX_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "R42GI_UNIVERSAL_MEDIA_METHOD_MATRIX_REPORT.md").write_text(
        _report_markdown(report),
        encoding="utf-8",
    )
    (output_root / "R42GI_UNIVERSAL_MEDIA_METHOD_MATRIX.json").write_text(
        json.dumps(source_matrix_as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "R42GI_MEDIA_CANDIDATE_SCHEMA.json").write_text(
        json.dumps({"fields": list(MEDIA_CANDIDATE_SCHEMA_FIELDS), "sample": build_global_player_media_candidate().to_dict()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "R42GI_MEDIA_MATERIALIZATION_PLAN_SCHEMA.json").write_text(
        json.dumps({"fields": list(MATERIALIZATION_PLAN_SCHEMA_FIELDS), "sample": build_global_player_materialization_plan().to_dict()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _report_markdown(report: R42GIReport) -> str:
    lines = [
        f"# {R42GI_MARKER}",
        "",
        f"Status: {report.status}",
        f"Generated: {report.generated_at}",
        f"Media kinds: {report.media_kind_count}",
        f"Discovery methods: {report.discovery_method_count}",
        f"Media roles: {report.media_role_count}",
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
            "## Fast Queue Policy",
        ]
    )
    lines.extend(f"- {item}" for item in FAST_QUEUE_POLICY)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GI_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gi_universal_media_method_matrix")
    args = parser.parse_args(argv)
    report = validate_universal_media_method_matrix(args.source_root)
    _write_report(Path(args.output_root), report)
    print(R42GI_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "CAPTURE_STATUSES",
    "DISCOVERY_METHODS",
    "FAST_QUEUE_POLICY",
    "MATERIALIZATION_PLAN_SCHEMA_FIELDS",
    "MEDIA_CANDIDATE_SCHEMA_FIELDS",
    "MEDIA_KINDS",
    "MEDIA_METHOD_SLOTS",
    "MEDIA_ROLES",
    "MediaCandidate",
    "MediaMaterializationPlan",
    "MediaMethodSlot",
    "R42GI_BLOCKED_STATUS",
    "R42GI_MARKER",
    "R42GI_PASS_STATUS",
    "R42GIReport",
    "build_generic_article_export_layout",
    "build_generic_article_sample_media_candidate",
    "build_global_player_materialization_plan",
    "build_global_player_media_candidate",
    "build_media_export_layout",
    "build_public_audio_export_layout",
    "build_sample_candidates",
    "build_sample_plans",
    "build_twitter_sample_media_candidate",
    "source_matrix_as_dict",
    "validate_universal_media_method_matrix",
]


if __name__ == "__main__":
    raise SystemExit(main())
