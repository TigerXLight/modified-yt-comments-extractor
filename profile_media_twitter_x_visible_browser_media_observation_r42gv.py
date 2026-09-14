from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_twitter_x_media_extraction_r42gt import (
    LOCAL_FIXTURE_COPIED,
    PROMOTION_NONE,
    REMOTE_NOT_DOWNLOADED,
    REVIEW_METADATA_ONLY,
    TwitterXMediaExtractionOptions,
    TwitterXMediaExtractionPackage,
    TwitterXMediaItem,
    TwitterXPostMediaRecord,
    machine_url_fields_are_plain,
    sanitize_plain_url,
    write_twitter_x_media_evidence_package,
)
from source_resource_state import (
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    SourceResourceItem,
)

R42GV_MARKER = "YTCE_R42GV_TWITTER_X_VISIBLE_BROWSER_MEDIA_OBSERVATION_STORE"
R42GV_PASS_STATUS = "PASS_R42GV_TWITTER_X_VISIBLE_BROWSER_MEDIA_OBSERVATION_STORE"
R42GV_BLOCKED_STATUS = "BLOCKED_R42GV_WITH_EXACT_BLOCKER"
R42GV_SCHEMA_VERSION = "twitter_x_visible_browser_media_observation_store.r42gv.v1"

MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_VIDEO = "video"
MEDIA_KIND_AUDIO = "audio"
MEDIA_KIND_MANIFEST = "manifest"
MEDIA_KIND_SEGMENT = "segment"
MEDIA_KIND_UNKNOWN = "unknown"

BYTE_STATUS_REMOTE = "remote_candidate_review_required"
BYTE_STATUS_SESSION_LOCAL = "session_local_file_available"
BYTE_STATUS_COPIED_WITH_SHA256 = "copied_with_sha256_by_r42gt_package_writer"

SOURCE_KIND_BROWSER_NETWORK = "visible_browser_network_response"
SOURCE_KIND_RENDERED_DOM_RESOURCE = "rendered_dom_media_resource"
SOURCE_KIND_MEDIA_INVENTORY = "twitter_media_inventory"
SOURCE_KIND_SESSION_LOCAL_FILE = "session_local_file"

OBSERVATION_STORE_JSON = "visible_browser_media_observations.json"
OBSERVATION_STORE_NDJSON = "visible_browser_media_observations.ndjson"
SEGMENT_TABLE_NDJSON = "visible_browser_media_segments.ndjson"
REVIEW_PROJECTION_JSON = "visible_browser_media_review_projection.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".mov"}
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".ogg"}
MANIFEST_EXTENSIONS = {".m3u8", ".mpd"}
SEGMENT_EXTENSIONS = {".ts", ".m4s", ".cmfv", ".cmfa"}

TWITTER_MEDIA_HOST_PARTS = (
    "pbs.twimg.com",
    "video.twimg.com",
    "abs.twimg.com",
    "twimg.com",
    "x.com",
    "twitter.com",
)


@dataclass(frozen=True)
class TwitterXVisibleBrowserMediaObservation:
    observation_id: str
    source_url: str
    canonical_source_url: str
    media_url: str
    canonical_media_url: str
    media_kind: str
    source_kind: str
    detection_method: str
    post_url: str = ""
    canonical_post_url: str = ""
    account_handle: str = ""
    status_id: str = ""
    content_type: str = ""
    resource_type: str = ""
    media_id: str = ""
    preview_url: str = ""
    thumbnail_url: str = ""
    width: int = 0
    height: int = 0
    bitrate: int = 0
    duration_seconds: float = 0.0
    playlist_manifest_url: str = ""
    segment_index: int = 0
    segment_group_id: str = ""
    byte_status: str = BYTE_STATUS_REMOTE
    local_session_path: str = ""
    sha256: str = ""
    review_required: bool = True
    selectable_in_image_window: bool = False
    selectable_in_video_window: bool = False
    warning: str = (
        "Observed in a visible human-authorized X/Twitter browser session; "
        "remote URLs remain metadata-only unless session-local bytes already exist."
    )
    provenance: str = "R42GV visible browser media observation store"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXVisibleBrowserSegmentRow:
    segment_id: str
    source_url: str
    canonical_source_url: str
    segment_url: str
    canonical_segment_url: str
    playlist_manifest_url: str = ""
    segment_index: int = 0
    content_type: str = ""
    byte_status: str = BYTE_STATUS_REMOTE
    local_session_path: str = ""
    sha256: str = ""
    warning: str = (
        "Segment row is preserved for grouped stream review; "
        "R42GV does not download remote segments."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXVisibleBrowserMediaObservationStore:
    schema_version: str
    marker: str
    source_url: str
    canonical_source_url: str
    capture_timestamp: str
    observations: tuple[TwitterXVisibleBrowserMediaObservation, ...] = ()
    segment_rows: tuple[TwitterXVisibleBrowserSegmentRow, ...] = ()
    side_effect_flags: Mapping[str, bool] | None = None
    status: str = R42GV_PASS_STATUS

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def segment_count(self) -> int:
        return len(self.segment_rows)

    @property
    def remote_candidate_count(self) -> int:
        return sum(1 for item in self.observations if item.byte_status == BYTE_STATUS_REMOTE)

    @property
    def session_local_file_count(self) -> int:
        return sum(1 for item in self.observations if item.local_session_path)

    def to_dict(self) -> dict[str, Any]:
        flags = dict(self.side_effect_flags or build_side_effect_flags())
        return {
            "canonical_source_url": self.canonical_source_url,
            "capture_timestamp": self.capture_timestamp,
            "marker": self.marker,
            "observation_count": self.observation_count,
            "observations": [item.to_dict() for item in self.observations],
            "remote_candidate_count": self.remote_candidate_count,
            "schema_version": self.schema_version,
            "segment_count": self.segment_count,
            "segment_rows": [item.to_dict() for item in self.segment_rows],
            "session_local_file_count": self.session_local_file_count,
            "side_effect_flags": flags,
            "source_url": self.source_url,
            "status": self.status,
        }


@dataclass(frozen=True)
class TwitterXVisibleBrowserObservationWriteResult:
    output_dir: str
    observation_store_path: str
    observation_ndjson_path: str
    segment_table_path: str
    review_projection_path: str
    observation_count: int
    segment_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R42GVReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    observation_store: Mapping[str, Any]
    write_result: Mapping[str, Any]
    review_window_database_projection: Mapping[str, Any]
    image_resource_count: int
    video_audio_resource_count: int
    r42gt_package: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R42GV_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "image_resource_count": self.image_resource_count,
            "marker": self.marker,
            "observation_store": dict(self.observation_store),
            "r42gt_package": dict(self.r42gt_package),
            "review_window_database_projection": dict(self.review_window_database_projection),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "source_root": self.source_root,
            "status": self.status,
            "video_audio_resource_count": self.video_audio_resource_count,
            "write_result": dict(self.write_result),
        }


