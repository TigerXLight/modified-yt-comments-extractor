from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from profile_media_source_map_raw_url_audio_catchup_r42gh import (
    GLOBAL_PLAYER_LBC_FIXTURE_URL,
    GLOBAL_PLAYER_METHOD_METADATA,
    R42GH_PASS_STATUS,
    build_lbc_global_player_evidence_record,
    validate_source_map_raw_url_audio_catchup,
)
from profile_media_universal_media_method_matrix_r42gi import (
    R42GI_PASS_STATUS,
    build_generic_article_sample_media_candidate,
    build_global_player_media_candidate,
    build_twitter_sample_media_candidate,
    validate_universal_media_method_matrix,
)
from profile_media_universal_source_map_r42gg import (
    R42GG_PASS_STATUS,
    SIDE_EFFECT_BOUNDARY,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_REVIEW_REQUIRED,
    sanitize_source_url,
    validate_universal_source_map,
)

R42GJ_MARKER = "YTCE_R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX"
R42GJ_PASS_STATUS = "PASS_R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX"
R42GJ_BLOCKED_STATUS = "BLOCKED_R42GJ_WITH_EXACT_BLOCKER"
R42GJ_SCHEMA_VERSION = "universal_evidence_bundle_review_string_index.r42gj.v1"

PROMOTION_NONE = "not_promoted_review_bridge_only"
ROLE_STATUS_COMPAT = "compatible_bridge_not_role_assignment"
SOURCE_ROLE_EFFECT_NONE = "none_contract_only"

EVIDENCE_RECORD_SCHEMA_FIELDS: tuple[str, ...] = (
    "schema_version",
    "evidence_id",
    "record_type",
    "source_family",
    "platform_or_provider",
    "source_url",
    "canonical_url",
    "raw_url",
    "capture_time_iso",
    "capture_timezone",
    "access_status",
    "capture_method_id",
    "parent_record_id",
    "child_record_ids",
    "title",
    "display_name",
    "handle_or_author",
    "created_at_text",
    "created_at_iso_if_known",
    "text",
    "quoted_text",
    "stats",
    "language_hint",
    "media_candidate_ids",
    "comments_index_path",
    "replies_index_path",
    "thread_index_path",
    "timeline_index_path",
    "archive_snapshot_path",
    "source_role_status",
    "review_status",
    "promotion_status",
    "blocked_reason",
    "requires_human_chain",
    "requires_login",
    "requires_manual_receipt",
    "side_effect_boundary",
    "review_strings",
    "source_fingerprint",
)

BUNDLE_MANIFEST_SCHEMA_FIELDS: tuple[str, ...] = (
    "schema_version",
    "bundle_id",
    "source_family",
    "platform_or_provider",
    "source_url",
    "canonical_url",
    "capture_time_iso",
    "capture_timezone",
    "capture_method_id",
    "access_status",
    "root_output_path",
    "records_index_path",
    "review_strings_path",
    "media_index_path",
    "comments_index_path",
    "progress_events_path",
    "audit_log_path",
    "source_role_bridge_path",
    "record_count",
    "media_candidate_count",
    "comment_count",
    "reply_count",
    "side_effect_boundary",
    "promotion_policy",
)

REVIEW_STRING_INDEX_SCHEMA_FIELDS: tuple[str, ...] = (
    "schema_version",
    "bundle_id",
    "index_path",
    "strings",
    "records_by_string",
    "source_roles_by_string",
    "media_candidates_by_string",
    "normalization_policy",
    "plain_url_policy",
)

SOURCE_ROLE_BRIDGE_SCHEMA_FIELDS: tuple[str, ...] = (
    "bridge_id",
    "bundle_id",
    "evidence_id",
    "source_candidate_id",
    "source_family",
    "candidate_kind",
    "review_strings",
    "role_hint",
    "role_status",
    "promotion_status",
    "blocked_reason",
    "requires_review",
    "source_role_compatible",
    "no_jump_counter_safe",
)

MACHINE_URL_FIELDS = {
    "source_url",
    "canonical_url",
    "raw_url",
    "normalized_url",
    "canonical_source_url",
    "canonical_media_url",
    "raw_media_url",
    "thumbnail_url",
    "poster_url",
}


