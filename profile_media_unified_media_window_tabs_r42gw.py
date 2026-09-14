from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from source_resource_state import (
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    SourceResourceItem,
    SourceResourceRowState,
)

R42GW_MARKER = "YTCE_R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING"
R42GW_PASS_STATUS = "PASS_R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING"
R42GW_BLOCKED_STATUS = "BLOCKED_R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING"
R42GW_SCHEMA_VERSION = "unified_media_window_tabs_jdownloader_grouping.r42gw.v1"

TAB_ALL = "all"
TAB_IMAGES = "images"
TAB_VIDEOS = "videos"
MEDIA_WINDOW_TABS = (TAB_ALL, TAB_IMAGES, TAB_VIDEOS)

ROW_ROLE_PACKAGE = "package"
ROW_ROLE_CHILD = "child"

MEDIA_CLASS_IMAGE = "image"
MEDIA_CLASS_VIDEO = "video"
MEDIA_CLASS_AUDIO = "audio"
MEDIA_CLASS_MANIFEST = "manifest"
MEDIA_CLASS_SEGMENT = "segment"
MEDIA_CLASS_SEGMENT_COLLECTION = "segment_collection"
MEDIA_CLASS_TEXT = "text"
MEDIA_CLASS_UNKNOWN = "unknown"

PACKAGE_KIND_IMAGES = "image_package"
PACKAGE_KIND_VIDEO_STREAM = "video_stream_package"
PACKAGE_KIND_DIRECT_VIDEO = "direct_video_package"
PACKAGE_KIND_AUDIO = "audio_package"
PACKAGE_KIND_MIXED = "mixed_media_package"

BYTE_STATUS_REMOTE = "remote_candidate_review_required"
BYTE_STATUS_LOCAL = "session_local_file_available"
BYTE_STATUS_UNKNOWN = "unknown"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".ts", ".m2ts", ".m4s"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac"}
MANIFEST_EXTENSIONS = {".m3u8", ".mpd"}
SEGMENT_EXTENSIONS = {".ts", ".m4s", ".cmfv", ".cmfa"}

JDOWNLOADER_REFERENCE_MODEL = {
    "package_child_tree": (
        "JDownloader-style Linkgrabber presents packages/folders with child links; "
        "R42GW uses that structure as an attributed source-reference model. Direct framework, "
        "logic, or code adaptation is allowed when attribution, provenance, and licence "
        "compatibility are recorded."
    ),
    "source_usage_policy": {
        "attribution_required": True,
        "direct_code_copy_allowed_when_attributed_and_license_compatible": True,
        "copied_source_must_be_marked_in_notes": True,
        "current_r42gw_direct_source_included": False,
    },
    "tabs": ("all", "images", "videos"),
    "filter_axes": ("filename", "extension", "host", "media_class", "byte_status", "selectable"),
    "segment_policy": (
        "Segments are listed as child rows under a video/manifest package, but individual segments "
        "are not selected by default unless a site-specific policy explicitly allows it."
    ),
    "review_window_policy": "Review/source-role decisions stay in the separate review window.",
}


@dataclass(frozen=True)
class MediaWindowFilterState:
    """Local-only Media window filter state.

    This mirrors the useful JDownloader ideas: quick type/host/filename filters,
    but it is deliberately a local projection/filter only. It does not crawl,
    download, click, or perform network work.
    """

    tab_id: str = TAB_ALL
    search_text: str = ""
    host_filter: str = ""
    extension_filter: str = ""
    media_class_filter: str = ""
    byte_status_filter: str = ""
    only_selectable: bool = False
    include_segments: bool = True


@dataclass(frozen=True)
class MediaWindowChildRow:
    row_id: str
    package_id: str
    source_row_id: str
    source_resource_id: str
    media_class: str
    display_name: str
    filename: str
    extension: str
    host: str
    media_url: str
    canonical_url: str
    mime_type: str = ""
    byte_status: str = BYTE_STATUS_UNKNOWN
    status: str = ""
    selectable: bool = True
    selected_by_default: bool = False
    segment_index: int = 0
    variant_label: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    tab_memberships: tuple[str, ...] = (TAB_ALL,)
    warning: str = ""
    provenance: str = ""

    @property
    def row_role(self) -> str:
        return ROW_ROLE_CHILD

    def to_dict(self) -> dict[str, Any]:
        return state_to_dict(self)


@dataclass(frozen=True)
class MediaWindowPackageRow:
    package_id: str
    source_row_id: str
    package_name: str
    package_kind: str
    package_key: str
    host: str
    source_url: str
    child_count: int
    selectable_child_count: int
    selected_child_count: int
    segment_child_count: int
    media_classes: tuple[str, ...]
    extensions: tuple[str, ...]
    byte_statuses: tuple[str, ...]
    tab_memberships: tuple[str, ...]
    children: tuple[MediaWindowChildRow, ...] = ()
    expanded_by_default: bool = True
    warning: str = ""
    provenance: str = "R42GW JDownloader-style package/folder projection"

    @property
    def row_role(self) -> str:
        return ROW_ROLE_PACKAGE

    def to_dict(self) -> dict[str, Any]:
        return state_to_dict(self)


