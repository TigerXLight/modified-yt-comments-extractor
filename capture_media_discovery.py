from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin, urlsplit

from capture_status import DRM_NONE_DETECTED, DRM_UNKNOWN


MEDIA_RESOURCE_KIND_VIDEO = "video"
MEDIA_RESOURCE_KIND_AUDIO = "audio"
MEDIA_RESOURCE_KIND_IMAGE = "image"
MEDIA_RESOURCE_KIND_SOURCE = "source"
MEDIA_RESOURCE_KIND_FRAME = "frame"
MEDIA_RESOURCE_KIND_MANIFEST = "manifest"
MEDIA_RESOURCE_KIND_REQUEST = "request"
MEDIA_RESOURCE_KIND_BLOB = "blob"

MEDIA_MANIFEST_HLS = "hls"
MEDIA_MANIFEST_DASH = "dash"

MEDIA_DISCOVERY_DOM = "dom"
MEDIA_DISCOVERY_POSTER = "poster"
MEDIA_DISCOVERY_SRCSET = "srcset"
MEDIA_DISCOVERY_MANIFEST = "manifest"
MEDIA_DISCOVERY_REQUEST_LOG = "request_log"
MEDIA_DISCOVERY_PLAYBACK_EVENT = "playback_event"

MEDIA_DISCOVERY_SCOPE = (
    "local supplied-HTML/request-log media discovery only; no fetch, playback automation, "
    "download, archive, provider, credential, scraping, external process, or GUI behavior"
)


@dataclass(frozen=True)
class MediaResource:
    resource_id: str
    kind: str
    url: str
    source_tag: str
    mime_type: str = ""
    display_name: str = ""
    downloadable: bool = True
    requires_playback: bool = False
    drm_status: str = DRM_UNKNOWN
    warnings: tuple[str, ...] = ()
    discovery_methods: tuple[str, ...] = ()
    selector: str = ""
    frame_reference: str = ""
    request_reference: str = ""
    final_url: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    bitrate: int = 0
    resolution: str = ""
    codec: str = ""
    container: str = ""
    language: str = ""
    manifest_kind: str = ""
    presentation_id: str = ""
    signed_url: bool = False
    expiry_hint: str = ""
    component_role: str = ""
    skipped_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bitrate": self.bitrate,
            "codec": self.codec,
            "component_role": self.component_role,
            "container": self.container,
            "discovery_methods": list(self.discovery_methods),
            "display_name": self.display_name,
            "downloadable": self.downloadable,
            "drm_status": self.drm_status,
            "duration_seconds": self.duration_seconds,
            "expiry_hint": self.expiry_hint,
            "final_url": self.final_url,
            "frame_reference": self.frame_reference,
            "height": self.height,
            "kind": self.kind,
            "language": self.language,
            "manifest_kind": self.manifest_kind,
            "mime_type": self.mime_type,
            "presentation_id": self.presentation_id,
            "request_reference": self.request_reference,
            "requires_playback": self.requires_playback,
            "resolution": self.resolution,
            "resource_id": self.resource_id,
            "selector": self.selector,
            "signed_url": self.signed_url,
            "skipped_reason": self.skipped_reason,
            "source_tag": self.source_tag,
            "url": self.url,
            "warnings": list(self.warnings),
            "width": self.width,
        }


@dataclass(frozen=True)
class MediaDiscoveryResult:
    source_url: str
    resources: tuple[MediaResource, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = MEDIA_DISCOVERY_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "resources": [resource.to_dict() for resource in self.resources],
            "scope": self.scope,
            "source_url": self.source_url,
            "warnings": list(self.warnings),
        }