@dataclass(frozen=True)
class UniversalEvidenceRecord:
    evidence_id: str
    record_type: str
    source_family: str
    platform_or_provider: str
    source_url: str
    canonical_url: str
    raw_url: str
    capture_time_iso: str
    capture_timezone: str
    access_status: str
    capture_method_id: str
    parent_record_id: str = ""
    child_record_ids: tuple[str, ...] = ()
    title: str = ""
    display_name: str = ""
    handle_or_author: str = ""
    created_at_text: str = ""
    created_at_iso_if_known: str = ""
    text: str = ""
    quoted_text: str = ""
    stats: Mapping[str, str] | None = None
    language_hint: str = ""
    media_candidate_ids: tuple[str, ...] = ()
    comments_index_path: str = ""
    replies_index_path: str = ""
    thread_index_path: str = ""
    timeline_index_path: str = ""
    archive_snapshot_path: str = ""
    source_role_status: str = ROLE_STATUS_COMPAT
    review_status: str = STATUS_REVIEW_REQUIRED
    promotion_status: str = PROMOTION_NONE
    blocked_reason: str = ""
    requires_human_chain: bool = False
    requires_login: bool = False
    requires_manual_receipt: bool = False
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY
    review_strings: tuple[str, ...] = ()
    source_fingerprint: str = ""
    schema_version: str = R42GJ_SCHEMA_VERSION

    def with_derived_fields(self) -> "UniversalEvidenceRecord":
        canonical = sanitize_source_url(self.canonical_url or self.source_url)
        source_url = sanitize_source_url(self.source_url or canonical)
        raw_url = sanitize_source_url(self.raw_url or source_url)
        fingerprint = self.source_fingerprint or _fingerprint(
            [
                self.record_type,
                self.source_family,
                canonical,
                self.evidence_id,
                self.handle_or_author,
                _text_snippet(self.text or self.quoted_text),
                *self.media_candidate_ids,
            ]
        )
        data = asdict(self)
        data.update(
            {
                "canonical_url": canonical,
                "source_url": source_url,
                "raw_url": raw_url,
                "source_fingerprint": fingerprint,
            }
        )
        record = UniversalEvidenceRecord(**data)
        if not record.review_strings:
            data["review_strings"] = tuple(build_evidence_review_strings(record))
            record = UniversalEvidenceRecord(**data)
        return record

    def to_dict(self) -> dict[str, Any]:
        record = self.with_derived_fields()
        data = asdict(record)
        data["child_record_ids"] = list(record.child_record_ids)
        data["media_candidate_ids"] = list(record.media_candidate_ids)
        data["review_strings"] = list(record.review_strings)
        data["stats"] = dict(record.stats or {})
        return data


@dataclass(frozen=True)
class EvidenceBundleManifest:
    bundle_id: str
    source_family: str
    platform_or_provider: str
    source_url: str
    canonical_url: str
    capture_time_iso: str
    capture_timezone: str
    capture_method_id: str
    access_status: str
    root_output_path: str
    records_index_path: str
    review_strings_path: str
    media_index_path: str
    comments_index_path: str
    progress_events_path: str
    audit_log_path: str
    source_role_bridge_path: str
    record_count: int
    media_candidate_count: int
    comment_count: int
    reply_count: int
    promotion_policy: str = "metadata_review_blocked_not_promoted_by_bundle_contract"
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY
    schema_version: str = R42GJ_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_url"] = sanitize_source_url(data["source_url"])
        data["canonical_url"] = sanitize_source_url(data["canonical_url"])
        return data


@dataclass(frozen=True)
class ReviewStringIndex:
    bundle_id: str
    index_path: str
    strings: tuple[str, ...]
    records_by_string: Mapping[str, tuple[str, ...]]
    source_roles_by_string: Mapping[str, tuple[str, ...]]
    media_candidates_by_string: Mapping[str, tuple[str, ...]]
    normalization_policy: str = "sanitize_urls_normalize_whitespace_keep_human_text"
    plain_url_policy: str = "url_like_strings_are_plain_not_markdown"
    schema_version: str = R42GJ_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "index_path": self.index_path,
            "media_candidates_by_string": {key: list(values) for key, values in self.media_candidates_by_string.items()},
            "normalization_policy": self.normalization_policy,
            "plain_url_policy": self.plain_url_policy,
            "records_by_string": {key: list(values) for key, values in self.records_by_string.items()},
            "schema_version": self.schema_version,
            "source_roles_by_string": {key: list(values) for key, values in self.source_roles_by_string.items()},
            "strings": list(self.strings),
        }