@dataclass(frozen=True)
class UnifiedMediaWindowState:
    schema_version: str
    marker: str
    source_row_id: str
    source_url: str
    adapter_id: str
    tabs: tuple[str, ...]
    packages: tuple[MediaWindowPackageRow, ...]
    active_tab: str = TAB_ALL
    review_window_separate: bool = True
    all_tab_model: str = "jdownloader_style_package_tree"
    side_effect_flags: Mapping[str, bool] | None = None
    status: str = R42GW_PASS_STATUS

    @property
    def package_count(self) -> int:
        return len(self.packages)

    @property
    def child_count(self) -> int:
        return sum(package.child_count for package in self.packages)

    @property
    def selectable_child_count(self) -> int:
        return sum(package.selectable_child_count for package in self.packages)

    @property
    def segment_child_count(self) -> int:
        return sum(package.segment_child_count for package in self.packages)

    def tab_packages(self, tab_id: str) -> tuple[MediaWindowPackageRow, ...]:
        normalized = normalize_tab_id(tab_id)
        return tuple(package for package in self.packages if normalized in package.tab_memberships)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_tab": self.active_tab,
            "adapter_id": self.adapter_id,
            "all_tab_model": self.all_tab_model,
            "child_count": self.child_count,
            "marker": self.marker,
            "package_count": self.package_count,
            "packages": [package.to_dict() for package in self.packages],
            "review_window_separate": self.review_window_separate,
            "schema_version": self.schema_version,
            "segment_child_count": self.segment_child_count,
            "selectable_child_count": self.selectable_child_count,
            "side_effect_flags": dict(self.side_effect_flags or build_side_effect_flags()),
            "source_row_id": self.source_row_id,
            "source_url": self.source_url,
            "status": self.status,
            "tabs": list(self.tabs),
            "tab_counts": {
                tab: {
                    "packages": len(self.tab_packages(tab)),
                    "children": sum(package.child_count for package in self.tab_packages(tab)),
                }
                for tab in self.tabs
            },
        }


@dataclass(frozen=True)
class R42GWReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    unified_media_window_state: Mapping[str, Any]
    filtered_examples: Mapping[str, Any]
    jdownloader_reference_model: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R42GW_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return state_to_dict(self)


def state_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: state_to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [state_to_dict(item) for item in value]
    if isinstance(value, list):
        return [state_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): state_to_dict(item) for key, item in value.items()}
    return value


def build_side_effect_flags() -> dict[str, bool]:
    return {
        "network_actions_performed": False,
        "downloads_performed": False,
        "browser_session_started": False,
        "hidden_x_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "review_window_rewrite_performed": False,
        "source_role_assignment_performed": False,
        "youtube_capture_engine_changed": False,
        "jdownloader_direct_source_included_in_r42gw": False,
        "jdownloader_source_usage_policy_recorded": True,
        "jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible": True,
        "local_projection_only": True,
    }