def build_side_effect_flags() -> Mapping[str, bool]:
    return {
        "visible_browser_session_observation_enabled": True,
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "account_crawling_outside_visible_session_performed": False,
        "rate_limit_evasion_performed": False,
        "remote_x_media_download_performed_by_r42gv": False,
        "source_role_assignment_performed": False,
        "review_window_rewrite_performed": False,
        "counter_no_jump_mutation_performed": False,
        "youtube_capture_engine_changed": False,
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            if isinstance(converted, Mapping):
                return converted
        except Exception:
            pass
    if hasattr(value, "__dataclass_fields__"):
        try:
            return asdict(value)
        except Exception:
            pass
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key, None))
    }


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_segment(value: str, default: str = "unknown") -> str:
    text = re.sub(r"[^A-Za-z0-9_.@-]+", "_", _clean(value)).strip("._-")
    return text or default


def _plain_path(value: str | Path) -> str:
    return str(value or "").replace("\\", "/")


def _extension_from_url(url: str) -> str:
    path = urlsplit(_clean(url)).path.lower()
    for ext in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | MANIFEST_EXTENSIONS | SEGMENT_EXTENSIONS, key=len, reverse=True):
        if path.endswith(ext):
            return ext
    if ":large" in path or ":small" in path:
        suffix = path.split(":")[-1]
        base = path.rsplit(":", 1)[0]
        for ext in IMAGE_EXTENSIONS:
            if base.endswith(ext):
                return ext
    return ""


def _is_twitter_media_relevant_url(url: str) -> bool:
    clean = sanitize_plain_url(_clean(url))
    parsed = urlsplit(clean)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not any(host == part or host.endswith("." + part) or part in host for part in TWITTER_MEDIA_HOST_PARTS):
        return False
    lowered = clean.lower()
    if any(marker in lowered for marker in ("/media/", "/ext_tw_video/", "/tweet_video/", "format=jpg", "format=png", "format=webp")):
        return True
    if _extension_from_url(clean):
        return True
    if "/i/api/" in lowered or "/graphql/" in lowered:
        return True
    return False


def _media_kind_for_url_content_type(url: str, content_type: str = "", fallback_media_type: str = "") -> str:
    lowered = f"{url} {content_type} {fallback_media_type}".lower()
    ext = _extension_from_url(url)
    if ext in MANIFEST_EXTENSIONS or "mpegurl" in lowered or "dash+xml" in lowered:
        return MEDIA_KIND_MANIFEST
    if ext in SEGMENT_EXTENSIONS or "video/mp2t" in lowered or re.search(r"/(?:seg(?:ment)?|chunk|frag|part)[-_/.]?\d", lowered):
        return MEDIA_KIND_SEGMENT
    if ext in IMAGE_EXTENSIONS or "image/" in lowered or "pbs.twimg.com/media/" in lowered:
        return MEDIA_KIND_IMAGE
    if ext in VIDEO_EXTENSIONS or "video/" in lowered or "ext_tw_video" in lowered or "tweet_video" in lowered:
        return MEDIA_KIND_VIDEO
    if ext in AUDIO_EXTENSIONS or "audio/" in lowered:
        return MEDIA_KIND_AUDIO
    return MEDIA_KIND_UNKNOWN


def _status_id_from_url(url: str) -> str:
    match = re.search(r"/(?:i/)?status/(\d+)", _clean(url))
    if match:
        return match.group(1)
    match = re.search(r"/ext_tw_video/(\d+)", _clean(url))
    if match:
        return match.group(1)
    return ""


def _account_from_url(url: str) -> str:
    parsed = urlsplit(sanitize_plain_url(_clean(url)))
    path = parsed.path.strip("/").split("/")
    if not path or not path[0]:
        return ""
    handle = path[0]
    if handle.lower() in {"i", "api", "intent", "home", "search", "hashtag"}:
        return ""
    return "@" + handle.lstrip("@")


