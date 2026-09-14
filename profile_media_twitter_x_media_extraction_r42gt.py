from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from profile_media_universal_media_method_matrix_r42gi import R42GI_PASS_STATUS, validate_universal_media_method_matrix
from profile_media_universal_source_map_r42gg import SIDE_EFFECT_BOUNDARY, sanitize_source_url
from profile_media_youtube_comment_sort_spam_review_r42gs import R42GS_PASS_STATUS, generate_r42gs_report

R42GT_MARKER = "YTCE_R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA"
R42GT_PASS_STATUS = "PASS_R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA"
R42GT_BLOCKED_STATUS = "BLOCKED_R42GT_WITH_EXACT_BLOCKER"
R42GT_SCHEMA_VERSION = "twitter_x_media_extraction_route_schema.r42gt.v1"

PROMOTION_NONE = "not_promoted_review_bridge_only"
SOURCE_ROLE_BRIDGE_COMPAT = "compatible_bridge_not_role_assignment"
REVIEW_METADATA_ONLY = "metadata_only_review_required"
LOCAL_FIXTURE_COPIED = "local_fixture_copied_with_sha256"
REMOTE_NOT_DOWNLOADED = "remote_candidate_not_downloaded_by_r42gt"

MACHINE_URL_FIELDS = {
    "source_url",
    "canonical_source_url",
    "post_url",
    "canonical_post_url",
    "media_url",
    "canonical_media_url",
    "thumbnail_url",
    "preview_url",
}

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "igsh",
    "mc_cid",
    "mc_eid",
    "ref_src",
    "s",
    "si",
}

MEDIA_ITEM_SCHEMA_FIELDS: tuple[str, ...] = (
    "media_id",
    "post_id",
    "source_family",
    "source_url",
    "canonical_source_url",
    "post_url",
    "canonical_post_url",
    "media_kind",
    "media_role",
    "media_url",
    "canonical_media_url",
    "thumbnail_url",
    "preview_url",
    "alt_text",
    "width",
    "height",
    "duration_seconds",
    "mime_type",
    "filename",
    "local_fixture_path",
    "relative_output_path",
    "sha256",
    "capture_method_id",
    "capture_method_detail",
    "requires_human_authorized_session",
    "access_mode",
    "review_status",
    "promotion_status",
    "media_file_status",
    "review_strings",
)

POST_RECORD_SCHEMA_FIELDS: tuple[str, ...] = (
    "post_id",
    "account_handle",
    "display_name",
    "source_url",
    "canonical_source_url",
    "post_url",
    "canonical_post_url",
    "created_at_text",
    "text",
    "quoted_text",
    "stats",
    "media_items",
    "review_strings",
    "source_role_bridge_status",
    "promotion_status",
)

PACKAGE_MANIFEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "marker",
    "status",
    "source_family",
    "account_or_unknown",
    "capture_timestamp",
    "root_output_path",
    "post_count",
    "media_candidate_count",
    "local_fixture_media_count",
    "remote_metadata_only_count",
    "capability_metadata",
    "source_role_bridge_status",
    "promotion_status",
    "review_strings_path",
    "media_index_path",
)


