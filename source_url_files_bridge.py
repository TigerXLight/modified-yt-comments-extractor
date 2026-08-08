from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from capture_media_discovery import MediaDiscoveryResult, MediaResource, discover_media_resources_from_html
from source_url_media_ui_contract import (
    ArchiveIconStatus,
    ArchiveStatusIcon,
    SourceUrlResolvedRow,
    SourceUrlResourceChoice,
    SourceUrlUiRoadmapState,
    UrlResourceKind,
)


SOURCE_URL_FILES_BRIDGE_SCHEMA_VERSION = "source_url_files_bridge_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _resource_kind(resource: MediaResource) -> UrlResourceKind:
    kind = str(resource.kind)
    if kind == "audio":
        return UrlResourceKind.AUDIO
    if kind == "video":
        return UrlResourceKind.VIDEO
    if kind in {"caption", "subtitle", "track"}:
        return UrlResourceKind.CAPTION
    return UrlResourceKind.IMAGE


@dataclass(frozen=True)
class SourceFilesHierarchyRow:
    row_id: str
    display_name: str
    source_row_id: str
    resource_choice_id: str
    role: str
    active_media: bool = False
    active_transcript: bool = False
    session_only_detach: bool = True
    local_path_included: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceUrlFilesBridgeState:
    bridge_id: str
    source_rows: tuple[Mapping[str, Any], ...]
    files_rows: tuple[SourceFilesHierarchyRow, ...]
    selected_download_choice_ids: tuple[str, ...]
    injected_choice_ids: tuple[str, ...]
    clear_editor_deletes_file: bool = False
    transcript_replacement_deletes_previous: bool = False
    audio_playback_requires_transcript: bool = False
    network_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    schema_version: str = SOURCE_URL_FILES_BRIDGE_SCHEMA_VERSION

    @property
    def source_row_count(self) -> int:
        return len(self.source_rows)

    @property
    def files_row_count(self) -> int:
        return len(self.files_rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["source_row_count"] = self.source_row_count
        data["files_row_count"] = self.files_row_count
        data["selected_download_count"] = len(self.selected_download_choice_ids)
        data["injected_choice_count"] = len(self.injected_choice_ids)
        return data


def _choice_from_media_resource(resource: MediaResource) -> SourceUrlResourceChoice:
    label = resource.display_name or resource.url.rsplit("/", 1)[-1] or resource.resource_id
    return SourceUrlResourceChoice(
        choice_id=resource.resource_id,
        display_name=label,
        kind=_resource_kind(resource),
        source_url=resource.url,
        selected_for_download=False,
        inject_into_transcript_editor=False,
        auto_download_after_inject_tick=False,
        duration_label=str(resource.duration_seconds or "") or None,
        bitrate_label=str(resource.bitrate or "") or None,
        resolution_label=resource.resolution or None,
        thumbnail_ref=resource.url if resource.kind == "image" else resource.final_url,
        hover_preview_gif_future=resource.kind == "video",
        stored_in_files_after_get=False,
    )


def build_source_url_files_bridge_state(
    *,
    urls: Sequence[str],
    fixture_html_by_url: Mapping[str, str] | None = None,
    selected_download_choice_ids: Iterable[str] = (),
    injected_choice_ids: Iterable[str] = (),
) -> SourceUrlFilesBridgeState:
    selected = tuple(sorted(set(selected_download_choice_ids)))
    injected = tuple(sorted(set(injected_choice_ids)))
    rows: list[SourceUrlResolvedRow] = []
    files_rows: list[SourceFilesHierarchyRow] = []
    fixture_map = dict(fixture_html_by_url or {})
    for ordinal, url in enumerate(urls, start=1):
        discovery: MediaDiscoveryResult | None = None
        if url in fixture_map:
            discovery = discover_media_resources_from_html(fixture_map[url], source_url=url)
        choices = tuple(_choice_from_media_resource(resource) for resource in (discovery.resources if discovery else ()))
        if not choices:
            choices = (
                SourceUrlResourceChoice(
                    choice_id=f"source_{ordinal}_article_text",
                    display_name="Readable/article text",
                    kind=UrlResourceKind.ARTICLE_TEXT,
                    source_url=url,
                ),
            )
        updated_choices = tuple(
            SourceUrlResourceChoice(
                choice_id=choice.choice_id,
                display_name=choice.display_name,
                kind=choice.kind,
                source_url=choice.source_url,
                inject_into_transcript_editor=choice.choice_id in injected,
                selected_for_download=choice.choice_id in selected,
                auto_download_after_inject_tick=choice.auto_download_after_inject_tick,
                duration_label=choice.duration_label,
                bitrate_label=choice.bitrate_label,
                resolution_label=choice.resolution_label,
                local_file_id=f"file_{choice.choice_id}" if choice.choice_id in injected else None,
                thumbnail_ref=choice.thumbnail_ref,
                hover_preview_gif_future=choice.hover_preview_gif_future,
                stored_in_files_after_get=choice.choice_id in injected,
            )
            for choice in choices
        )
        row = SourceUrlResolvedRow(
            source_url=url,
            page_title="Resolved page title pending",
            platform_label="Local fixture/source URL",
            resource_choices=updated_choices,
            archive_icons=(
                ArchiveStatusIcon("wayback", ArchiveIconStatus.UNKNOWN),
                ArchiveStatusIcon("archive_today", ArchiveIconStatus.UNKNOWN),
            ),
        )
        rows.append(row)
        for choice in updated_choices:
            if choice.inject_into_transcript_editor:
                files_rows.append(
                    SourceFilesHierarchyRow(
                        row_id=f"files_{choice.choice_id}",
                        display_name=choice.display_name.rsplit("/", 1)[-1],
                        source_row_id=f"source_row_{ordinal}",
                        resource_choice_id=choice.choice_id,
                        role=choice.kind.value,
                        active_media=choice.kind in {UrlResourceKind.AUDIO, UrlResourceKind.VIDEO},
                        active_transcript=choice.kind in {UrlResourceKind.TRANSCRIPT, UrlResourceKind.CAPTION},
                    )
                )
    data_rows = tuple(row.to_dict() for row in rows)
    return SourceUrlFilesBridgeState(
        bridge_id="source_url_files_bridge_" + _sha16((data_rows, selected, injected)),
        source_rows=data_rows,
        files_rows=tuple(files_rows),
        selected_download_choice_ids=selected,
        injected_choice_ids=injected,
    )


def build_default_source_url_files_bridge_state() -> SourceUrlFilesBridgeState:
    url = "https://example.invalid/story"
    html = """
    <html><body>
      <img src="/image.jpg" alt="fixture">
      <video src="/video.mp4" poster="/poster.jpg"><track src="/captions.vtt" kind="subtitles"></video>
      <audio src="/audio.m4a"></audio>
    </body></html>
    """
    preview = discover_media_resources_from_html(html, source_url=url)
    choice_ids = tuple(resource.resource_id for resource in preview.resources)
    return build_source_url_files_bridge_state(
        urls=(url,),
        fixture_html_by_url={url: html},
        selected_download_choice_ids=choice_ids[:1],
        injected_choice_ids=choice_ids[1:3],
    )


def validate_source_url_files_bridge_state(state: SourceUrlFilesBridgeState | Mapping[str, Any]) -> tuple[str, ...]:
    data = state.to_dict() if hasattr(state, "to_dict") else dict(state)
    errors: list[str] = []
    if data.get("clear_editor_deletes_file", True):
        errors.append("clear_editor_must_not_delete_file")
    if data.get("transcript_replacement_deletes_previous", True):
        errors.append("transcript_replacement_must_preserve_previous_file")
    if data.get("audio_playback_requires_transcript", True):
        errors.append("audio_playback_must_not_require_transcript")
    for key in ("network_performed", "download_performed", "file_move_performed"):
        if data.get(key, False):
            errors.append(f"unsafe_flag_true:{key}")
    return tuple(errors)


def source_url_files_bridge_state_to_json(state: SourceUrlFilesBridgeState) -> str:
    return _stable_json(state.to_dict(), pretty=True)