@dataclass(frozen=True)
class SourceRoleBridgeRecord:
    bridge_id: str
    bundle_id: str
    evidence_id: str
    source_candidate_id: str
    source_family: str
    candidate_kind: str
    review_strings: tuple[str, ...]
    role_hint: str = "none"
    role_status: str = ROLE_STATUS_COMPAT
    promotion_status: str = PROMOTION_NONE
    blocked_reason: str = ""
    requires_review: bool = True
    source_role_compatible: bool = True
    no_jump_counter_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["review_strings"] = list(self.review_strings)
        return data


@dataclass(frozen=True)
class R42GJReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    evidence_record_schema: Mapping[str, Any]
    bundle_manifest_schema: Mapping[str, Any]
    review_string_index_schema: Mapping[str, Any]
    source_role_bridge_schema: Mapping[str, Any]
    folder_layouts: Mapping[str, Any]
    sample_bundles: tuple[Mapping[str, Any], ...]
    sample_records: tuple[Mapping[str, Any], ...]
    sample_review_indexes: tuple[Mapping[str, Any], ...]
    sample_source_role_bridges: tuple[Mapping[str, Any], ...]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GJ_PASS_STATUS and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_manifest_schema": dict(self.bundle_manifest_schema),
            "checks": [dict(check) for check in self.checks],
            "evidence_record_schema": dict(self.evidence_record_schema),
            "folder_layouts": dict(self.folder_layouts),
            "generated_at": self.generated_at,
            "marker": self.marker,
            "passed": self.passed,
            "review_string_index_schema": dict(self.review_string_index_schema),
            "sample_bundles": [dict(bundle) for bundle in self.sample_bundles],
            "sample_records": [dict(record) for record in self.sample_records],
            "sample_review_indexes": [dict(index) for index in self.sample_review_indexes],
            "sample_source_role_bridges": [dict(bridge) for bridge in self.sample_source_role_bridges],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_role_bridge_schema": dict(self.source_role_bridge_schema),
            "source_root": self.source_root,
            "status": self.status,
        }


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return tuple(output)


def _fingerprint(values: Sequence[str]) -> str:
    payload = "|".join(str(value or "") for value in values)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8', errors='replace')).hexdigest()[:24]}"


def _text_snippet(value: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _url_like(value: str) -> bool:
    return bool(re.match(r"(?i)^https?://", str(value or "").strip()))


def is_plain_machine_value(value: str) -> bool:
    text = str(value or "").strip()
    return not text.startswith("[") and "](" not in text


def schema_for(fields: Sequence[str]) -> Mapping[str, Any]:
    return {"schema_version": R42GJ_SCHEMA_VERSION, "fields": list(fields)}


def build_folder_layouts(capture_timestamp: str = "20260913T000000Z") -> Mapping[str, Any]:
    return {
        "twitter_x_single_post": {
            "root": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845",
            "post_md": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845/post.md",
            "post_json": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845/post.json",
            "media": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845/media/",
            "comments": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845/comments/",
            "replies": f"source_exports/twitter_x/BBCr4today/capture_{capture_timestamp}/posts/2097217541416308845/replies/",
        },
        "twitter_x_timeline": {
            "root": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}",
            "manifest": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/manifest.json",
            "timeline_md": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/timeline.md",
            "timeline_ndjson": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/timeline.ndjson",
            "progress_events": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/progress_events.ndjson",
            "review_strings": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/review_strings.txt",
            "media_index": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/media_index.json",
            "posts": f"source_exports/twitter_x/examaddaorg/capture_{capture_timestamp}/posts/<post_id>/",
        },
        "news_article": {
            "root": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}",
            "manifest": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/manifest.json",
            "article_md": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/article.md",
            "article_json": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/article.json",
            "media_index": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/media_index.json",
            "comments": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/comments/",
            "screenshots": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/screenshots/",
            "archive": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/archive/",
            "review_strings": f"source_exports/news_websites/metro.co.uk/capture_{capture_timestamp}/review_strings.txt",
        },
        "public_audio_global_player": {
            "root": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}",
            "manifest": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/manifest.json",
            "episode_md": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/episode.md",
            "episode_json": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/episode.json",
            "media_original": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/media/original.m4a",
            "sidecar_info": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/sidecars/info.json",
            "sidecar_description": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/sidecars/description.txt",
            "sidecar_thumbnail": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/sidecars/thumbnail.*",
            "review_strings": f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}/review_strings.txt",
        },
    }