@dataclass(frozen=True)
class TwitterXMediaItem:
    media_id: str
    post_id: str
    source_url: str
    post_url: str
    media_kind: str
    media_role: str
    media_url: str = ""
    thumbnail_url: str = ""
    preview_url: str = ""
    alt_text: str = ""
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    mime_type: str = ""
    filename: str = ""
    local_fixture_path: str = ""
    relative_output_path: str = ""
    sha256: str = ""
    capture_method_id: str = "twitter_x_media_receipt_or_future_visible_browser_resource"
    capture_method_detail: str = "registered_schema_only_no_live_capture_by_r42gt"
    requires_human_authorized_session: bool = True
    access_mode: str = "human_authorized_visible_session_or_user_supplied_receipt_required"
    review_status: str = REVIEW_METADATA_ONLY
    promotion_status: str = PROMOTION_NONE
    media_file_status: str = REMOTE_NOT_DOWNLOADED
    review_strings: tuple[str, ...] = ()
    source_family: str = "twitter_x"
    canonical_source_url: str = ""
    canonical_post_url: str = ""
    canonical_media_url: str = ""

    def with_derived_fields(self) -> "TwitterXMediaItem":
        canonical_source = sanitize_plain_url(self.canonical_source_url or self.source_url)
        canonical_post = sanitize_plain_url(self.canonical_post_url or self.post_url or canonical_source)
        canonical_media = sanitize_plain_url(self.canonical_media_url or self.media_url) if (self.canonical_media_url or self.media_url) else ""
        suggested = self.filename or _filename_from_url(canonical_media, self.media_kind, self.media_id)
        rel = self.relative_output_path or f"posts/{_safe_segment(self.post_id, 'post')}/media/{suggested}"
        review = self.review_strings or tuple(
            _dedupe(
                [
                    canonical_source,
                    self.source_url,
                    canonical_post,
                    self.post_url,
                    self.post_id,
                    self.media_id,
                    canonical_media,
                    self.media_url,
                    self.thumbnail_url,
                    self.preview_url,
                    suggested,
                    rel,
                    self.media_kind,
                    self.media_role,
                    self.capture_method_id,
                ]
            )
        )
        data = asdict(self)
        data.update(
            {
                "canonical_source_url": canonical_source,
                "canonical_post_url": canonical_post,
                "canonical_media_url": canonical_media,
                "filename": suggested,
                "relative_output_path": rel,
                "review_strings": review,
            }
        )
        return TwitterXMediaItem(**data)

    def to_dict(self) -> dict[str, Any]:
        item = self.with_derived_fields()
        data = asdict(item)
        data["review_strings"] = list(item.review_strings)
        return data


@dataclass(frozen=True)
class TwitterXPostMediaRecord:
    post_id: str
    account_handle: str
    display_name: str
    source_url: str
    post_url: str
    created_at_text: str = ""
    text: str = ""
    quoted_text: str = ""
    stats: Mapping[str, str] | None = None
    media_items: tuple[TwitterXMediaItem, ...] = ()
    review_strings: tuple[str, ...] = ()
    source_role_bridge_status: str = SOURCE_ROLE_BRIDGE_COMPAT
    promotion_status: str = PROMOTION_NONE
    canonical_source_url: str = ""
    canonical_post_url: str = ""

    def with_derived_fields(self) -> "TwitterXPostMediaRecord":
        canonical_source = sanitize_plain_url(self.canonical_source_url or self.source_url)
        canonical_post = sanitize_plain_url(self.canonical_post_url or self.post_url or canonical_source)
        items = tuple(item.with_derived_fields() for item in self.media_items)
        review = self.review_strings or tuple(
            _dedupe(
                [
                    canonical_source,
                    self.source_url,
                    canonical_post,
                    self.post_url,
                    self.account_handle,
                    self.display_name,
                    self.post_id,
                    self.created_at_text,
                    _snippet(self.quoted_text),
                    _snippet(self.text, 320),
                    _stats_text(self.stats or {}),
                    *(string for item in items for string in item.review_strings),
                ]
            )
        )
        data = asdict(self)
        data.update(
            {
                "canonical_source_url": canonical_source,
                "canonical_post_url": canonical_post,
                "media_items": items,
                "review_strings": review,
            }
        )
        return TwitterXPostMediaRecord(**data)

    def to_dict(self) -> dict[str, Any]:
        record = self.with_derived_fields()
        return {
            "account_handle": record.account_handle,
            "canonical_post_url": record.canonical_post_url,
            "canonical_source_url": record.canonical_source_url,
            "created_at_text": record.created_at_text,
            "display_name": record.display_name,
            "media_items": [item.to_dict() for item in record.media_items],
            "post_id": record.post_id,
            "post_url": record.post_url,
            "promotion_status": record.promotion_status,
            "quoted_text": record.quoted_text,
            "review_strings": list(record.review_strings),
            "source_role_bridge_status": record.source_role_bridge_status,
            "source_url": record.source_url,
            "stats": dict(record.stats or {}),
            "text": record.text,
        }