class _MediaDiscoveryParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.resources: list[MediaResource] = []
        self.warnings: list[str] = []
        self._picture_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if lowered == "picture":
            self._picture_depth += 1
        if lowered in {"video", "audio", "img", "source", "iframe", "embed", "object"}:
            self._record_media_tag(lowered, attr_map)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "picture":
            self._picture_depth = max(0, self._picture_depth - 1)

    def _record_media_tag(self, tag_name: str, attrs: dict[str, str]) -> None:
        src = attrs.get("src", "") or attrs.get("data", "")
        mime_type = attrs.get("type", "")
        if tag_name == "source" and not src:
            src = _first_srcset_url(attrs.get("srcset", ""))
        if tag_name == "img" and not src:
            src = attrs.get("data-src", "") or _first_srcset_url(attrs.get("srcset", ""))
        if tag_name == "video" and attrs.get("poster"):
            self.resources.append(
                _build_media_resource(
                    kind=MEDIA_RESOURCE_KIND_IMAGE,
                    source_url=self.source_url,
                    src=attrs.get("poster", ""),
                    source_tag="poster",
                    mime_type="image/*",
                    display_name="video poster",
                    discovery_methods=(MEDIA_DISCOVERY_POSTER,),
                    drm_status=DRM_NONE_DETECTED,
                )
            )
        if src.startswith("blob:") or attrs.get("data-fixture") in {"blob", "mse"}:
            self.resources.append(
                _build_blob_resource(
                    source_url=self.source_url,
                    src=src or attrs.get("data-fixture", ""),
                    source_tag=tag_name,
                    mime_type=mime_type,
                )
            )
            return
        if not src:
            if tag_name in {"video", "audio"}:
                self.warnings.append(f"{tag_name} element has no direct src; playback discovery may be required.")
            return
        kind = _kind_for_tag(tag_name, src, mime_type, self._picture_depth > 0)
        manifest_kind = _manifest_kind(src, mime_type)
        methods = [MEDIA_DISCOVERY_DOM]
        if manifest_kind:
            kind = MEDIA_RESOURCE_KIND_MANIFEST
            methods.append(MEDIA_DISCOVERY_MANIFEST)
        self.resources.append(
            _build_media_resource(
                kind=kind,
                source_url=self.source_url,
                src=src,
                source_tag=tag_name,
                mime_type=mime_type,
                display_name=attrs.get("alt", "") or attrs.get("title", ""),
                downloadable=not manifest_kind,
                requires_playback=_bool_attr(attrs.get("data-playback-required", "")),
                drm_status=DRM_NONE_DETECTED,
                discovery_methods=tuple(methods),
                selector=attrs.get("id", "") or attrs.get("class", ""),
                frame_reference=attrs.get("title", "") if tag_name in {"iframe", "embed", "object"} else "",
                width=_int_or_zero(attrs.get("width", "")),
                height=_int_or_zero(attrs.get("height", "")),
                duration_seconds=_float_or_zero(attrs.get("data-duration", "")),
                bitrate=_int_or_zero(attrs.get("data-bitrate", "")),
                resolution=attrs.get("data-resolution", ""),
                codec=attrs.get("data-codec", ""),
                container=attrs.get("data-container", ""),
                language=attrs.get("srclang", "") or attrs.get("data-language", ""),
                manifest_kind=manifest_kind,
                presentation_id=attrs.get("data-presentation-id", ""),
                signed_url=_bool_attr(attrs.get("data-signed-url", "")),
                expiry_hint=attrs.get("data-expiry-hint", ""),
                component_role=attrs.get("data-component-role", ""),
            )
        )


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _bool_attr(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_zero(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _first_srcset_url(value: str) -> str:
    first = str(value or "").split(",", 1)[0].strip()
    return first.split(" ", 1)[0].strip()


def _kind_for_tag(tag_name: str, src: str, mime_type: str, in_picture: bool) -> str:
    if tag_name == "video":
        return MEDIA_RESOURCE_KIND_VIDEO
    if tag_name == "audio":
        return MEDIA_RESOURCE_KIND_AUDIO
    if tag_name == "img" or in_picture:
        return MEDIA_RESOURCE_KIND_IMAGE
    if tag_name in {"iframe", "embed", "object"}:
        return MEDIA_RESOURCE_KIND_FRAME
    lowered = f"{src} {mime_type}".lower()
    if "audio" in lowered:
        return MEDIA_RESOURCE_KIND_AUDIO
    if "image" in lowered:
        return MEDIA_RESOURCE_KIND_IMAGE
    if "video" in lowered:
        return MEDIA_RESOURCE_KIND_VIDEO
    return MEDIA_RESOURCE_KIND_SOURCE


def _manifest_kind(src: str, mime_type: str) -> str:
    lowered = f"{src} {mime_type}".lower()
    if ".m3u8" in lowered or "mpegurl" in lowered:
        return MEDIA_MANIFEST_HLS
    if ".mpd" in lowered or "dash+xml" in lowered:
        return MEDIA_MANIFEST_DASH
    return ""


def _resource_id(kind: str, url: str, method: str = "") -> str:
    digest = hashlib.sha256(f"{kind}:{url}:{method}".encode("utf-8")).hexdigest()[:16]
    return f"media_{digest}"


def _build_blob_resource(
    *,
    source_url: str,
    src: str,
    source_tag: str,
    mime_type: str = "",
) -> MediaResource:
    return _build_media_resource(
        kind=MEDIA_RESOURCE_KIND_BLOB,
        source_url=source_url,
        src=src,
        source_tag=source_tag,
        mime_type=mime_type,
        downloadable=False,
        requires_playback=True,
        drm_status=DRM_UNKNOWN,
        discovery_methods=(MEDIA_DISCOVERY_DOM,),
        skipped_reason="blob_or_mediasource_not_directly_downloadable",
        warnings=("Blob/MediaSource media requires manifest/request observation or rendered citation recording.",),
    )


def _build_media_resource(
    *,
    kind: str,
    source_url: str,
    src: str,
    source_tag: str,
    mime_type: str = "",
    display_name: str = "",
    downloadable: bool = True,
    requires_playback: bool = False,
    drm_status: str = DRM_UNKNOWN,
    warnings: tuple[str, ...] = (),
    discovery_methods: tuple[str, ...] = (MEDIA_DISCOVERY_DOM,),
    selector: str = "",
    frame_reference: str = "",
    request_reference: str = "",
    width: int = 0,
    height: int = 0,
    duration_seconds: float = 0.0,
    bitrate: int = 0,
    resolution: str = "",
    codec: str = "",
    container: str = "",
    language: str = "",
    manifest_kind: str = "",
    presentation_id: str = "",
    signed_url: bool = False,
    expiry_hint: str = "",
    component_role: str = "",
    skipped_reason: str = "",
) -> MediaResource:
    resolved_url = urljoin(source_url, src) if src else ""
    return MediaResource(
        resource_id=_resource_id(kind, resolved_url, ",".join(discovery_methods)),
        kind=kind,
        url=resolved_url,
        source_tag=source_tag,
        mime_type=mime_type,
        display_name=_normalize_text(display_name),
        downloadable=downloadable,
        requires_playback=requires_playback,
        drm_status=drm_status,
        warnings=warnings,
        discovery_methods=discovery_methods,
        selector=selector,
        frame_reference=frame_reference,
        request_reference=request_reference,
        final_url=resolved_url,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        bitrate=bitrate,
        resolution=resolution,
        codec=codec,
        container=container,
        language=language,
        manifest_kind=manifest_kind,
        presentation_id=presentation_id,
        signed_url=signed_url,
        expiry_hint=expiry_hint,
        component_role=component_role,
        skipped_reason=skipped_reason,
    )


def discover_media_resources_from_html(html: str, *, source_url: str = "") -> MediaDiscoveryResult:
    parser = _MediaDiscoveryParser(source_url=source_url)
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; media discovery may be partial.")
    warnings.extend(parser.warnings)
    resources = _dedupe_resources(parser.resources)
    if not resources:
        warnings.append("No media resources found in supplied HTML.")
    return MediaDiscoveryResult(
        source_url=source_url,
        resources=resources,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def discover_media_resources_from_request_log(
    entries: Iterable[Mapping[str, Any]],
    *,
    source_url: str = "",
) -> MediaDiscoveryResult:
    resources: list[MediaResource] = []
    for index, entry in enumerate(entries, start=1):
        url = str(entry.get("url") or "")
        mime_type = str(entry.get("mime_type") or entry.get("content_type") or "")
        if not url:
            continue
        kind = _kind_for_request(url, mime_type)
        manifest_kind = _manifest_kind(url, mime_type)
        if manifest_kind:
            kind = MEDIA_RESOURCE_KIND_MANIFEST
        resources.append(
            _build_media_resource(
                kind=kind,
                source_url=source_url,
                src=url,
                source_tag="request",
                mime_type=mime_type,
                downloadable=kind not in {MEDIA_RESOURCE_KIND_MANIFEST, MEDIA_RESOURCE_KIND_BLOB},
                requires_playback=True,
                drm_status=DRM_NONE_DETECTED,
                discovery_methods=(MEDIA_DISCOVERY_REQUEST_LOG,),
                request_reference=str(entry.get("request_id") or f"request-{index}"),
                duration_seconds=_float_or_zero(entry.get("duration_seconds", 0)),
                bitrate=_int_or_zero(entry.get("bitrate", 0)),
                resolution=str(entry.get("resolution") or ""),
                codec=str(entry.get("codec") or ""),
                container=str(entry.get("container") or ""),
                language=str(entry.get("language") or ""),
                manifest_kind=manifest_kind,
                presentation_id=str(entry.get("presentation_id") or ""),
                signed_url=_bool_attr(str(entry.get("signed_url") or "")),
                expiry_hint=str(entry.get("expiry_hint") or ""),
                component_role=str(entry.get("component_role") or ""),
            )
        )
    warnings = () if resources else ("No media resources found in supplied request log.",)
    return MediaDiscoveryResult(source_url=source_url, resources=_dedupe_resources(resources), warnings=warnings)


def discover_media_resources_from_playback_events(
    events: Iterable[Mapping[str, Any]],
    *,
    source_url: str = "",
) -> MediaDiscoveryResult:
    resources: list[MediaResource] = []
    for index, event in enumerate(events, start=1):
        url = str(event.get("url") or "")
        if not url:
            continue
        resources.extend(
            discover_media_resources_from_request_log(
                (
                    {
                        **dict(event),
                        "request_id": event.get("event_id") or f"playback-{index}",
                    },
                ),
                source_url=source_url,
            ).resources
        )
    resources = tuple(
        MediaResource(
            **{
                **resource.to_dict(),
                "discovery_methods": (MEDIA_DISCOVERY_PLAYBACK_EVENT,),
                "warnings": tuple(resource.warnings),
            }
        )
        for resource in _dedupe_resources(resources)
    )
    warnings = () if resources else ("No media resources found in supplied playback event log.",)
    return MediaDiscoveryResult(source_url=source_url, resources=resources, warnings=warnings)


def _kind_for_request(url: str, mime_type: str) -> str:
    lowered = f"{url} {mime_type}".lower()
    if lowered.startswith("blob:") or "mediasource" in lowered:
        return MEDIA_RESOURCE_KIND_BLOB
    if "audio" in lowered or re.search(r"\.(m4a|mp3|wav|aac)(\?|$)", lowered):
        return MEDIA_RESOURCE_KIND_AUDIO
    if "image" in lowered or re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", lowered):
        return MEDIA_RESOURCE_KIND_IMAGE
    if "video" in lowered or re.search(r"\.(mp4|webm|mov|m4v)(\?|$)", lowered):
        return MEDIA_RESOURCE_KIND_VIDEO
    return MEDIA_RESOURCE_KIND_REQUEST


def _dedupe_resources(resources: Iterable[MediaResource]) -> tuple[MediaResource, ...]:
    deduped: dict[tuple[str, str], MediaResource] = {}
    for resource in resources:
        key = (resource.kind, resource.url)
        if key not in deduped:
            deduped[key] = resource
    return tuple(deduped.values())