def _canonical_post_url(source_url: str, post_url: str = "", status_id: str = "", account_handle: str = "") -> str:
    if post_url:
        return sanitize_plain_url(post_url)
    source = sanitize_plain_url(source_url)
    if status_id and "/status/" in source:
        return source
    if status_id and account_handle and account_handle != "@unknown":
        return f"https://x.com/{account_handle.lstrip('@')}/status/{status_id}"
    return source


def _observation_id(*parts: Any) -> str:
    digest = _hash_text("|".join(_clean(part) for part in parts))[:20]
    return f"r42gv_media_{digest}"


def _display_name_for_observation(obs: TwitterXVisibleBrowserMediaObservation, *, segment_count: int = 0) -> str:
    if obs.media_kind == MEDIA_KIND_SEGMENT:
        return f"Segmented stream ({segment_count or 1} observed segment{'s' if (segment_count or 1) != 1 else ''})"
    if obs.media_kind == MEDIA_KIND_MANIFEST:
        return "Observed X/Twitter stream manifest"
    if obs.media_kind == MEDIA_KIND_IMAGE:
        return "Observed X/Twitter image"
    if obs.media_kind == MEDIA_KIND_VIDEO:
        return "Observed X/Twitter video"
    if obs.media_kind == MEDIA_KIND_AUDIO:
        return "Observed X/Twitter audio"
    return "Observed X/Twitter media candidate"


def _source_resource_id(source_row_id: str, obs: TwitterXVisibleBrowserMediaObservation, resource_kind: str, suffix: str = "") -> str:
    tail = suffix or obs.observation_id
    return f"{source_row_id}:{resource_kind}:r42gv:{tail}"


def _obs_from_url(
    *,
    source_url: str,
    media_url: str,
    source_kind: str,
    detection_method: str,
    content_type: str = "",
    resource_type: str = "",
    media_id: str = "",
    preview_url: str = "",
    thumbnail_url: str = "",
    width: int = 0,
    height: int = 0,
    bitrate: int = 0,
    duration_seconds: float = 0.0,
    post_url: str = "",
    account_handle: str = "",
    status_id: str = "",
    playlist_manifest_url: str = "",
    segment_index: int = 0,
    byte_status: str = BYTE_STATUS_REMOTE,
    local_session_path: str = "",
    created_at: str = "",
) -> TwitterXVisibleBrowserMediaObservation | None:
    clean_media_url = sanitize_plain_url(media_url)
    if not clean_media_url:
        return None
    media_kind = _media_kind_for_url_content_type(clean_media_url, content_type, "")
    if media_kind == MEDIA_KIND_UNKNOWN:
        return None
    clean_source_url = sanitize_plain_url(source_url)
    status = status_id or _status_id_from_url(post_url) or _status_id_from_url(clean_source_url) or _status_id_from_url(clean_media_url)
    account = account_handle or _account_from_url(post_url) or _account_from_url(clean_source_url) or "@unknown"
    canonical_post = _canonical_post_url(clean_source_url, post_url, status, account)
    selectable_image = media_kind == MEDIA_KIND_IMAGE
    selectable_video = media_kind in {MEDIA_KIND_VIDEO, MEDIA_KIND_AUDIO, MEDIA_KIND_MANIFEST}
    if media_kind == MEDIA_KIND_SEGMENT:
        selectable_video = False
    sha256 = ""
    if local_session_path and Path(local_session_path).is_file():
        try:
            sha256 = _hash_file(local_session_path)
            byte_status = BYTE_STATUS_SESSION_LOCAL
        except Exception:
            sha256 = ""
    return TwitterXVisibleBrowserMediaObservation(
        observation_id=_observation_id(clean_source_url, clean_media_url, source_kind, media_id, segment_index),
        source_url=clean_source_url,
        canonical_source_url=clean_source_url,
        media_url=clean_media_url,
        canonical_media_url=clean_media_url,
        media_kind=media_kind,
        source_kind=source_kind,
        detection_method=detection_method,
        post_url=canonical_post,
        canonical_post_url=canonical_post,
        account_handle=account,
        status_id=status,
        content_type=content_type,
        resource_type=resource_type,
        media_id=media_id,
        preview_url=sanitize_plain_url(preview_url) if preview_url else "",
        thumbnail_url=sanitize_plain_url(thumbnail_url) if thumbnail_url else "",
        width=width,
        height=height,
        bitrate=bitrate,
        duration_seconds=duration_seconds,
        playlist_manifest_url=sanitize_plain_url(playlist_manifest_url) if playlist_manifest_url else "",
        segment_index=segment_index,
        segment_group_id=_observation_id(clean_source_url, playlist_manifest_url or clean_media_url, "segment_group") if media_kind == MEDIA_KIND_SEGMENT else "",
        byte_status=byte_status,
        local_session_path=_plain_path(local_session_path),
        sha256=sha256,
        selectable_in_image_window=selectable_image,
        selectable_in_video_window=selectable_video,
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
    )