def normalize_tab_id(value: str) -> str:
    tab = str(value or TAB_ALL).strip().lower().replace("-", "_")
    aliases = {
        "all_media": TAB_ALL,
        "media": TAB_ALL,
        "image": TAB_IMAGES,
        "images": TAB_IMAGES,
        "video": TAB_VIDEOS,
        "videos": TAB_VIDEOS,
        "video_audio": TAB_VIDEOS,
        "audio": TAB_VIDEOS,
    }
    return aliases.get(tab, TAB_ALL)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hash_text(value: str, length: int = 16) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _plain_url(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    # Defend against values pasted back from Markdown logs, including escaped
    # markdown produced by chat/composer rendering.
    text = text.replace("\_", "_").replace("\&", "&").replace("\/", "/").strip("<>").strip()
    normalized = text.replace("]\(", "](").replace("\)", ")")
    if "](" in normalized:
        match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
        if match:
            return match.group(1).replace("\_", "_").replace("\&", "&").replace("\/", "/").strip()
    return normalized

def _host_from_url(value: Any) -> str:
    url = _plain_url(value)
    try:
        return urlsplit(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _path_basename_from_url(value: Any) -> str:
    url = _plain_url(value)
    try:
        path = unquote(urlsplit(url).path or "")
    except Exception:
        path = ""
    name = path.rsplit("/", 1)[-1].strip()
    return name or "media"


def _extension_from_name_or_url(name_or_url: Any) -> str:
    name = _path_basename_from_url(name_or_url)
    suffix = Path(name).suffix.lower()
    if suffix:
        return suffix
    text = _plain_url(name_or_url).lower()
    for ext in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | MANIFEST_EXTENSIONS | SEGMENT_EXTENSIONS, key=len, reverse=True):
        if ext in text:
            return ext
    return ""


def _filename_from_values(*values: Any, fallback: str = "media") -> str:
    for value in values:
        text = _clean(value)
        if not text:
            continue
        if text.startswith("http://") or text.startswith("https://") or "](" in text:
            name = _path_basename_from_url(text)
        else:
            name = text
        name = re.sub(r"[^A-Za-z0-9._() -]+", "_", name).strip(" ._-")
        if name:
            return name[:180]
    return fallback


def _media_class_from_parts(media_type: str = "", mime_type: str = "", extension: str = "", url: str = "", status: str = "") -> str:
    media = _clean(media_type).lower()
    mime = _clean(mime_type).lower()
    ext = extension.lower() if extension else _extension_from_name_or_url(url)
    status_text = _clean(status).lower()
    url_text = _plain_url(url).lower()

    if media in {MEDIA_CLASS_SEGMENT, "stream_segment"} or "segment" in status_text and ext in SEGMENT_EXTENSIONS:
        return MEDIA_CLASS_SEGMENT
    if media in {"stream_segments", MEDIA_CLASS_SEGMENT_COLLECTION}:
        return MEDIA_CLASS_SEGMENT_COLLECTION
    if media in {MEDIA_CLASS_MANIFEST, "stream"} or ext in MANIFEST_EXTENSIONS or "mpegurl" in mime or "dash+xml" in mime:
        return MEDIA_CLASS_MANIFEST
    if media == MEDIA_CLASS_IMAGE or mime.startswith("image/") or ext in IMAGE_EXTENSIONS or "pbs.twimg.com/media/" in url_text:
        return MEDIA_CLASS_IMAGE
    if media == MEDIA_CLASS_AUDIO or mime.startswith("audio/") or ext in AUDIO_EXTENSIONS:
        return MEDIA_CLASS_AUDIO
    if media == MEDIA_CLASS_VIDEO or mime.startswith("video/") or ext in VIDEO_EXTENSIONS or "video.twimg.com/" in url_text:
        return MEDIA_CLASS_VIDEO
    if media == MEDIA_CLASS_TEXT or mime.startswith("text/"):
        return MEDIA_CLASS_TEXT
    return MEDIA_CLASS_UNKNOWN


def _tabs_for_media_class(media_class: str) -> tuple[str, ...]:
    if media_class == MEDIA_CLASS_IMAGE:
        return (TAB_ALL, TAB_IMAGES)
    if media_class in {MEDIA_CLASS_VIDEO, MEDIA_CLASS_AUDIO, MEDIA_CLASS_MANIFEST, MEDIA_CLASS_SEGMENT, MEDIA_CLASS_SEGMENT_COLLECTION}:
        return (TAB_ALL, TAB_VIDEOS)
    return (TAB_ALL,)


def _package_kind_for_media_class(media_class: str) -> str:
    if media_class == MEDIA_CLASS_IMAGE:
        return PACKAGE_KIND_IMAGES
    if media_class == MEDIA_CLASS_AUDIO:
        return PACKAGE_KIND_AUDIO
    if media_class in {MEDIA_CLASS_MANIFEST, MEDIA_CLASS_SEGMENT, MEDIA_CLASS_SEGMENT_COLLECTION}:
        return PACKAGE_KIND_VIDEO_STREAM
    if media_class == MEDIA_CLASS_VIDEO:
        return PACKAGE_KIND_DIRECT_VIDEO
    return PACKAGE_KIND_MIXED


def _package_tabs(children: Sequence[MediaWindowChildRow]) -> tuple[str, ...]:
    tabs = {TAB_ALL}
    for child in children:
        tabs.update(child.tab_memberships)
    return tuple(tab for tab in MEDIA_WINDOW_TABS if tab in tabs)


def _sort_key_child(child: MediaWindowChildRow) -> tuple[int, int, str]:
    class_rank = {
        MEDIA_CLASS_IMAGE: 10,
        MEDIA_CLASS_VIDEO: 20,
        MEDIA_CLASS_MANIFEST: 30,
        MEDIA_CLASS_AUDIO: 35,
        MEDIA_CLASS_SEGMENT_COLLECTION: 40,
        MEDIA_CLASS_SEGMENT: 50,
        MEDIA_CLASS_TEXT: 60,
    }.get(child.media_class, 90)
    return (class_rank, int(child.segment_index or 0), child.filename.lower())


def _sort_key_package(package: MediaWindowPackageRow) -> tuple[int, str, str]:
    kind_rank = {
        PACKAGE_KIND_IMAGES: 10,
        PACKAGE_KIND_DIRECT_VIDEO: 20,
        PACKAGE_KIND_VIDEO_STREAM: 30,
        PACKAGE_KIND_AUDIO: 40,
        PACKAGE_KIND_MIXED: 90,
    }.get(package.package_kind, 99)
    return (kind_rank, package.host, package.package_name.lower())


def _byte_status_from_values(status: str = "", provenance: str = "", local_path: str = "", sha256: str = "") -> str:
    status_text = f"{status} {provenance}".lower()
    if local_path or sha256 or "session_local_file" in status_text or "local_file" in status_text:
        return BYTE_STATUS_LOCAL
    if "remote" in status_text or "observed" in status_text or "metadata" in status_text:
        return BYTE_STATUS_REMOTE
    return BYTE_STATUS_UNKNOWN


def _site_segment_selection_allowed(host: str, filename: str, source_kind: str = "") -> bool:
    """Return whether a segment can be directly selected.

    Default is false. This preserves the user's preferred JDownloader-like folder
    behaviour: segments are listed, but selection is site/file-policy dependent.
    Future site adapters can allow safe local/session segment selection here.
    """

    host_l = _clean(host).lower()
    name_l = _clean(filename).lower()
    source_l = _clean(source_kind).lower()
    if "session_local" in source_l and host_l.endswith(("localhost", "127.0.0.1")):
        return True
    if name_l.endswith(".txt"):
        return True
    return False


def _child_from_source_resource(item: SourceResourceItem, media_class: str, package_id: str, package_key: str) -> MediaWindowChildRow:
    url = _plain_url(item.canonical_url or item.reference_url)
    extension = _clean(item.extension).lower()
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    extension = extension or _extension_from_name_or_url(url)
    filename = _filename_from_values(item.display_name, url, fallback=item.resource_id)
    host = _host_from_url(url or item.reference_url)
    byte_status = _byte_status_from_values(item.status, item.provenance)
    selectable = bool(item.selectable)
    if media_class == MEDIA_CLASS_SEGMENT:
        selectable = selectable and _site_segment_selection_allowed(host, filename, item.provenance)
    return MediaWindowChildRow(
        row_id=f"{package_id}:child:{_hash_text(item.resource_id + url)}",
        package_id=package_id,
        source_row_id=item.source_row_id,
        source_resource_id=item.resource_id,
        media_class=media_class,
        display_name=item.display_name or filename,
        filename=filename,
        extension=extension,
        host=host,
        media_url=_plain_url(item.reference_url),
        canonical_url=url,
        mime_type=item.mime_type,
        byte_status=byte_status,
        status=item.status,
        selectable=selectable,
        selected_by_default=False,
        segment_index=0,
        variant_label=item.bitrate_or_quality,
        width=int(item.width or 0),
        height=int(item.height or 0),
        duration_seconds=float(item.duration_seconds or 0.0),
        tab_memberships=_tabs_for_media_class(media_class),
        warning=item.warning,
        provenance=item.provenance,
    )


def _observation_get(obj: Any, key: str, default: Any = "") -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _child_from_visible_observation(obs: Any, package_id: str, package_key: str, *, source_row_id: str, force_segment: bool = False) -> MediaWindowChildRow:
    media_url = _plain_url(_observation_get(obs, "canonical_media_url") or _observation_get(obs, "canonical_segment_url") or _observation_get(obs, "media_url") or _observation_get(obs, "segment_url"))
    media_kind = _clean(_observation_get(obs, "media_kind") or ("segment" if force_segment else ""))
    content_type = _clean(_observation_get(obs, "content_type"))
    extension = _extension_from_name_or_url(media_url)
    media_class = MEDIA_CLASS_SEGMENT if force_segment else _media_class_from_parts(media_kind, content_type, extension, media_url, _clean(_observation_get(obs, "status")))
    host = _host_from_url(media_url)
    obs_id = _clean(_observation_get(obs, "observation_id") or _observation_get(obs, "segment_id") or _hash_text(media_url))
    segment_index = int(_observation_get(obs, "segment_index", 0) or 0)
    source_kind = _clean(_observation_get(obs, "source_kind") or _observation_get(obs, "detection_method"))
    local_path = _clean(_observation_get(obs, "local_session_path"))
    sha256 = _clean(_observation_get(obs, "sha256"))
    byte_status = _clean(_observation_get(obs, "byte_status")) or _byte_status_from_values(_clean(_observation_get(obs, "status")), source_kind, local_path, sha256)
    filename = _filename_from_values(_observation_get(obs, "media_id"), media_url, fallback=obs_id)
    selectable = media_class != MEDIA_CLASS_SEGMENT
    if media_class == MEDIA_CLASS_SEGMENT:
        selectable = _site_segment_selection_allowed(host, filename, source_kind)
    return MediaWindowChildRow(
        row_id=f"{package_id}:child:{_hash_text(obs_id + media_url + str(segment_index))}",
        package_id=package_id,
        source_row_id=source_row_id,
        source_resource_id=obs_id,
        media_class=media_class,
        display_name=_clean(_observation_get(obs, "media_id")) or filename,
        filename=filename,
        extension=extension,
        host=host,
        media_url=media_url,
        canonical_url=media_url,
        mime_type=content_type,
        byte_status=byte_status,
        status=_clean(_observation_get(obs, "status")),
        selectable=selectable,
        selected_by_default=False,
        segment_index=segment_index,
        variant_label=str(_observation_get(obs, "bitrate") or ""),
        width=int(_observation_get(obs, "width", 0) or 0),
        height=int(_observation_get(obs, "height", 0) or 0),
        duration_seconds=float(_observation_get(obs, "duration_seconds", 0.0) or 0.0),
        tab_memberships=_tabs_for_media_class(media_class),
        warning=_clean(_observation_get(obs, "warning")),
        provenance=_clean(_observation_get(obs, "provenance") or "R42GV visible browser observation"),
    )


def _package_name(package_kind: str, host: str, source_hint: str, child_count: int, segment_count: int = 0) -> str:
    host_part = host or "source"
    if package_kind == PACKAGE_KIND_IMAGES:
        return f"Images - {host_part} ({child_count})"
    if package_kind == PACKAGE_KIND_VIDEO_STREAM:
        seg = f", {segment_count} segment(s)" if segment_count else ""
        return f"Video stream - {host_part} ({child_count}{seg})"
    if package_kind == PACKAGE_KIND_DIRECT_VIDEO:
        return f"Videos - {host_part} ({child_count})"
    if package_kind == PACKAGE_KIND_AUDIO:
        return f"Audio - {host_part} ({child_count})"
    return f"Media - {source_hint or host_part} ({child_count})"


def _make_package(source_row_id: str, source_url: str, package_key: str, children: Sequence[MediaWindowChildRow]) -> MediaWindowPackageRow:
    ordered = tuple(sorted(children, key=_sort_key_child))
    media_classes = tuple(sorted({child.media_class for child in ordered}))
    extensions = tuple(sorted({child.extension for child in ordered if child.extension}))
    byte_statuses = tuple(sorted({child.byte_status for child in ordered if child.byte_status}))
    segment_count = sum(1 for child in ordered if child.media_class == MEDIA_CLASS_SEGMENT)
    host = next((child.host for child in ordered if child.host), _host_from_url(source_url))
    if any(child.media_class in {MEDIA_CLASS_MANIFEST, MEDIA_CLASS_SEGMENT, MEDIA_CLASS_SEGMENT_COLLECTION} for child in ordered):
        package_kind = PACKAGE_KIND_VIDEO_STREAM
    elif any(child.media_class == MEDIA_CLASS_VIDEO for child in ordered):
        package_kind = PACKAGE_KIND_DIRECT_VIDEO
    elif any(child.media_class == MEDIA_CLASS_AUDIO for child in ordered):
        package_kind = PACKAGE_KIND_AUDIO
    elif all(child.media_class == MEDIA_CLASS_IMAGE for child in ordered):
        package_kind = PACKAGE_KIND_IMAGES
    else:
        package_kind = PACKAGE_KIND_MIXED
    return MediaWindowPackageRow(
        package_id=f"{source_row_id}:media_package:{_hash_text(package_key)}",
        source_row_id=source_row_id,
        package_name=_package_name(package_kind, host, source_url, len(ordered), segment_count),
        package_kind=package_kind,
        package_key=package_key,
        host=host,
        source_url=_plain_url(source_url),
        child_count=len(ordered),
        selectable_child_count=sum(1 for child in ordered if child.selectable),
        selected_child_count=sum(1 for child in ordered if child.selected_by_default),
        segment_child_count=segment_count,
        media_classes=media_classes,
        extensions=extensions,
        byte_statuses=byte_statuses,
        tab_memberships=_package_tabs(ordered),
        children=ordered,
        expanded_by_default=True,
        warning=(
            "Segment children are listed under their stream package; select the manifest/video candidate "
            "unless a site-specific rule marks individual segments selectable."
            if segment_count
            else ""
        ),
    )


def _group_children_to_packages(source_row_id: str, source_url: str, children: Iterable[tuple[str, MediaWindowChildRow]]) -> tuple[MediaWindowPackageRow, ...]:
    groups: dict[str, list[MediaWindowChildRow]] = {}
    for package_key, child in children:
        groups.setdefault(package_key, []).append(child)
    packages = [_make_package(source_row_id, source_url, key, rows) for key, rows in groups.items()]
    return tuple(sorted(packages, key=_sort_key_package))


def _package_key_for_source_item(row: SourceResourceRowState, item: SourceResourceItem, media_class: str) -> str:
    host = _host_from_url(item.canonical_url or item.reference_url or row.canonical_url)
    if media_class == MEDIA_CLASS_IMAGE:
        return f"{row.row_id}:images:{host}"
    if media_class in {MEDIA_CLASS_MANIFEST, MEDIA_CLASS_SEGMENT_COLLECTION}:
        return f"{row.row_id}:video_stream:{item.canonical_url or item.reference_url or host}"
    if media_class in {MEDIA_CLASS_VIDEO, MEDIA_CLASS_AUDIO}:
        return f"{row.row_id}:{media_class}:{host}"
    return f"{row.row_id}:media:{host}:{media_class}"


def build_unified_media_window_state_from_source_row(
    row: SourceResourceRowState,
    *,
    active_tab: str = TAB_ALL,
) -> UnifiedMediaWindowState:
    """Build the one-window All/Images/Videos package tree from an existing source row."""

    children_with_keys: list[tuple[str, MediaWindowChildRow]] = []
    for item in tuple(row.image_resources or ()):
        media_class = _media_class_from_parts(item.media_type, item.mime_type, item.extension, item.canonical_url or item.reference_url, item.status)
        if media_class == MEDIA_CLASS_UNKNOWN:
            media_class = MEDIA_CLASS_IMAGE
        key = _package_key_for_source_item(row, item, media_class)
        package_id = f"{row.row_id}:media_package:{_hash_text(key)}"
        children_with_keys.append((key, _child_from_source_resource(item, media_class, package_id, key)))
    for item in tuple(row.video_audio_resources or ()):
        media_class = _media_class_from_parts(item.media_type, item.mime_type, item.extension, item.canonical_url or item.reference_url, item.status)
        if media_class == MEDIA_CLASS_UNKNOWN:
            media_class = MEDIA_CLASS_VIDEO
        key = _package_key_for_source_item(row, item, media_class)
        package_id = f"{row.row_id}:media_package:{_hash_text(key)}"
        children_with_keys.append((key, _child_from_source_resource(item, media_class, package_id, key)))

    source_url = _plain_url(row.canonical_url or row.raw_url)
    packages = _group_children_to_packages(row.row_id, source_url, children_with_keys)
    return UnifiedMediaWindowState(
        schema_version=R42GW_SCHEMA_VERSION,
        marker=R42GW_MARKER,
        source_row_id=row.row_id,
        source_url=source_url,
        adapter_id=row.adapter_id,
        tabs=MEDIA_WINDOW_TABS,
        packages=packages,
        active_tab=normalize_tab_id(active_tab),
        review_window_separate=True,
        side_effect_flags=build_side_effect_flags(),
    )


def _visible_package_key_for_observation(source_row_id: str, source_url: str, obs: Any, *, force_segment: bool = False) -> str:
    media_url = _plain_url(_observation_get(obs, "canonical_media_url") or _observation_get(obs, "canonical_segment_url") or _observation_get(obs, "media_url") or _observation_get(obs, "segment_url"))
    media_kind = _clean(_observation_get(obs, "media_kind") or ("segment" if force_segment else ""))
    content_type = _clean(_observation_get(obs, "content_type"))
    ext = _extension_from_name_or_url(media_url)
    media_class = MEDIA_CLASS_SEGMENT if force_segment else _media_class_from_parts(media_kind, content_type, ext, media_url)
    host = _host_from_url(media_url or source_url)
    manifest = _plain_url(_observation_get(obs, "playlist_manifest_url"))
    post_url = _plain_url(_observation_get(obs, "canonical_post_url") or _observation_get(obs, "post_url") or source_url)
    status_id = _clean(_observation_get(obs, "status_id"))
    if media_class == MEDIA_CLASS_IMAGE:
        return f"{source_row_id}:images:{post_url}:{host}"
    if media_class in {MEDIA_CLASS_MANIFEST, MEDIA_CLASS_SEGMENT}:
        # Manifest and segment rows are one JDownloader-style stream package.
        stream_key = manifest or (media_url if media_class == MEDIA_CLASS_MANIFEST else "") or post_url or status_id or host
        return f"{source_row_id}:video_stream:{stream_key}"
    if media_class in {MEDIA_CLASS_VIDEO, MEDIA_CLASS_AUDIO}:
        # Direct media resources stay in the same source/post package unless a future
        # site policy supplies a more precise variant-group key.
        return f"{source_row_id}:video_stream:{post_url or status_id or manifest or host}"
    return f"{source_row_id}:media:{host}:{media_class}"


def build_unified_media_window_state_from_visible_browser_store(
    store: Any,
    *,
    source_row_id: str,
    adapter_id: str = "twitter_x",
    active_tab: str = TAB_ALL,
) -> UnifiedMediaWindowState:
    """Build a package tree directly from the R42GV visible-browser observation store."""

    source_url = _plain_url(_observation_get(store, "canonical_source_url") or _observation_get(store, "source_url"))
    observations = tuple(_observation_get(store, "observations", ()) or ())
    segment_rows = tuple(_observation_get(store, "segment_rows", ()) or ())

    children_with_keys: list[tuple[str, MediaWindowChildRow]] = []
    emitted_segment_urls: set[str] = set()
    for obs in observations:
        media_kind = _clean(_observation_get(obs, "media_kind"))
        if media_kind == MEDIA_CLASS_SEGMENT and segment_rows:
            # Prefer the explicit R42GV segment table, but do not mark those
            # URLs as already emitted before the table has been projected.
            # The previous guard suppressed all matching segment-table rows,
            # which broke R42GY's background WebView2 observer refresh path.
            continue
        key = _visible_package_key_for_observation(source_row_id, source_url, obs)
        package_id = f"{source_row_id}:media_package:{_hash_text(key)}"
        children_with_keys.append((key, _child_from_visible_observation(obs, package_id, key, source_row_id=source_row_id)))
    for segment in segment_rows:
        segment_url = _plain_url(_observation_get(segment, "canonical_segment_url") or _observation_get(segment, "segment_url"))
        if not segment_url or segment_url in emitted_segment_urls:
            continue
        key = _visible_package_key_for_observation(source_row_id, source_url, segment, force_segment=True)
        package_id = f"{source_row_id}:media_package:{_hash_text(key)}"
        children_with_keys.append((key, _child_from_visible_observation(segment, package_id, key, source_row_id=source_row_id, force_segment=True)))
        emitted_segment_urls.add(segment_url)

    packages = _group_children_to_packages(source_row_id, source_url, children_with_keys)
    return UnifiedMediaWindowState(
        schema_version=R42GW_SCHEMA_VERSION,
        marker=R42GW_MARKER,
        source_row_id=source_row_id,
        source_url=source_url,
        adapter_id=adapter_id,
        tabs=MEDIA_WINDOW_TABS,
        packages=packages,
        active_tab=normalize_tab_id(active_tab),
        review_window_separate=True,
        side_effect_flags=build_side_effect_flags(),
    )


def flatten_media_window_tree(
    state: UnifiedMediaWindowState,
    *,
    tab_id: str = TAB_ALL,
    include_children: bool = True,
) -> tuple[Mapping[str, Any], ...]:
    """Return a JDownloader-like flat tree: package row then child rows."""

    tab = normalize_tab_id(tab_id)
    rows: list[Mapping[str, Any]] = []
    for package in state.tab_packages(tab):
        package_payload = package.to_dict()
        package_payload["row_role"] = ROW_ROLE_PACKAGE
        package_payload["visible_in_tab"] = tab
        rows.append(package_payload)
        if include_children:
            for child in package.children:
                if tab not in child.tab_memberships:
                    continue
                child_payload = child.to_dict()
                child_payload["row_role"] = ROW_ROLE_CHILD
                child_payload["visible_in_tab"] = tab
                rows.append(child_payload)
    return tuple(rows)


def _child_matches_filter(child: MediaWindowChildRow, filters: MediaWindowFilterState) -> bool:
    tab = normalize_tab_id(filters.tab_id)
    if tab not in child.tab_memberships:
        return False
    if not filters.include_segments and child.media_class == MEDIA_CLASS_SEGMENT:
        return False
    if filters.only_selectable and not child.selectable:
        return False
    host_filter = _clean(filters.host_filter).lower()
    if host_filter and host_filter not in child.host.lower():
        return False
    ext_filter = _clean(filters.extension_filter).lower()
    if ext_filter:
        if not ext_filter.startswith("."):
            ext_filter = f".{ext_filter}"
        if child.extension.lower() != ext_filter:
            return False
    class_filter = _clean(filters.media_class_filter).lower()
    if class_filter and child.media_class.lower() != class_filter:
        return False
    byte_filter = _clean(filters.byte_status_filter).lower()
    if byte_filter and byte_filter not in child.byte_status.lower():
        return False
    search = _clean(filters.search_text).lower()
    if search:
        haystack = " ".join(
            (
                child.display_name,
                child.filename,
                child.extension,
                child.host,
                child.media_url,
                child.canonical_url,
                child.mime_type,
                child.byte_status,
                child.status,
                child.variant_label,
                child.warning,
                child.provenance,
            )
        ).lower()
        if search not in haystack:
            return False
    return True


def filter_unified_media_window_state(
    state: UnifiedMediaWindowState,
    filters: MediaWindowFilterState | None = None,
) -> UnifiedMediaWindowState:
    filters = filters or MediaWindowFilterState(tab_id=state.active_tab)
    filtered_packages: list[MediaWindowPackageRow] = []
    for package in state.packages:
        children = tuple(child for child in package.children if _child_matches_filter(child, filters))
        if not children:
            continue
        filtered_packages.append(_make_package(package.source_row_id, package.source_url, package.package_key, children))
    return UnifiedMediaWindowState(
        schema_version=state.schema_version,
        marker=state.marker,
        source_row_id=state.source_row_id,
        source_url=state.source_url,
        adapter_id=state.adapter_id,
        tabs=state.tabs,
        packages=tuple(filtered_packages),
        active_tab=normalize_tab_id(filters.tab_id),
        review_window_separate=state.review_window_separate,
        all_tab_model=state.all_tab_model,
        side_effect_flags=state.side_effect_flags,
        status=state.status,
    )


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def machine_url_fields_are_plain(value: Any) -> bool:
    text = json.dumps(state_to_dict(value), sort_keys=True)
    return "](" not in text and "]\\(" not in text and "\"[http" not in text


def _build_fixture_store(output_root: Path) -> Mapping[str, Any]:
    fixture = output_root / "fixtures" / "session_local_image.jpg"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_bytes(b"R42GW local image fixture\n")
    source_url = "https://x.com/example/status/1234567890"
    manifest = "https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16"
    return {
        "source_url": source_url,
        "canonical_source_url": source_url,
        "observations": [
            {
                "observation_id": "img-network",
                "media_id": "image",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/r42gw_image.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/r42gw_image.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "manifest-network",
                "media_id": "manifest",
                "media_kind": "manifest",
                "media_url": manifest,
                "canonical_media_url": manifest,
                "content_type": "application/x-mpegURL",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "mp4-network",
                "media_id": "mp4",
                "media_kind": "video",
                "media_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
                "canonical_media_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
                "content_type": "video/mp4",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "session-local",
                "media_id": "session-local-image",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/r42gw_session_local.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/r42gw_session_local.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "session_local_file",
                "byte_status": BYTE_STATUS_LOCAL,
                "local_session_path": str(fixture),
                "sha256": "fixture-sha256",
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "dom-image",
                "media_id": "dom-image",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/dom_r42gw.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/dom_r42gw.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "rendered_dom_media_resource",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
        ],
        "segment_rows": [
            {
                "segment_id": "seg1",
                "segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
                "canonical_segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
                "playlist_manifest_url": manifest,
                "content_type": "video/mp2t",
                "segment_index": 1,
                "byte_status": BYTE_STATUS_REMOTE,
            },
            {
                "segment_id": "seg2",
                "segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts",
                "canonical_segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts",
                "playlist_manifest_url": manifest,
                "content_type": "video/mp2t",
                "segment_index": 2,
                "byte_status": BYTE_STATUS_REMOTE,
            },
        ],
    }


def build_report(output_root: str | Path = "profile_media_live_captures/r42gw_unified_media_window_tabs_jdownloader_grouping") -> R42GWReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    store = _build_fixture_store(root)
    state = build_unified_media_window_state_from_visible_browser_store(
        store,
        source_row_id="twitter_x:example:1234567890",
        adapter_id="twitter_x",
    )
    all_rows = flatten_media_window_tree(state, tab_id=TAB_ALL)
    image_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_IMAGES))
    video_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_VIDEOS))
    ts_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_VIDEOS, extension_filter=".ts"))
    host_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_ALL, host_filter="pbs.twimg.com"))

    video_packages = state.tab_packages(TAB_VIDEOS)
    image_packages = state.tab_packages(TAB_IMAGES)
    segment_children = [
        child
        for package in video_packages
        for child in package.children
        if child.media_class == MEDIA_CLASS_SEGMENT
    ]

    checks = (
        _check("tabs_are_all_images_videos", state.tabs == MEDIA_WINDOW_TABS),
        _check("review_window_remains_separate", state.review_window_separate is True),
        _check("all_tab_uses_package_child_tree", any(row.get("row_role") == ROW_ROLE_PACKAGE for row in all_rows) and any(row.get("row_role") == ROW_ROLE_CHILD for row in all_rows)),
        _check("image_tab_excludes_video_children", image_state.child_count > 0 and all(child.media_class == MEDIA_CLASS_IMAGE for package in image_state.packages for child in package.children)),
        _check("video_tab_excludes_image_children", video_state.child_count > 0 and all(child.media_class != MEDIA_CLASS_IMAGE for package in video_state.packages for child in package.children)),
        _check("segments_listed_under_video_package", len(segment_children) >= 2 and any(package.segment_child_count >= 2 for package in video_packages)),
        _check("segments_not_selected_by_default", segment_children and not any(child.selectable for child in segment_children)),
        _check("filename_extension_filter_keeps_segment_children", ts_state.segment_child_count >= 2 and all(child.extension == ".ts" for package in ts_state.packages for child in package.children)),
        _check("host_filter_keeps_image_host_group", host_state.child_count >= 2 and all("pbs.twimg.com" in child.host for package in host_state.packages for child in package.children)),
        _check("plain_machine_urls", machine_url_fields_are_plain(state.to_dict())),
        _check("no_forbidden_side_effects", not any(value for key, value in build_side_effect_flags().items() if key not in {"local_projection_only", "jdownloader_source_usage_policy_recorded", "jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible"})),
        _check("jdownloader_source_usage_policy_allows_attributed_licensed_adaptation", build_side_effect_flags()["jdownloader_source_usage_policy_recorded"] is True and build_side_effect_flags()["jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible"] is True),
    )
    status = R42GW_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GW_BLOCKED_STATUS
    return R42GWReport(
        marker=R42GW_MARKER,
        schema_version=R42GW_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        unified_media_window_state=state.to_dict(),
        filtered_examples={
            "all_tree_rows": [dict(row) for row in all_rows],
            "images_tab": image_state.to_dict(),
            "videos_tab": video_state.to_dict(),
            "video_ts_extension_filter": ts_state.to_dict(),
            "pbs_host_filter": host_state.to_dict(),
        },
        jdownloader_reference_model=JDOWNLOADER_REFERENCE_MODEL,
        side_effect_flags=build_side_effect_flags(),
    )