def build_evidence_review_strings(record: UniversalEvidenceRecord) -> tuple[str, ...]:
    stats_text = " ".join(f"{key}: {value}" for key, value in sorted((record.stats or {}).items()) if value)
    status_id = _extract_status_id(record.canonical_url)
    episode_id = "2zGwFmzE7xNLAfiMVL5BMHmPeB" if "globalplayer.com" in record.canonical_url else ""
    article_slug = _extract_slug(record.canonical_url)
    media_paths = tuple(record.media_candidate_ids)
    values = [
        record.canonical_url,
        record.raw_url,
        record.source_url,
        sanitize_source_url(record.canonical_url),
        record.evidence_id,
        status_id,
        episode_id,
        article_slug,
        record.handle_or_author,
        record.display_name,
        record.title,
        record.created_at_text,
        _text_snippet(record.quoted_text),
        _text_snippet(record.text, 320),
        stats_text,
        record.comments_index_path,
        record.replies_index_path,
        record.thread_index_path,
        record.timeline_index_path,
        record.archive_snapshot_path,
        *media_paths,
        record.source_fingerprint,
        record.capture_method_id,
        record.platform_or_provider,
        record.source_family,
    ]
    return _dedupe([value for value in values if value])


def _extract_status_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else ""


def _extract_slug(url: str) -> str:
    path = re.sub(r"/+$", "", re.sub(r"^https?://[^/]+", "", url))
    return Path(path).name if path else ""


def build_twitter_single_post_record() -> UniversalEvidenceRecord:
    raw = "https://x.com/BBCr4today/status/2097217541416308845?s=20"
    canonical = sanitize_source_url(raw)
    post_id = "2097217541416308845"
    quote_text = "I think it carries a real risk of increased chances of attacks on the British Jewish community."
    body_text = (
        "Dr Peter Prinsley, vice chair of Labour Friends of Israel, tells @bbcnickrobinson that he warned "
        "Foreign Secretary Ed Miliband about the risk of implementing sanctions on goods and services from "
        "West Bank settlements."
    )
    record = UniversalEvidenceRecord(
        evidence_id=f"twitter_x:post:{post_id}",
        record_type="post/status",
        source_family="twitter_x",
        platform_or_provider="X/Twitter",
        source_url=canonical,
        canonical_url=canonical,
        raw_url=raw,
        capture_time_iso="2026-09-13T00:00:00Z",
        capture_timezone="UTC",
        access_status=STATUS_REVIEW_REQUIRED,
        capture_method_id="extension_manual_receipt_or_local_exporter_import_contract",
        title="BBC Radio 4 Today status 2097217541416308845",
        display_name="BBC Radio 4 Today",
        handle_or_author="@BBCr4today",
        created_at_text="7:56 AM · Sep 8, 2026",
        text=body_text,
        quoted_text=quote_text,
        stats={
            "views": "256K",
            "comments": "309",
            "retweets": "76",
            "likes": "92",
            "bookmarks": "40",
        },
        language_hint="en",
        media_candidate_ids=("media:twitter_x:BBCr4today:2097217541416308845:receipt_media",),
        comments_index_path=f"posts/{post_id}/comments/",
        replies_index_path=f"posts/{post_id}/replies/",
        review_status=STATUS_REVIEW_REQUIRED,
        promotion_status=PROMOTION_NONE,
        requires_human_chain=True,
        requires_manual_receipt=True,
    )
    return record.with_derived_fields()