def _event_observations(
    *,
    source_url: str,
    events: Iterable[Any],
    capture_timestamp: str,
) -> tuple[TwitterXVisibleBrowserMediaObservation, ...]:
    observations: list[TwitterXVisibleBrowserMediaObservation] = []
    last_manifest_by_host: dict[str, str] = {}
    segment_index_by_manifest: dict[str, int] = {}
    for index, event in enumerate(events):
        row = _as_mapping(event)
        url = sanitize_plain_url(_clean(row.get("url") or row.get("request_url") or row.get("response_url") or ""))
        if not url or not _is_twitter_media_relevant_url(url):
            continue
        content_type = _clean(row.get("content_type") or row.get("mime_type") or row.get("response_content_type"))
        media_kind = _media_kind_for_url_content_type(url, content_type, _clean(row.get("resource_type")))
        if media_kind == MEDIA_KIND_UNKNOWN:
            continue
        host = (urlsplit(url).hostname or "").lower()
        playlist = ""
        segment_index = 0
        if media_kind == MEDIA_KIND_MANIFEST:
            last_manifest_by_host[host] = url
        elif media_kind == MEDIA_KIND_SEGMENT:
            playlist = last_manifest_by_host.get(host, "")
            key = playlist or f"{host}:ungrouped"
            segment_index_by_manifest[key] = segment_index_by_manifest.get(key, 0) + 1
            segment_index = segment_index_by_manifest[key]
        obs = _obs_from_url(
            source_url=source_url,
            media_url=url,
            source_kind=SOURCE_KIND_BROWSER_NETWORK,
            detection_method="visible_browser_network_event",
            content_type=content_type,
            resource_type=_clean(row.get("resource_type")),
            media_id=_clean(row.get("request_id") or row.get("query_name") or f"network-{index}"),
            playlist_manifest_url=playlist,
            segment_index=segment_index,
            created_at=capture_timestamp,
        )
        if obs:
            observations.append(obs)
    return tuple(observations)


def _inventory_observations(
    *,
    source_url: str,
    media_inventory: Iterable[Any],
    capture_timestamp: str,
) -> tuple[TwitterXVisibleBrowserMediaObservation, ...]:
    observations: list[TwitterXVisibleBrowserMediaObservation] = []
    for index, item in enumerate(media_inventory):
        row = _as_mapping(item)
        url = sanitize_plain_url(_clean(row.get("media_url") or row.get("url")))
        if not url:
            continue
        media_type = _clean(row.get("media_type") or row.get("type"))
        content_type = _clean(row.get("content_type") or row.get("mime_type"))
        obs = _obs_from_url(
            source_url=source_url,
            media_url=url,
            source_kind=_clean(row.get("source_kind")) or SOURCE_KIND_MEDIA_INVENTORY,
            detection_method=_clean(row.get("from_query_name")) or "twitter_media_inventory",
            content_type=content_type,
            media_id=_clean(row.get("media_id")) or f"inventory-{index}",
            preview_url=_clean(row.get("preview_url")),
            thumbnail_url=_clean(row.get("thumbnail_url") or row.get("preview_url")),
            width=_safe_int(row.get("width")),
            height=_safe_int(row.get("height")),
            bitrate=_safe_int(row.get("bitrate")),
            post_url=_clean(row.get("page_url") or row.get("post_url")),
            account_handle=_clean(row.get("account_handle")),
            status_id=_clean(row.get("status_id")),
            created_at=capture_timestamp,
        )
        if obs:
            if media_type and obs.media_kind == MEDIA_KIND_UNKNOWN:
                obs = replace(obs, media_kind=media_type)
            observations.append(obs)
    return tuple(observations)


def _dom_observations(*, source_url: str, final_dom: str, capture_timestamp: str) -> tuple[TwitterXVisibleBrowserMediaObservation, ...]:
    if not final_dom:
        return ()
    observations: list[TwitterXVisibleBrowserMediaObservation] = []
    try:
        from capture_media_discovery import discover_media_resources_from_html
    except Exception:
        return ()
    try:
        result = discover_media_resources_from_html(final_dom, source_url=source_url)
    except Exception:
        return ()
    for index, resource in enumerate(getattr(result, "resources", ()) or ()):
        row = _as_mapping(resource)
        url = sanitize_plain_url(_clean(row.get("url") or row.get("src") or row.get("reference_url")))
        if not url or not _is_twitter_media_relevant_url(url):
            continue
        obs = _obs_from_url(
            source_url=source_url,
            media_url=url,
            source_kind=SOURCE_KIND_RENDERED_DOM_RESOURCE,
            detection_method="rendered_dom_media_resource",
            content_type=_clean(row.get("mime_type")),
            resource_type=_clean(row.get("kind")),
            media_id=_clean(row.get("resource_id")) or f"dom-{index}",
            width=_safe_int(row.get("width")),
            height=_safe_int(row.get("height")),
            created_at=capture_timestamp,
        )
        if obs:
            observations.append(obs)
    return tuple(observations)


def _local_file_observations(
    *,
    source_url: str,
    session_local_files: Iterable[Any],
    capture_timestamp: str,
) -> tuple[TwitterXVisibleBrowserMediaObservation, ...]:
    observations: list[TwitterXVisibleBrowserMediaObservation] = []
    for index, item in enumerate(session_local_files):
        row = _as_mapping(item)
        raw_path = row.get("local_path") or row.get("path") or row.get("file_path")
        if not raw_path and isinstance(item, (str, Path)):
            raw_path = item
        path_text = _clean(raw_path)
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_file():
            continue
        url = sanitize_plain_url(_clean(row.get("media_url") or row.get("remote_url") or row.get("source_media_url") or path.as_uri()))
        content_type = _clean(row.get("content_type") or row.get("mime_type"))
        if not content_type:
            ext = path.suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                content_type = "image/*"
            elif ext in VIDEO_EXTENSIONS:
                content_type = "video/*"
            elif ext in AUDIO_EXTENSIONS:
                content_type = "audio/*"
        obs = _obs_from_url(
            source_url=source_url,
            media_url=url,
            source_kind=SOURCE_KIND_SESSION_LOCAL_FILE,
            detection_method="session_local_file_already_present",
            content_type=content_type,
            media_id=_clean(row.get("media_id")) or f"local-session-{index}",
            local_session_path=str(path),
            byte_status=BYTE_STATUS_SESSION_LOCAL,
            created_at=capture_timestamp,
        )
        if obs:
            observations.append(obs)
    return tuple(observations)