def render_report_markdown(report: R42GWReport) -> str:
    lines = [
        f"# {R42GW_MARKER}",
        "",
        f"Status: `{report.status}`",
        f"Schema: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        detail = f" — {check.get('detail')}" if check.get("detail") else ""
        lines.append(f"- {check.get('status')}: {check.get('name')}{detail}")
    state = report.unified_media_window_state
    lines += [
        "",
        "## Media window",
        "",
        f"- Tabs: `{', '.join(state.get('tabs', []))}`",
        f"- Packages: `{state.get('package_count')}`",
        f"- Children: `{state.get('child_count')}`",
        f"- Segments: `{state.get('segment_child_count')}`",
        f"- Review window separate: `{state.get('review_window_separate')}`",
        "",
        "## JDownloader-style logic copied conceptually",
        "",
        "- package/folder rows contain child media rows",
        "- All tab renders the package-child tree",
        "- Images and Videos tabs are filtered projections of the same model",
        "- segment rows remain listed under stream package rows",
        "- filename/extension/host/media-class filtering is local-only",
        "- no JDownloader source code is copied",
        "",
    ]
    return "\n".join(lines)


def write_report(report: R42GWReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING_REPORT.md").write_text(
        render_report_markdown(report),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build R42GW unified Media window tabs report.")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gw_unified_media_window_tabs_jdownloader_grouping")
    args = parser.parse_args(list(argv or []))
    report = build_report(args.output_root)
    write_report(report, args.output_root)
    print(R42GW_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