@dataclass(frozen=True)
class TwitterXMediaExtractionOptions:
    account_or_unknown: str = "unknown"
    capture_timestamp: str = "20260914T000000Z"
    copy_local_fixtures: bool = True
    register_route_only: bool = True
    live_capture_enabled: bool = False
    browser_or_cdp_enabled: bool = False
    network_capture_enabled: bool = False
    cookie_or_token_access_enabled: bool = False
    challenge_bypass_enabled: bool = False
    media_download_from_x_enabled: bool = False
    source_role_assignment_enabled: bool = False
    review_window_rewrite_enabled: bool = False
    counter_no_jump_mutation_enabled: bool = False
    metadata_promotion_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXMediaExtractionPackage:
    root_output_path: str
    manifest_path: str
    media_index_path: str
    media_index_ndjson_path: str
    timeline_ndjson_path: str
    timeline_markdown_path: str
    review_strings_path: str
    source_info_path: str
    post_paths: tuple[Mapping[str, str], ...]
    manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": dict(self.manifest),
            "manifest_path": self.manifest_path,
            "media_index_ndjson_path": self.media_index_ndjson_path,
            "media_index_path": self.media_index_path,
            "post_paths": [dict(item) for item in self.post_paths],
            "review_strings_path": self.review_strings_path,
            "root_output_path": self.root_output_path,
            "source_info_path": self.source_info_path,
            "timeline_markdown_path": self.timeline_markdown_path,
            "timeline_ndjson_path": self.timeline_ndjson_path,
        }


@dataclass(frozen=True)
class R42GTReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    checks: tuple[Mapping[str, str], ...]
    options: Mapping[str, Any]
    package: Mapping[str, Any]
    sample_posts: tuple[Mapping[str, Any], ...]
    capability_metadata: Mapping[str, Any]
    media_item_schema: Mapping[str, Any]
    post_record_schema: Mapping[str, Any]
    package_manifest_schema: Mapping[str, Any]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GT_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_metadata": dict(self.capability_metadata),
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "media_item_schema": dict(self.media_item_schema),
            "options": dict(self.options),
            "package": dict(self.package),
            "package_manifest_schema": dict(self.package_manifest_schema),
            "passed": self.passed,
            "post_record_schema": dict(self.post_record_schema),
            "sample_posts": [dict(item) for item in self.sample_posts],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_root": self.source_root,
            "status": self.status,
        }