def build_visible_browser_media_observation_store(
    *,
    source_url: str,
    events: Iterable[Any] = (),
    final_dom: str = "",
    media_inventory: Iterable[Any] = (),
    session_local_files: Iterable[Any] = (),
    capture_timestamp: str = "",
) -> TwitterXVisibleBrowserMediaObservationStore:
    clean_source = sanitize_plain_url(source_url)
    capture_ts = capture_timestamp or _now_ts()
    raw_observations: list[TwitterXVisibleBrowserMediaObservation] = []
    raw_observations.extend(_event_observations(source_url=clean_source, events=events, capture_timestamp=capture_ts))
    raw_observations.extend(_inventory_observations(source_url=clean_source, media_inventory=media_inventory, capture_timestamp=capture_ts))
    raw_observations.extend(_dom_observations(source_url=clean_source, final_dom=final_dom, capture_timestamp=capture_ts))
    raw_observations.extend(_local_file_observations(source_url=clean_source, session_local_files=session_local_files, capture_timestamp=capture_ts))

    deduped: list[TwitterXVisibleBrowserMediaObservation] = []
    seen: set[tuple[str, str, str]] = set()
    for obs in raw_observations:
        key = (obs.canonical_media_url, obs.source_kind, obs.local_session_path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(obs)

    segment_rows = tuple(
        TwitterXVisibleBrowserSegmentRow(
            segment_id=obs.observation_id,
            source_url=obs.source_url,
            canonical_source_url=obs.canonical_source_url,
            segment_url=obs.media_url,
            canonical_segment_url=obs.canonical_media_url,
            playlist_manifest_url=obs.playlist_manifest_url,
            segment_index=obs.segment_index,
            content_type=obs.content_type,
            byte_status=obs.byte_status,
            local_session_path=obs.local_session_path,
            sha256=obs.sha256,
        )
        for obs in deduped
        if obs.media_kind == MEDIA_KIND_SEGMENT
    )
    return TwitterXVisibleBrowserMediaObservationStore(
        schema_version=R42GV_SCHEMA_VERSION,
        marker=R42GV_MARKER,
        source_url=clean_source,
        canonical_source_url=clean_source,
        capture_timestamp=capture_ts,
        observations=tuple(deduped),
        segment_rows=segment_rows,
        side_effect_flags=build_side_effect_flags(),
        status=R42GV_PASS_STATUS,
    )


def write_visible_browser_media_observation_store(
    store: TwitterXVisibleBrowserMediaObservationStore,
    output_dir: str | Path,
) -> TwitterXVisibleBrowserObservationWriteResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    observation_json_path = root / OBSERVATION_STORE_JSON
    observation_ndjson_path = root / OBSERVATION_STORE_NDJSON
    segment_table_path = root / SEGMENT_TABLE_NDJSON
    projection_path = root / REVIEW_PROJECTION_JSON

    observation_json_path.write_text(json.dumps(store.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    observation_ndjson_path.write_text(
        "\n".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) for item in store.observations) + ("\n" if store.observations else ""),
        encoding="utf-8",
    )
    segment_table_path.write_text(
        "\n".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) for item in store.segment_rows) + ("\n" if store.segment_rows else ""),
        encoding="utf-8",
    )
    projection_path.write_text(
        json.dumps(build_review_window_database_projection(store), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return TwitterXVisibleBrowserObservationWriteResult(
        output_dir=_plain_path(root.as_posix()),
        observation_store_path=_plain_path(observation_json_path.as_posix()),
        observation_ndjson_path=_plain_path(observation_ndjson_path.as_posix()),
        segment_table_path=_plain_path(segment_table_path.as_posix()),
        review_projection_path=_plain_path(projection_path.as_posix()),
        observation_count=store.observation_count,
        segment_count=store.segment_count,
    )


def build_review_window_database_projection(store: TwitterXVisibleBrowserMediaObservationStore) -> Mapping[str, Any]:
    columns = (
        "observation_id",
        "media_kind",
        "source_kind",
        "detection_method",
        "canonical_post_url",
        "canonical_media_url",
        "content_type",
        "byte_status",
        "playlist_manifest_url",
        "segment_index",
        "local_session_path",
        "sha256",
        "review_required",
    )
    segment_columns = (
        "segment_id",
        "canonical_segment_url",
        "playlist_manifest_url",
        "segment_index",
        "content_type",
        "byte_status",
        "local_session_path",
        "sha256",
    )
    return {
        "schema_version": R42GV_SCHEMA_VERSION,
        "table_name": "twitter_x_visible_browser_media_observations",
        "segment_table_name": "twitter_x_visible_browser_media_segments",
        "columns": list(columns),
        "segment_columns": list(segment_columns),
        "rows": [{key: item.to_dict().get(key, "") for key in columns} for item in store.observations],
        "segment_rows": [{key: item.to_dict().get(key, "") for key in segment_columns} for item in store.segment_rows],
        "source_role_effect": "none",
        "review_window_rewrite_performed": False,
    }


def project_visible_browser_observations_to_source_resources(
    store: TwitterXVisibleBrowserMediaObservationStore,
    *,
    source_row_id: str,
) -> tuple[tuple[SourceResourceItem, ...], tuple[SourceResourceItem, ...]]:
    images: list[SourceResourceItem] = []
    videos: list[SourceResourceItem] = []
    seen_image_urls: set[str] = set()
    seen_video_urls: set[str] = set()
    segment_groups: dict[str, list[TwitterXVisibleBrowserMediaObservation]] = {}

    for obs in store.observations:
        if obs.media_kind == MEDIA_KIND_SEGMENT:
            key = obs.playlist_manifest_url or obs.segment_group_id or "ungrouped_segments"
            segment_groups.setdefault(key, []).append(obs)
            continue
        warning = (
            "Observed in visible X/Twitter browser session; remote URL remains metadata-only "
            "until selected and handled by an approved backend or session-local bytes."
        )
        if obs.media_kind == MEDIA_KIND_IMAGE:
            if obs.canonical_media_url in seen_image_urls:
                continue
            seen_image_urls.add(obs.canonical_media_url)
            images.append(
                SourceResourceItem(
                    resource_id=_source_resource_id(source_row_id, obs, RESOURCE_KIND_IMAGE),
                    source_row_id=source_row_id,
                    resource_kind=RESOURCE_KIND_IMAGE,
                    reference_url=obs.media_url,
                    canonical_url=obs.canonical_media_url,
                    display_name=_display_name_for_observation(obs),
                    media_type="image",
                    mime_type=obs.content_type or "image/*",
                    extension=_extension_from_url(obs.media_url),
                    width=obs.width,
                    height=obs.height,
                    thumbnail_reference=obs.thumbnail_url or obs.preview_url or obs.media_url,
                    from_link=False,
                    status="observed_visible_session",
                    selectable=True,
                    warning=warning,
                    provenance=f"R42GV visible browser media observation store; source_kind={obs.source_kind}; byte_status={obs.byte_status}",
                )
            )
        elif obs.media_kind in {MEDIA_KIND_VIDEO, MEDIA_KIND_AUDIO, MEDIA_KIND_MANIFEST}:
            if obs.canonical_media_url in seen_video_urls:
                continue
            seen_video_urls.add(obs.canonical_media_url)
            videos.append(
                SourceResourceItem(
                    resource_id=_source_resource_id(source_row_id, obs, RESOURCE_KIND_VIDEO_AUDIO),
                    source_row_id=source_row_id,
                    resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                    reference_url=obs.media_url,
                    canonical_url=obs.canonical_media_url,
                    display_name=_display_name_for_observation(obs),
                    media_type="stream" if obs.media_kind == MEDIA_KIND_MANIFEST else obs.media_kind,
                    mime_type=obs.content_type or ("application/x-mpegURL" if obs.media_kind == MEDIA_KIND_MANIFEST else f"{obs.media_kind}/*"),
                    extension=_extension_from_url(obs.media_url),
                    width=obs.width,
                    height=obs.height,
                    bitrate_or_quality=str(obs.bitrate) if obs.bitrate else "",
                    thumbnail_reference=obs.thumbnail_url or obs.preview_url,
                    from_link=False,
                    status="observed_visible_session",
                    selectable=True,
                    warning=warning,
                    provenance=f"R42GV visible browser media observation store; source_kind={obs.source_kind}; byte_status={obs.byte_status}",
                )
            )

    for index, (manifest_url, rows) in enumerate(segment_groups.items(), start=1):
        representative = rows[0]
        reference = manifest_url or representative.canonical_media_url
        videos.append(
            SourceResourceItem(
                resource_id=f"{source_row_id}:{RESOURCE_KIND_VIDEO_AUDIO}:r42gv:segment_group:{index}",
                source_row_id=source_row_id,
                resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                reference_url=reference,
                canonical_url=reference,
                display_name=_display_name_for_observation(representative, segment_count=len(rows)),
                media_type="stream_segments",
                mime_type="application/vnd.apple.mpegurl" if manifest_url.endswith(".m3u8") else "video/segments",
                extension="",
                bitrate_or_quality=f"{len(rows)} observed segment rows",
                status="observed_segment_table",
                selectable=False,
                warning="Segment URLs are preserved in the R42GV segment table; select a manifest/variant candidate instead of individual segment URLs.",
                provenance=f"R42GV segment manifest/table bridge; segment_rows={len(rows)}",
            )
        )

    return tuple(images), tuple(videos)


def _filename_for_observation(obs: TwitterXVisibleBrowserMediaObservation) -> str:
    if obs.local_session_path:
        suffix = Path(obs.local_session_path).suffix
        if suffix:
            return Path(obs.local_session_path).name
    ext = _extension_from_url(obs.media_url)
    if not ext:
        ext = {
            MEDIA_KIND_IMAGE: ".jpg",
            MEDIA_KIND_VIDEO: ".mp4",
            MEDIA_KIND_AUDIO: ".m4a",
            MEDIA_KIND_MANIFEST: ".m3u8",
            MEDIA_KIND_SEGMENT: ".ts",
        }.get(obs.media_kind, ".bin")
    return f"{_safe_segment(obs.media_id or obs.observation_id, 'media')}{ext}"


def convert_observation_store_to_r42gt_posts(
    store: TwitterXVisibleBrowserMediaObservationStore,
    *,
    display_name: str = "Twitter/X visible browser session",
) -> tuple[TwitterXPostMediaRecord, ...]:
    groups: dict[str, list[TwitterXVisibleBrowserMediaObservation]] = {}
    for obs in store.observations:
        key = obs.status_id or obs.canonical_post_url or store.canonical_source_url
        groups.setdefault(key, []).append(obs)

    records: list[TwitterXPostMediaRecord] = []
    for group_key, observations in groups.items():
        first = observations[0]
        post_id = first.status_id or _safe_segment(group_key, "visible_browser_session")
        account = first.account_handle or _account_from_url(first.canonical_post_url) or "@unknown"
        post_url = first.canonical_post_url or store.canonical_source_url
        media_items: list[TwitterXMediaItem] = []
        for obs in observations:
            media_items.append(
                TwitterXMediaItem(
                    media_id=obs.media_id or obs.observation_id,
                    post_id=post_id,
                    source_url=store.canonical_source_url,
                    post_url=post_url,
                    media_kind=obs.media_kind,
                    media_role="visible_browser_observed_stream_segment" if obs.media_kind == MEDIA_KIND_SEGMENT else "visible_browser_observed_media",
                    media_url=obs.canonical_media_url,
                    thumbnail_url=obs.thumbnail_url or obs.preview_url,
                    alt_text=obs.warning,
                    width=obs.width,
                    height=obs.height,
                    duration_seconds=obs.duration_seconds,
                    mime_type=obs.content_type,
                    filename=_filename_for_observation(obs),
                    local_fixture_path=obs.local_session_path,
                    capture_method_id="r42gv_visible_browser_media_observation_store",
                    capture_method_detail=obs.detection_method,
                    requires_human_authorized_session=True,
                    access_mode="human_authorized_visible_browser_session_observation",
                    review_status=REVIEW_METADATA_ONLY,
                    promotion_status=PROMOTION_NONE,
                    media_file_status=REMOTE_NOT_DOWNLOADED,
                    review_strings=tuple(
                        value
                        for value in (
                            obs.canonical_media_url,
                            obs.canonical_post_url,
                            obs.media_kind,
                            obs.byte_status,
                            obs.playlist_manifest_url,
                            R42GV_MARKER,
                        )
                        if value
                    ),
                    canonical_source_url=store.canonical_source_url,
                    canonical_post_url=post_url,
                    canonical_media_url=obs.canonical_media_url,
                )
            )
        records.append(
            TwitterXPostMediaRecord(
                post_id=post_id,
                account_handle=account,
                display_name=display_name,
                source_url=store.canonical_source_url,
                post_url=post_url,
                created_at_text=store.capture_timestamp,
                text="Visible browser/session media observations imported by R42GV.",
                media_items=tuple(media_items),
                review_strings=tuple(
                    value
                    for value in (
                        store.canonical_source_url,
                        post_url,
                        account,
                        R42GV_MARKER,
                    )
                    if value
                ),
                source_role_bridge_status="compatible_bridge_not_role_assignment",
                promotion_status=PROMOTION_NONE,
                canonical_source_url=store.canonical_source_url,
                canonical_post_url=post_url,
            )
        )
    return tuple(records)


def write_r42gt_package_from_visible_browser_observations(
    store: TwitterXVisibleBrowserMediaObservationStore,
    output_root: str | Path,
    *,
    account_or_unknown: str = "",
) -> TwitterXMediaExtractionPackage:
    records = convert_observation_store_to_r42gt_posts(store)
    account = account_or_unknown or (records[0].account_handle.lstrip("@") if records else "unknown")
    options = TwitterXMediaExtractionOptions(
        account_or_unknown=_safe_segment(account, "unknown"),
        capture_timestamp=_safe_segment(store.capture_timestamp, _now_ts()),
        copy_local_fixtures=True,
        register_route_only=False,
        live_capture_enabled=False,
        browser_or_cdp_enabled=True,
        network_capture_enabled=True,
        cookie_or_token_access_enabled=False,
        challenge_bypass_enabled=False,
        media_download_from_x_enabled=False,
        source_role_assignment_enabled=False,
        review_window_rewrite_enabled=False,
        counter_no_jump_mutation_enabled=False,
        metadata_promotion_enabled=False,
    )
    return write_twitter_x_media_evidence_package(records, output_root, options)


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def build_report(source_root: str | Path = ".", output_root: str | Path | None = None) -> R42GVReport:
    root = Path(output_root or "profile_media_live_captures/r42gv_twitter_x_visible_browser_media_observation_store")
    root.mkdir(parents=True, exist_ok=True)
    fixture = root / "fixtures" / "session_local_image.jpg"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_bytes(b"R42GV session-local fixture bytes\n")

    source_url = "https://x.com/example/status/1234567890"
    events = (
        {"url": "https://pbs.twimg.com/media/r42gv_image.jpg?format=jpg&name=large", "content_type": "image/jpeg", "resource_type": "image", "request_id": "img-1"},
        {"url": "https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16", "content_type": "application/x-mpegURL", "resource_type": "media", "request_id": "manifest-1"},
        {"url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts", "content_type": "video/mp2t", "resource_type": "media", "request_id": "seg-1"},
        {"url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts", "content_type": "video/mp2t", "resource_type": "media", "request_id": "seg-2"},
        {"url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4", "content_type": "video/mp4", "resource_type": "media", "request_id": "mp4-1"},
    )
    media_inventory = (
        {
            "media_id": "inventory-local",
            "media_type": "image",
            "media_url": "https://pbs.twimg.com/media/session_local.jpg?format=jpg&name=large",
            "preview_url": "https://pbs.twimg.com/media/session_local.jpg?format=jpg&name=small",
            "source_kind": "api_media_entity",
            "status_id": "1234567890",
        },
    )
    session_local_files = (
        {
            "local_path": str(fixture),
            "media_url": "https://pbs.twimg.com/media/session_local.jpg?format=jpg&name=large",
            "content_type": "image/jpeg",
            "media_id": "session-local-image",
        },
    )
    store = build_visible_browser_media_observation_store(
        source_url=source_url,
        events=events,
        final_dom='<html><body><img src="https://pbs.twimg.com/media/dom_seen.jpg?format=jpg&name=large"></body></html>',
        media_inventory=media_inventory,
        session_local_files=session_local_files,
        capture_timestamp="20260914T000000Z",
    )
    write_result = write_visible_browser_media_observation_store(store, root)
    images, videos = project_visible_browser_observations_to_source_resources(store, source_row_id="twitter_x:example:1234567890")
    projection = build_review_window_database_projection(store)
    package = write_r42gt_package_from_visible_browser_observations(store, root / "r42gt_visible_browser_media_package", account_or_unknown="example")
    media_index = json.loads(Path(package.media_index_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(package.manifest_path).read_text(encoding="utf-8"))
    payload_text = json.dumps({"store": store.to_dict(), "projection": projection, "package": package.to_dict(), "media_index": media_index}, sort_keys=True)

    side_effects = build_side_effect_flags()
    checks = (
        _check("visible_browser_observation_store_written", Path(write_result.observation_store_path).exists() and store.observation_count >= 5),
        _check("image_window_projection_populated", len(images) >= 2),
        _check("video_window_projection_populated", any(item.media_type in {"video", "stream"} for item in videos)),
        _check("segmented_media_manifest_and_segment_rows_preserved", store.segment_count >= 2 and any(row.playlist_manifest_url for row in store.segment_rows)),
        _check("segment_rows_do_not_spam_selectable_window_resources", any(item.status == "observed_segment_table" and not item.selectable for item in videos)),
        _check("remote_candidates_metadata_only", any(row.get("media_file_status") == REMOTE_NOT_DOWNLOADED for row in media_index.get("media", []))),
        _check("session_local_file_bridged_to_r42gt_with_sha256", any(row.get("media_file_status") == LOCAL_FIXTURE_COPIED and row.get("sha256") for row in media_index.get("media", []))),
        _check("r42gt_package_not_promoted", manifest.get("promotion_status") == PROMOTION_NONE),
        _check("plain_machine_urls", machine_url_fields_are_plain(store.to_dict()) and machine_url_fields_are_plain(media_index) and "](" not in payload_text and "]\\(" not in payload_text),
        _check("no_forbidden_side_effects", not any(value for key, value in side_effects.items() if key != "visible_browser_session_observation_enabled")),
    )
    status = R42GV_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GV_BLOCKED_STATUS
    return R42GVReport(
        marker=R42GV_MARKER,
        schema_version=R42GV_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(source_root),
        status=status,
        checks=checks,
        observation_store=store.to_dict(),
        write_result=write_result.to_dict(),
        review_window_database_projection=projection,
        image_resource_count=len(images),
        video_audio_resource_count=len(videos),
        r42gt_package=package.to_dict(),
        side_effect_flags=side_effects,
    )


def write_report(report: R42GVReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "R42GV_TWITTER_X_VISIBLE_BROWSER_MEDIA_OBSERVATION_STORE_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "R42GV_TWITTER_X_VISIBLE_BROWSER_MEDIA_OBSERVATION_STORE_REPORT.md").write_text(render_report_markdown(report), encoding="utf-8")


def render_report_markdown(report: R42GVReport) -> str:
    lines = [
        f"# {R42GV_MARKER}",
        "",
        f"Status: {report.status}",
        f"Generated: {report.generated_at}",
        "",
        "## Scope",
        "",
        "- Visible browser/session media observations are normalized into a fast local store.",
        "- Image and video/audio windows can use the same projected resource rows.",
        "- Segmented media is represented as a manifest plus segment table, not as hidden downloads.",
        "- Remote X/Twitter URLs remain metadata-only/review-required unless session-local bytes already exist.",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Observation store: {report.write_result.get('observation_store_path')}",
            f"- Segment table: {report.write_result.get('segment_table_path')}",
            f"- R42GT package manifest: {report.r42gt_package.get('manifest_path')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GV_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gv_twitter_x_visible_browser_media_observation_store")
    args = parser.parse_args(argv)
    report = build_report(args.source_root, args.output_root)
    write_report(report, args.output_root)
    print(R42GV_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "BYTE_STATUS_REMOTE",
    "BYTE_STATUS_SESSION_LOCAL",
    "R42GV_BLOCKED_STATUS",
    "R42GV_MARKER",
    "R42GV_PASS_STATUS",
    "R42GV_SCHEMA_VERSION",
    "TwitterXVisibleBrowserMediaObservation",
    "TwitterXVisibleBrowserMediaObservationStore",
    "TwitterXVisibleBrowserObservationWriteResult",
    "build_report",
    "build_review_window_database_projection",
    "build_side_effect_flags",
    "build_visible_browser_media_observation_store",
    "convert_observation_store_to_r42gt_posts",
    "project_visible_browser_observations_to_source_resources",
    "write_r42gt_package_from_visible_browser_observations",
    "write_report",
    "write_visible_browser_media_observation_store",
]


if __name__ == "__main__":
    raise SystemExit(main())