def render_twitter_post_card(record: UniversalEvidenceRecord) -> str:
    record = record.with_derived_fields()
    stats = record.stats or {}
    post_id = _extract_status_id(record.canonical_url)
    return "\n".join(
        [
            record.display_name,
            record.handle_or_author,
            f'"{record.quoted_text}"',
            "",
            record.text,
            "",
            f"{record.created_at_text} · {stats.get('views', '')} Views".strip(),
            f"{stats.get('comments', '')} comments {stats.get('retweets', '')} Retweets {stats.get('likes', '')} Likes {stats.get('bookmarks', '')} Bookmarks".strip(),
            f"Captured: {record.capture_time_iso} {record.capture_timezone}",
            f"Source URL: {record.canonical_url}",
            f"Media folder: posts/{post_id}/media/",
            f"Comments folder: posts/{post_id}/comments/",
            f"Replies folder: posts/{post_id}/replies/",
        ]
    )


def build_twitter_timeline_record() -> UniversalEvidenceRecord:
    raw = "https://x.com/examaddaorg?utm_source=test&s=20"
    canonical = sanitize_source_url(raw)
    return UniversalEvidenceRecord(
        evidence_id="twitter_x:timeline:examaddaorg",
        record_type="timeline/account_export",
        source_family="twitter_x",
        platform_or_provider="X/Twitter",
        source_url=canonical,
        canonical_url=canonical,
        raw_url=raw,
        capture_time_iso="2026-09-13T00:00:00Z",
        capture_timezone="UTC",
        access_status=STATUS_REVIEW_REQUIRED,
        capture_method_id="dynamic_gradual_discovery_receipt_contract",
        title="examaddaorg timeline/account export",
        display_name="examaddaorg",
        handle_or_author="@examaddaorg",
        text=(
            "Observed benchmark context: 6.7k records, 8.9 MB, pause/recovery around 01:07, "
            "completed around 08:13. This is not a hard-coded threshold, limit, or guarantee."
        ),
        stats={"observed_records": "6.7k", "observed_bytes": "8.9 MB", "hard_limit": "none"},
        media_candidate_ids=(build_twitter_sample_media_candidate().candidate_id,),
        timeline_index_path="timeline.ndjson",
        review_status=STATUS_REVIEW_REQUIRED,
        promotion_status=PROMOTION_NONE,
        requires_human_chain=True,
    ).with_derived_fields()


def build_news_article_record() -> UniversalEvidenceRecord:
    canonical = "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"
    candidate = build_generic_article_sample_media_candidate()
    return UniversalEvidenceRecord(
        evidence_id="news_websites:article:metro_seagull_eater_20260717",
        record_type="article",
        source_family="news_websites",
        platform_or_provider="Metro",
        source_url=canonical,
        canonical_url=canonical,
        raw_url=canonical,
        capture_time_iso="2026-09-13T00:00:00Z",
        capture_timezone="UTC",
        access_status=STATUS_METADATA_ONLY_UNTIL_CAPTURED,
        capture_method_id="generic_article_lane_contract",
        title="People shout seagull eater at me in the street after far right lies",
        display_name="Metro",
        handle_or_author="Barney Davis",
        created_at_text="Published July 17, 2026",
        text="Metro article source text and media candidates bridge to review strings when cached/captured material exists.",
        media_candidate_ids=(candidate.candidate_id,),
        comments_index_path="comments/",
        archive_snapshot_path="archive/",
        review_status=STATUS_REVIEW_REQUIRED,
        promotion_status=PROMOTION_NONE,
    ).with_derived_fields()


def build_global_player_audio_record() -> UniversalEvidenceRecord:
    evidence = build_lbc_global_player_evidence_record()
    candidate = build_global_player_media_candidate()
    return UniversalEvidenceRecord(
        evidence_id=f"public_broadcast_catchup_audio:episode:{evidence.episode_id}",
        record_type="episode/audio_item",
        source_family="public_broadcast_catchup_audio",
        platform_or_provider="Global Player",
        source_url=evidence.canonical_url,
        canonical_url=evidence.canonical_url,
        raw_url=GLOBAL_PLAYER_LBC_FIXTURE_URL,
        capture_time_iso=evidence.capture_time_iso,
        capture_timezone=evidence.capture_timezone,
        access_status=STATUS_REVIEW_REQUIRED,
        capture_method_id=str(GLOBAL_PLAYER_METHOD_METADATA["backend_id"]),
        title=evidence.episode_title,
        display_name=evidence.programme_or_show,
        handle_or_author=evidence.station_or_publisher,
        text="Public catch-up audio episode with native M4A preservation contract and sidecars.",
        media_candidate_ids=(candidate.candidate_id,),
        review_status=STATUS_REVIEW_REQUIRED,
        promotion_status=PROMOTION_NONE,
    ).with_derived_fields()