def sanitize_plain_url(value: str) -> str:
    text = str(value or "").strip().strip("<>")
    markdown = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    if markdown:
        text = markdown.group(1)
    bare_markdown = re.search(r"\((https?://[^)]+)\)", text)
    if text.startswith("[") and bare_markdown:
        text = bare_markdown.group(1)
    text = text.replace("\\_", "_").replace("\\/", "/").strip()
    text = sanitize_source_url(text)
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text
    host = (parsed.hostname or parsed.netloc).lower()
    if host in {"twitter.com", "www.twitter.com"}:
        host = "x.com"
    elif host == "www.x.com":
        host = "x.com"
    kept_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_PARAMS
    ]
    return urlunsplit((parsed.scheme.lower(), host, re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/", urlencode(kept_query), ""))


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


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


def _filename_from_url(url: str, media_kind: str, media_id: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower() if url else ""
    if suffix and len(suffix) <= 8:
        return f"{_safe_segment(media_id, 'media')}{suffix}"
    default_suffix = ".mp4" if media_kind == "video" else ".jpg" if media_kind in {"image", "thumbnail"} else ".bin"
    return f"{_safe_segment(media_id, 'media')}{default_suffix}"


def _safe_segment(value: str, fallback: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "")).strip("_") or fallback


def _snippet(value: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _stats_text(stats: Mapping[str, str]) -> str:
    return " ".join(f"{key}: {value}" for key, value in sorted(stats.items()) if value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema(fields: Sequence[str]) -> Mapping[str, Any]:
    return {"schema_version": R42GT_SCHEMA_VERSION, "fields": list(fields)}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def build_capability_metadata() -> Mapping[str, Any]:
    return {
        "route_registered": True,
        "source_family": "twitter_x",
        "method_slots": (
            "extension_manual_receipt_import",
            "local_exporter_import",
            "future_visible_browser_resource_discovery",
        ),
        "live_capture_implemented_by_r42gt": False,
        "browser_or_cdp_network_capture_implemented_by_r42gt": False,
        "cookie_or_token_access_implemented_by_r42gt": False,
        "challenge_bypass_implemented_by_r42gt": False,
        "media_download_from_x_implemented_by_r42gt": False,
        "metadata_candidates_promoted_by_r42gt": False,
        "source_role_assignment_implemented_by_r42gt": False,
        "review_window_rewrite_implemented_by_r42gt": False,
    }


def build_sample_posts(local_fixture_path: str = "") -> tuple[TwitterXPostMediaRecord, ...]:
    post_url = "https://x.com/BBCr4today/status/2097217541416308845"
    account_url = "https://x.com/BBCr4today"
    remote = TwitterXMediaItem(
        media_id="media:twitter_x:BBCr4today:2097217541416308845:photo_remote",
        post_id="2097217541416308845",
        source_url=account_url,
        post_url=post_url,
        media_kind="image",
        media_role="primary_post_media",
        media_url="https://pbs.twimg.com/media/sample-r42gt.jpg?format=jpg&name=large",
        thumbnail_url="https://pbs.twimg.com/media/sample-r42gt.jpg?format=jpg&name=small",
        alt_text="Remote X media candidate kept as metadata only by R42GT.",
        filename="photo_remote.jpg",
    )
    fixture = TwitterXMediaItem(
        media_id="media:twitter_x:BBCr4today:2097217541416308845:local_fixture",
        post_id="2097217541416308845",
        source_url=account_url,
        post_url=post_url,
        media_kind="image",
        media_role="manual_receipt_file",
        media_url="",
        alt_text="Local user-supplied fixture copied only because it already exists on disk.",
        filename="local_fixture.bin",
        local_fixture_path=local_fixture_path,
        capture_method_id="local_fixture_import",
        requires_human_authorized_session=False,
        access_mode="local_fixture_only",
    )
    return (
        TwitterXPostMediaRecord(
            post_id="2097217541416308845",
            account_handle="@BBCr4today",
            display_name="BBC Radio 4 Today",
            source_url=account_url,
            post_url=post_url,
            created_at_text="7:56 AM Sep 8 2026",
            quoted_text="I think it carries a real risk of increased chances of attacks on the British Jewish community.",
            text=(
                "Dr Peter Prinsley, vice chair of Labour Friends of Israel, tells @bbcnickrobinson that he warned "
                "Foreign Secretary Ed Miliband about the risk of implementing sanctions on goods and services from "
                "West Bank settlements."
            ),
            stats={"views": "256K", "comments": "309", "retweets": "76", "likes": "92", "bookmarks": "40"},
            media_items=(remote, fixture) if local_fixture_path else (remote,),
        ).with_derived_fields(),
    )


def write_twitter_x_media_evidence_package(
    post_records: Sequence[TwitterXPostMediaRecord],
    output_root: str | Path,
    options: TwitterXMediaExtractionOptions | None = None,
) -> TwitterXMediaExtractionPackage:
    options = options or TwitterXMediaExtractionOptions()
    capture_timestamp = _safe_segment(options.capture_timestamp, "20260914T000000Z")
    account = _safe_segment(options.account_or_unknown, "unknown")
    root = Path(output_root) / "source_exports" / "twitter_x" / account / f"capture_{capture_timestamp}"
    posts_root = root / "posts"
    media_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    post_paths: list[Mapping[str, str]] = []
    review_strings: list[str] = []
    local_count = 0
    remote_count = 0

    for source_record in post_records:
        record = source_record.with_derived_fields()
        post_dir = posts_root / _safe_segment(record.post_id, "post")
        media_dir = post_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        materialized_items: list[dict[str, Any]] = []
        for source_item in record.media_items:
            item = source_item.with_derived_fields()
            item_data = item.to_dict()
            fixture_path = Path(item.local_fixture_path) if item.local_fixture_path else None
            if options.copy_local_fixtures and fixture_path and fixture_path.is_file():
                target = media_dir / item.filename
                shutil.copy2(fixture_path, target)
                sha256 = _sha256_file(target)
                item_data.update(
                    {
                        "media_file_status": LOCAL_FIXTURE_COPIED,
                        "relative_output_path": _plain_path(target.relative_to(root).as_posix()),
                        "sha256": sha256,
                    }
                )
                local_count += 1
            else:
                item_data.update({"media_file_status": REMOTE_NOT_DOWNLOADED, "sha256": ""})
                remote_count += 1
            media_rows.append(item_data)
            materialized_items.append(item_data)
            review_strings.extend(str(value) for value in item_data.get("review_strings", []) if value)

        post_data = record.to_dict()
        post_data["media_items"] = materialized_items
        review_strings.extend(str(value) for value in post_data.get("review_strings", []) if value)
        _write_json(post_dir / "post.json", post_data)
        _write_text(post_dir / "post.md", render_post_markdown(record, materialized_items))
        timeline_rows.append(
            {
                "account_handle": record.account_handle,
                "canonical_post_url": record.canonical_post_url,
                "post_id": record.post_id,
                "created_at_text": record.created_at_text,
                "text": record.text,
                "media_candidate_count": len(materialized_items),
                "promotion_status": PROMOTION_NONE,
            }
        )
        post_paths.append(
            {
                "post_id": record.post_id,
                "post_json": _plain_path((post_dir / "post.json").relative_to(root).as_posix()),
                "post_markdown": _plain_path((post_dir / "post.md").relative_to(root).as_posix()),
                "media_dir": _plain_path(media_dir.relative_to(root).as_posix()) + "/",
            }
        )

    manifest = {
        "account_or_unknown": options.account_or_unknown,
        "capability_metadata": dict(build_capability_metadata()),
        "capture_timestamp": capture_timestamp,
        "local_fixture_media_count": local_count,
        "manifest_path": "manifest.json",
        "marker": R42GT_MARKER,
        "media_candidate_count": len(media_rows),
        "media_index_path": "media_index.json",
        "post_count": len(post_records),
        "promotion_status": PROMOTION_NONE,
        "review_strings_path": "review_strings.txt",
        "root_output_path": _plain_path(root.as_posix()),
        "schema_version": R42GT_SCHEMA_VERSION,
        "source_family": "twitter_x",
        "source_role_bridge_status": SOURCE_ROLE_BRIDGE_COMPAT,
        "status": R42GT_PASS_STATUS,
        "remote_metadata_only_count": remote_count,
    }
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "media_index.json", {"media": media_rows, "promotion_status": PROMOTION_NONE})
    _write_ndjson(root / "media_index.ndjson", media_rows)
    _write_ndjson(root / "timeline.ndjson", timeline_rows)
    _write_text(root / "timeline.md", render_timeline_markdown(post_records))
    _write_text(root / "review_strings.txt", "\n".join(_dedupe(review_strings)) + "\n")
    _write_text(root / "source_info.txt", render_source_info(manifest))

    return TwitterXMediaExtractionPackage(
        root_output_path=_plain_path(root.as_posix()),
        manifest_path=_plain_path((root / "manifest.json").as_posix()),
        media_index_path=_plain_path((root / "media_index.json").as_posix()),
        media_index_ndjson_path=_plain_path((root / "media_index.ndjson").as_posix()),
        timeline_ndjson_path=_plain_path((root / "timeline.ndjson").as_posix()),
        timeline_markdown_path=_plain_path((root / "timeline.md").as_posix()),
        review_strings_path=_plain_path((root / "review_strings.txt").as_posix()),
        source_info_path=_plain_path((root / "source_info.txt").as_posix()),
        post_paths=tuple(post_paths),
        manifest=manifest,
    )


def render_post_markdown(record: TwitterXPostMediaRecord, media_items: Sequence[Mapping[str, Any]]) -> str:
    record = record.with_derived_fields()
    lines = [
        f"# {record.display_name} ({record.account_handle})",
        "",
        f"Source URL: {record.canonical_post_url}",
        f"Created: {record.created_at_text}",
        "",
    ]
    if record.quoted_text:
        lines.extend([f"> {record.quoted_text}", ""])
    if record.text:
        lines.extend([record.text, ""])
    if record.stats:
        lines.extend([_stats_text(record.stats), ""])
    lines.extend(["## Media Candidates", ""])
    for item in media_items:
        lines.append(f"- {item.get('media_id')}: {item.get('media_kind')} / {item.get('media_role')} / {item.get('media_file_status')}")
    return "\n".join(lines) + "\n"


def render_timeline_markdown(post_records: Sequence[TwitterXPostMediaRecord]) -> str:
    lines = ["# Twitter/X Timeline Media Evidence Package", ""]
    for record in post_records:
        item = record.with_derived_fields()
        lines.extend([f"## {item.display_name} {item.account_handle}", item.canonical_post_url, item.text, ""])
    return "\n".join(lines)


def render_source_info(manifest: Mapping[str, Any]) -> str:
    capability = manifest.get("capability_metadata", {})
    lines = [
        R42GT_MARKER,
        f"status: {manifest.get('status')}",
        "registered route only: true",
        f"live capture implemented by R42GT: {capability.get('live_capture_implemented_by_r42gt')}",
        f"browser/CDP capture implemented by R42GT: {capability.get('browser_or_cdp_network_capture_implemented_by_r42gt')}",
        f"media download from X implemented by R42GT: {capability.get('media_download_from_x_implemented_by_r42gt')}",
        f"source-role bridge: {manifest.get('source_role_bridge_status')}",
        f"promotion status: {manifest.get('promotion_status')}",
    ]
    return "\n".join(lines) + "\n"


def _plain_path(value: str) -> str:
    return str(value or "").replace("\\", "/")


def is_plain_machine_value(value: str) -> bool:
    text = str(value or "").strip()
    return not text.startswith("[") and "](" not in text and "]\\(" not in text


def machine_url_fields_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(machine_url_fields_are_plain(child, str(child_key)) for child_key, child in value.items())
    if isinstance(value, (list, tuple)):
        return all(machine_url_fields_are_plain(child, key) for child in value)
    if key in MACHINE_URL_FIELDS:
        return is_plain_machine_value(str(value or ""))
    return True


def url_like_review_strings_are_plain(values: Sequence[str]) -> bool:
    for value in values:
        text = str(value or "").strip()
        if text.startswith("http") and not is_plain_machine_value(text):
            return False
        if text.startswith("[") and "](" in text:
            return False
    return True


def build_report(source_root: str | Path = ".", output_root: str | Path | None = None) -> R42GTReport:
    root = Path(output_root or "profile_media_live_captures/r42gt_twitter_x_media_extraction")
    fixture = root / "fixtures" / "local_fixture_media.bin"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    if not fixture.exists():
        fixture.write_bytes(b"R42GT local fixture media bytes\n")
    options = TwitterXMediaExtractionOptions(account_or_unknown="BBCr4today", capture_timestamp="20260914T000000Z")
    posts = build_sample_posts(str(fixture))
    package = write_twitter_x_media_evidence_package(posts, root, options)
    package_payload = package.to_dict()
    manifest = json.loads(Path(package.manifest_path).read_text(encoding="utf-8"))
    media_index = json.loads(Path(package.media_index_path).read_text(encoding="utf-8"))
    written_posts = [json.loads((Path(package.root_output_path) / row["post_json"]).read_text(encoding="utf-8")) for row in package.post_paths]
    review_strings = Path(package.review_strings_path).read_text(encoding="utf-8").splitlines()
    gi_report = validate_universal_media_method_matrix(source_root)
    gs_report = generate_r42gs_report(source_root, root / "r42gs_guardrail")
    capability = build_capability_metadata()
    checks = (
        _check("canonical_model_schema_present", set(MEDIA_ITEM_SCHEMA_FIELDS).issubset(set(TwitterXMediaItem.__dataclass_fields__)) and set(POST_RECORD_SCHEMA_FIELDS).issubset(set(TwitterXPostMediaRecord.__dataclass_fields__))),
        _check("offline_package_layout_written", all(Path(package_payload[key]).exists() for key in ("manifest_path", "media_index_path", "media_index_ndjson_path", "timeline_ndjson_path", "timeline_markdown_path", "review_strings_path", "source_info_path"))),
        _check("post_package_files_written", all((Path(package.root_output_path) / row["post_json"]).exists() and (Path(package.root_output_path) / row["post_markdown"]).exists() for row in package.post_paths)),
        _check("remote_candidates_metadata_only", any(row.get("media_file_status") == REMOTE_NOT_DOWNLOADED and row.get("promotion_status") == PROMOTION_NONE for row in media_index.get("media", []))),
        _check("local_fixture_copied_and_hashed", any(row.get("media_file_status") == LOCAL_FIXTURE_COPIED and row.get("sha256") for row in media_index.get("media", []))),
        _check("plain_machine_url_fields", machine_url_fields_are_plain(manifest) and machine_url_fields_are_plain(media_index) and all(machine_url_fields_are_plain(post.to_dict()) for post in posts)),
        _check("plain_url_review_strings", url_like_review_strings_are_plain(review_strings)),
        _check("route_registered_no_side_effects", bool(capability["route_registered"]) and not any(bool(capability[key]) for key in capability if key.endswith("_implemented_by_r42gt") or key == "metadata_candidates_promoted_by_r42gt")),
        _check("no_metadata_promotion", manifest.get("promotion_status") == PROMOTION_NONE and all(row.get("promotion_status") == PROMOTION_NONE for row in media_index.get("media", []))),
        _check("prior_youtube_sort_spam_green", gs_report.get("status") == R42GS_PASS_STATUS),
        _check("prior_media_method_matrix_green", gi_report.status == R42GI_PASS_STATUS),
    )
    status = R42GT_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GT_BLOCKED_STATUS
    return R42GTReport(
        marker=R42GT_MARKER,
        schema_version=R42GT_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(source_root),
        status=status,
        checks=checks,
        options=options.to_dict(),
        package=package_payload,
        sample_posts=tuple(written_posts),
        capability_metadata=capability,
        media_item_schema=_schema(MEDIA_ITEM_SCHEMA_FIELDS),
        post_record_schema=_schema(POST_RECORD_SCHEMA_FIELDS),
        package_manifest_schema=_schema(PACKAGE_MANIFEST_FIELDS),
    )


def write_report(report: R42GTReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA_REPORT.json", report.to_dict())
    _write_text(root / "R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA_REPORT.md", render_report_markdown(report))


def render_report_markdown(report: R42GTReport) -> str:
    lines = [
        f"# {R42GT_MARKER}",
        "",
        f"Status: {report.status}",
        f"Generated: {report.generated_at}",
        "",
        "## Boundaries",
        "",
        "- Live X/Twitter capture: not implemented by R42GT.",
        "- Browser/CDP/network capture: not implemented by R42GT.",
        "- Cookie/token access and challenge bypass: not implemented by R42GT.",
        "- Remote X media download: not implemented by R42GT.",
        "- Source-role assignment/review-window/counter/no-jump changes: not implemented by R42GT.",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    lines.extend(["", "## Package", "", f"- Root: {report.package.get('root_output_path')}", f"- Manifest: {report.package.get('manifest_path')}"])
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GT_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gt_twitter_x_media_extraction")
    args = parser.parse_args(argv)
    report = build_report(args.source_root, args.output_root)
    write_report(report, args.output_root)
    print(R42GT_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "LOCAL_FIXTURE_COPIED",
    "PROMOTION_NONE",
    "R42GT_BLOCKED_STATUS",
    "R42GT_MARKER",
    "R42GT_PASS_STATUS",
    "REMOTE_NOT_DOWNLOADED",
    "REVIEW_METADATA_ONLY",
    "TwitterXMediaExtractionOptions",
    "TwitterXMediaExtractionPackage",
    "TwitterXMediaItem",
    "TwitterXPostMediaRecord",
    "build_capability_metadata",
    "build_report",
    "build_sample_posts",
    "machine_url_fields_are_plain",
    "sanitize_plain_url",
    "url_like_review_strings_are_plain",
    "write_report",
    "write_twitter_x_media_evidence_package",
]


if __name__ == "__main__":
    raise SystemExit(main())
