from __future__ import annotations

import hashlib
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from capture_status import DRM_NONE_DETECTED, DRM_UNKNOWN


MEDIA_RESOURCE_KIND_VIDEO = "video"
MEDIA_RESOURCE_KIND_AUDIO = "audio"
MEDIA_RESOURCE_KIND_IMAGE = "image"
MEDIA_RESOURCE_KIND_SOURCE = "source"
MEDIA_RESOURCE_KIND_BLOB = "blob"

MEDIA_DISCOVERY_SCOPE = (
    "local supplied-HTML media discovery only; no fetch, playback automation, download, "
    "archive, provider, credential, scraping, external process, or GUI behavior"
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "downloadable": self.downloadable,
            "drm_status": self.drm_status,
            "kind": self.kind,
            "mime_type": self.mime_type,
            "requires_playback": self.requires_playback,
            "resource_id": self.resource_id,
            "source_tag": self.source_tag,
            "url": self.url,
            "warnings": list(self.warnings),
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if lowered in {"video", "audio", "img", "source"}:
            self._record_media_tag(lowered, attr_map)

    def _record_media_tag(self, tag_name: str, attrs: dict[str, str]) -> None:
        src = attrs.get("src", "")
        mime_type = attrs.get("type", "")
        if src.startswith("blob:") or attrs.get("data-fixture") in {"blob", "mse"}:
            resource = _build_media_resource(
                kind=MEDIA_RESOURCE_KIND_BLOB,
                source_url=self.source_url,
                src=src or attrs.get("data-fixture", ""),
                source_tag=tag_name,
                mime_type=mime_type,
                downloadable=False,
                requires_playback=True,
                drm_status=DRM_UNKNOWN,
                warnings=("Blob/MediaSource media requires a future playback-observation route.",),
            )
            self.resources.append(resource)
            return
        if not src:
            if tag_name in {"video", "audio"}:
                self.warnings.append(f"{tag_name} element has no direct src; playback discovery may be required.")
            return
        kind = {
            "video": MEDIA_RESOURCE_KIND_VIDEO,
            "audio": MEDIA_RESOURCE_KIND_AUDIO,
            "img": MEDIA_RESOURCE_KIND_IMAGE,
            "source": MEDIA_RESOURCE_KIND_SOURCE,
        }.get(tag_name, MEDIA_RESOURCE_KIND_SOURCE)
        self.resources.append(
            _build_media_resource(
                kind=kind,
                source_url=self.source_url,
                src=src,
                source_tag=tag_name,
                mime_type=mime_type,
                display_name=attrs.get("alt", "") or attrs.get("title", ""),
                drm_status=DRM_NONE_DETECTED,
            )
        )


def _resource_id(kind: str, url: str) -> str:
    digest = hashlib.sha256(f"{kind}:{url}".encode("utf-8")).hexdigest()[:16]
    return f"media_{digest}"


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
) -> MediaResource:
    resolved_url = urljoin(source_url, src) if src else ""
    return MediaResource(
        resource_id=_resource_id(kind, resolved_url),
        kind=kind,
        url=resolved_url,
        source_tag=source_tag,
        mime_type=mime_type,
        display_name=display_name,
        downloadable=downloadable,
        requires_playback=requires_playback,
        drm_status=drm_status,
        warnings=warnings,
    )


def discover_media_resources_from_html(html: str, *, source_url: str = "") -> MediaDiscoveryResult:
    parser = _MediaDiscoveryParser(source_url=source_url)
    warnings: list[str] = []
    try:
        parser.feed(html or "")
    except Exception:
        warnings.append("HTML parser reported a non-secret parsing issue; media discovery may be partial.")
    warnings.extend(parser.warnings)
    if not parser.resources:
        warnings.append("No media resources found in supplied HTML.")
    return MediaDiscoveryResult(
        source_url=source_url,
        resources=tuple(parser.resources),
        warnings=tuple(dict.fromkeys(warnings)),
    )