def build_sample_records() -> tuple[UniversalEvidenceRecord, ...]:
    return (
        build_twitter_single_post_record(),
        build_twitter_timeline_record(),
        build_news_article_record(),
        build_global_player_audio_record(),
    )


def build_bundle_manifest(record: UniversalEvidenceRecord, layout: Mapping[str, str], *, record_count: int = 1, media_candidate_count: int = 0) -> EvidenceBundleManifest:
    root = str(layout.get("root") or "")
    return EvidenceBundleManifest(
        bundle_id=f"bundle:{record.evidence_id}",
        source_family=record.source_family,
        platform_or_provider=record.platform_or_provider,
        source_url=record.source_url,
        canonical_url=record.canonical_url,
        capture_time_iso=record.capture_time_iso,
        capture_timezone=record.capture_timezone,
        capture_method_id=record.capture_method_id,
        access_status=record.access_status,
        root_output_path=root,
        records_index_path=f"{root}/records.ndjson",
        review_strings_path=str(layout.get("review_strings") or f"{root}/review_strings.txt"),
        media_index_path=str(layout.get("media_index") or f"{root}/media_index.json"),
        comments_index_path=str(layout.get("comments") or f"{root}/comments/"),
        progress_events_path=str(layout.get("progress_events") or f"{root}/progress_events.ndjson"),
        audit_log_path=f"{root}/audit_log.ndjson",
        source_role_bridge_path=f"{root}/source_role_bridge.json",
        record_count=record_count,
        media_candidate_count=media_candidate_count,
        comment_count=0,
        reply_count=0,
    )


def build_sample_bundles() -> tuple[EvidenceBundleManifest, ...]:
    layouts = build_folder_layouts()
    single, timeline, news, audio = build_sample_records()
    return (
        build_bundle_manifest(single, layouts["twitter_x_single_post"], media_candidate_count=1),
        build_bundle_manifest(timeline, layouts["twitter_x_timeline"], record_count=1, media_candidate_count=1),
        build_bundle_manifest(news, layouts["news_article"], media_candidate_count=1),
        build_bundle_manifest(audio, layouts["public_audio_global_player"], media_candidate_count=1),
    )


def build_source_role_bridge(record: UniversalEvidenceRecord, bundle_id: str, candidate_kind: str = "evidence_record") -> SourceRoleBridgeRecord:
    record = record.with_derived_fields()
    return SourceRoleBridgeRecord(
        bridge_id=f"bridge:{record.evidence_id}",
        bundle_id=bundle_id,
        evidence_id=record.evidence_id,
        source_candidate_id=record.evidence_id,
        source_family=record.source_family,
        candidate_kind=candidate_kind,
        review_strings=record.review_strings,
        blocked_reason=record.blocked_reason,
        requires_review=True,
        source_role_compatible=True,
        no_jump_counter_safe=True,
    )


def build_review_string_index(bundle: EvidenceBundleManifest, records: Sequence[UniversalEvidenceRecord], bridges: Sequence[SourceRoleBridgeRecord]) -> ReviewStringIndex:
    records_by_string: dict[str, set[str]] = {}
    source_roles_by_string: dict[str, set[str]] = {}
    media_candidates_by_string: dict[str, set[str]] = {}
    strings: list[str] = []
    for record in records:
        derived = record.with_derived_fields()
        for value in derived.review_strings:
            records_by_string.setdefault(value, set()).add(derived.evidence_id)
            strings.append(value)
        for candidate_id in derived.media_candidate_ids:
            media_candidates_by_string.setdefault(candidate_id, set()).add(candidate_id)
            strings.append(candidate_id)
    for bridge in bridges:
        for value in bridge.review_strings:
            source_roles_by_string.setdefault(value, set()).add(bridge.bridge_id)
            strings.append(value)
    return ReviewStringIndex(
        bundle_id=bundle.bundle_id,
        index_path=bundle.review_strings_path,
        strings=_dedupe(strings),
        records_by_string={key: tuple(sorted(values)) for key, values in records_by_string.items()},
        source_roles_by_string={key: tuple(sorted(values)) for key, values in source_roles_by_string.items()},
        media_candidates_by_string={key: tuple(sorted(values)) for key, values in media_candidates_by_string.items()},
    )


def build_sample_review_indexes() -> tuple[ReviewStringIndex, ...]:
    records = build_sample_records()
    bundles = build_sample_bundles()
    output: list[ReviewStringIndex] = []
    for record, bundle in zip(records, bundles):
        bridge = build_source_role_bridge(record, bundle.bundle_id)
        output.append(build_review_string_index(bundle, (record,), (bridge,)))
    return tuple(output)


def build_sample_source_role_bridges() -> tuple[SourceRoleBridgeRecord, ...]:
    return tuple(build_source_role_bridge(record, bundle.bundle_id) for record, bundle in zip(build_sample_records(), build_sample_bundles()))


def machine_url_fields_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(machine_url_fields_are_plain(item, child_key) for child_key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(machine_url_fields_are_plain(item, key) for item in value)
    if key in MACHINE_URL_FIELDS:
        return is_plain_machine_value(str(value or ""))
    return True


def url_like_review_strings_are_plain(indexes: Sequence[ReviewStringIndex], records: Sequence[UniversalEvidenceRecord]) -> bool:
    values: list[str] = []
    for index in indexes:
        values.extend(index.strings)
    for record in records:
        values.extend(record.with_derived_fields().review_strings)
    for value in values:
        if _url_like(value) and not is_plain_machine_value(value):
            return False
    return True


def metadata_review_blocked_not_promoted(records: Sequence[UniversalEvidenceRecord], bridges: Sequence[SourceRoleBridgeRecord]) -> bool:
    for record in records:
        if record.review_status in {STATUS_REVIEW_REQUIRED, STATUS_METADATA_ONLY_UNTIL_CAPTURED} and record.promotion_status != PROMOTION_NONE:
            return False
    for bridge in bridges:
        if bridge.promotion_status != PROMOTION_NONE:
            return False
    return True


def build_report(source_root: str | Path = ".") -> R42GJReport:
    records = build_sample_records()
    bundles = build_sample_bundles()
    indexes = build_sample_review_indexes()
    bridges = build_sample_source_role_bridges()
    layouts = build_folder_layouts()
    r42gg = validate_universal_source_map(source_root)
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    r42gi = validate_universal_media_method_matrix(source_root)
    all_payloads: list[Any] = [record.to_dict() for record in records]
    all_payloads.extend(bundle.to_dict() for bundle in bundles)
    all_payloads.extend(index.to_dict() for index in indexes)
    all_payloads.extend(bridge.to_dict() for bridge in bridges)
    checks = (
        _check("evidence_record_schema_complete", set(EVIDENCE_RECORD_SCHEMA_FIELDS).issubset(set(UniversalEvidenceRecord.__dataclass_fields__))),
        _check("bundle_manifest_schema_complete", set(BUNDLE_MANIFEST_SCHEMA_FIELDS).issubset(set(EvidenceBundleManifest.__dataclass_fields__))),
        _check("review_string_index_schema_complete", set(REVIEW_STRING_INDEX_SCHEMA_FIELDS).issubset(set(ReviewStringIndex.__dataclass_fields__))),
        _check("source_role_bridge_schema_complete", set(SOURCE_ROLE_BRIDGE_SCHEMA_FIELDS).issubset(set(SourceRoleBridgeRecord.__dataclass_fields__))),
        _check("twitter_single_post_card_layout_present", "Media folder: posts/2097217541416308845/media/" in render_twitter_post_card(records[0])),
        _check("twitter_timeline_layout_present", "twitter_x_timeline" in layouts and "timeline_ndjson" in layouts["twitter_x_timeline"]),
        _check("news_article_layout_present", "news_article" in layouts and "article_json" in layouts["news_article"]),
        _check("public_audio_layout_present", "public_audio_global_player" in layouts and "media_original" in layouts["public_audio_global_player"]),
        _check("global_player_fixture_preserved", records[-1].canonical_url == sanitize_source_url(GLOBAL_PLAYER_LBC_FIXTURE_URL) and str(GLOBAL_PLAYER_METHOD_METADATA["backend_id"]) == "yt_dlp_python_module"),
        _check("r42gi_media_candidates_linked", any("media:public_broadcast_catchup_audio" in item for record in records for item in record.media_candidate_ids)),
        _check("plain_machine_urls_not_markdown", all(machine_url_fields_are_plain(payload) for payload in all_payloads) and url_like_review_strings_are_plain(indexes, records)),
        _check("review_strings_bridge_required_fields", all(record.with_derived_fields().canonical_url in record.with_derived_fields().review_strings for record in records)),
        _check("metadata_review_blocked_not_promoted", metadata_review_blocked_not_promoted(records, bridges)),
        _check("source_role_bridge_guardrail", all(bridge.source_role_compatible and bridge.no_jump_counter_safe and bridge.role_hint == "none" for bridge in bridges)),
        _check("side_effect_boundary_declared", SIDE_EFFECT_BOUNDARY in records[0].side_effect_boundary),
        _check("prior_green_layers_import", r42gg.status == R42GG_PASS_STATUS and r42gh.status == R42GH_PASS_STATUS and r42gi.status == R42GI_PASS_STATUS, f"{r42gg.status} {r42gh.status} {r42gi.status}"),
    )
    status = R42GJ_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GJ_BLOCKED_STATUS
    return R42GJReport(
        marker=R42GJ_MARKER,
        schema_version=R42GJ_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(source_root),
        status=status,
        evidence_record_schema=schema_for(EVIDENCE_RECORD_SCHEMA_FIELDS),
        bundle_manifest_schema=schema_for(BUNDLE_MANIFEST_SCHEMA_FIELDS),
        review_string_index_schema=schema_for(REVIEW_STRING_INDEX_SCHEMA_FIELDS),
        source_role_bridge_schema=schema_for(SOURCE_ROLE_BRIDGE_SCHEMA_FIELDS),
        folder_layouts=layouts,
        sample_bundles=tuple(bundle.to_dict() for bundle in bundles),
        sample_records=tuple(record.to_dict() for record in records),
        sample_review_indexes=tuple(index.to_dict() for index in indexes),
        sample_source_role_bridges=tuple(bridge.to_dict() for bridge in bridges),
        checks=checks,
    )


def _report_markdown(report: R42GJReport) -> str:
    lines = [
        "# R42GJ Universal Evidence Bundle + Review String Index",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Schema version: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(
        [
            "",
            "## Side Effect Boundary",
            report.side_effect_boundary,
            "",
            "## Sample Twitter/X Post Card",
            "```text",
            render_twitter_post_card(build_twitter_single_post_record()),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(report: R42GJReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    outputs = {
        "R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX_REPORT.json": payload,
        "R42GJ_EVIDENCE_RECORD_SCHEMA.json": report.evidence_record_schema,
        "R42GJ_BUNDLE_MANIFEST_SCHEMA.json": report.bundle_manifest_schema,
        "R42GJ_REVIEW_STRING_INDEX_SCHEMA.json": report.review_string_index_schema,
        "R42GJ_SOURCE_ROLE_BRIDGE_SCHEMA.json": report.source_role_bridge_schema,
        "R42GJ_SAMPLE_BUNDLES.json": [dict(bundle) for bundle in report.sample_bundles],
        "R42GJ_SAMPLE_REVIEW_INDEXES.json": [dict(index) for index in report.sample_review_indexes],
        "R42GJ_SAMPLE_SOURCE_ROLE_BRIDGES.json": [dict(bridge) for bridge in report.sample_source_role_bridges],
    }
    for filename, data in outputs.items():
        (root / filename).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (root / "R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the R42GJ universal evidence bundle/review-string index report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gj_universal_evidence_bundle_index")
    args = parser.parse_args(argv)
    report = build_report(args.source_root)
    write_report(report, args.output_root)
    print(R42GJ_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GJ_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
