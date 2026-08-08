from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Sequence


class UrlResourceKind(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    GIF = "gif"
    TRANSCRIPT = "transcript"
    CAPTION = "caption"
    ARTICLE_TEXT = "article_text"
    COMMENTS = "comments"
    LIVECHAT = "livechat"
    ARCHIVE_STATUS = "archive_status"


class ArchiveIconStatus(str, Enum):
    ONLINE_ALREADY_SAVED = "green_online_already_saved"
    NOT_SAVED_ONLINE = "red_not_saved_online"
    UNKNOWN = "unknown"
    CHALLENGE_OR_MANUAL_REQUIRED = "challenge_or_manual_required"
    CHECK_DISABLED = "check_disabled"


@dataclass(frozen=True)
class SourceUrlResourceChoice:
    choice_id: str
    display_name: str
    kind: UrlResourceKind
    source_url: str
    inject_into_transcript_editor: bool = False
    selected_for_download: bool = False
    auto_download_after_inject_tick: bool = False
    duration_label: str | None = None
    bitrate_label: str | None = None
    resolution_label: str | None = None
    local_file_id: str | None = None
    thumbnail_ref: str | None = None
    hover_preview_gif_future: bool = False
    stored_in_files_after_get: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(frozen=True)
class ArchiveStatusIcon:
    provider_id: str
    status: ArchiveIconStatus
    last_saved_label: str | None = None
    archive_url: str | None = None
    automatic_check_enabled: bool = True
    submit_requires_explicit_user_action: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class SourceUrlResolvedRow:
    source_url: str
    page_title: str
    platform_label: str
    resource_choices: tuple[SourceUrlResourceChoice, ...] = field(default_factory=tuple)
    archive_icons: tuple[ArchiveStatusIcon, ...] = field(default_factory=tuple)
    comments_dropdown_enabled: bool = True
    livechat_dropdown_enabled: bool = True
    screenshot_checkbox_enabled: bool = True
    source_url_enter_submits: bool = True
    no_youtube_specific_button: bool = True

    def selected_downloads(self) -> tuple[SourceUrlResourceChoice, ...]:
        return tuple(choice for choice in self.resource_choices if choice.selected_for_download)

    def injected_choices(self) -> tuple[SourceUrlResourceChoice, ...]:
        return tuple(choice for choice in self.resource_choices if choice.inject_into_transcript_editor)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_url": self.source_url,
            "page_title": self.page_title,
            "platform_label": self.platform_label,
            "resource_choice_count": len(self.resource_choices),
            "selected_download_count": len(self.selected_downloads()),
            "injected_choice_count": len(self.injected_choices()),
            "resource_choices": [choice.to_dict() for choice in self.resource_choices],
            "archive_icons": [icon.to_dict() for icon in self.archive_icons],
            "comments_dropdown_enabled": self.comments_dropdown_enabled,
            "livechat_dropdown_enabled": self.livechat_dropdown_enabled,
            "screenshot_checkbox_enabled": self.screenshot_checkbox_enabled,
            "source_url_enter_submits": self.source_url_enter_submits,
            "no_youtube_specific_button": self.no_youtube_specific_button,
        }


@dataclass(frozen=True)
class FilesSectionOrderingRule:
    injected_files_first: bool = True
    newest_added_files_next: bool = True
    sort_by_available: bool = True
    clear_editor_does_not_delete_file: bool = True
    imported_replacement_keeps_previous_file: bool = True
    audio_can_play_without_transcript: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SourceUrlUiRoadmapState:
    resolved_rows: tuple[SourceUrlResolvedRow, ...]
    files_ordering_rule: FilesSectionOrderingRule = field(default_factory=FilesSectionOrderingRule)
    image_window_select_all: bool = True
    image_window_clear_all: bool = True
    video_window_select_all: bool = True
    video_window_clear_all: bool = True
    media_window_download_button: bool = True
    media_window_cancel_button: bool = True
    waveform_subtitle_timing_future: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "resolved_row_count": len(self.resolved_rows),
            "download_selection_count": sum(len(row.selected_downloads()) for row in self.resolved_rows),
            "injection_selection_count": sum(len(row.injected_choices()) for row in self.resolved_rows),
            "resolved_rows": [row.to_dict() for row in self.resolved_rows],
            "files_ordering_rule": self.files_ordering_rule.to_dict(),
            "image_window_select_all": self.image_window_select_all,
            "image_window_clear_all": self.image_window_clear_all,
            "video_window_select_all": self.video_window_select_all,
            "video_window_clear_all": self.video_window_clear_all,
            "media_window_download_button": self.media_window_download_button,
            "media_window_cancel_button": self.media_window_cancel_button,
            "waveform_subtitle_timing_future": self.waveform_subtitle_timing_future,
        }


def build_example_youtube_source_url_row(url: str) -> SourceUrlResolvedRow:
    return SourceUrlResolvedRow(
        source_url=url,
        page_title="Special DJ by TAKU INOUE",
        platform_label="YouTube",
        resource_choices=(
            SourceUrlResourceChoice(
                choice_id="special_dj_audio_128k_aac",
                display_name="Special DJ by TAKU INOUE (128kbit_AAC).m4a",
                kind=UrlResourceKind.AUDIO,
                source_url=url,
                inject_into_transcript_editor=False,
                selected_for_download=False,
                auto_download_after_inject_tick=True,
                bitrate_label="128kbit_AAC",
            ),
            SourceUrlResourceChoice(
                choice_id="special_dj_video_1080p_h264_aac",
                display_name="Special DJ by TAKU INOUE (1080p_25fps_H264-128kbit_AAC).mp4",
                kind=UrlResourceKind.VIDEO,
                source_url=url,
                selected_for_download=True,
                duration_label="unknown_until_discovered",
                resolution_label="1080p_25fps_H264",
                hover_preview_gif_future=True,
            ),
            SourceUrlResourceChoice(
                choice_id="special_dj_transcript",
                display_name="Special DJ by TAKU INOUE transcript/captions",
                kind=UrlResourceKind.TRANSCRIPT,
                source_url=url,
                inject_into_transcript_editor=True,
                stored_in_files_after_get=True,
            ),
        ),
        archive_icons=(
            ArchiveStatusIcon("wayback", ArchiveIconStatus.UNKNOWN, automatic_check_enabled=True),
            ArchiveStatusIcon("archive_today", ArchiveIconStatus.UNKNOWN, automatic_check_enabled=True),
        ),
    )


def build_default_source_url_ui_roadmap_state(urls: Sequence[str]) -> SourceUrlUiRoadmapState:
    rows = []
    for url in urls:
        if "youtube.com" in url or "youtu.be" in url:
            rows.append(build_example_youtube_source_url_row(url))
        else:
            rows.append(
                SourceUrlResolvedRow(
                    source_url=url,
                    page_title="Resolved page title pending",
                    platform_label="Generic web",
                    resource_choices=(
                        SourceUrlResourceChoice("generic_article_text", "Readable/article text", UrlResourceKind.ARTICLE_TEXT, url),
                        SourceUrlResourceChoice("generic_screenshot", "Full-page screenshot", UrlResourceKind.IMAGE, url),
                    ),
                    archive_icons=(
                        ArchiveStatusIcon("wayback", ArchiveIconStatus.UNKNOWN),
                        ArchiveStatusIcon("archive_today", ArchiveIconStatus.UNKNOWN),
                    ),
                )
            )
    return SourceUrlUiRoadmapState(resolved_rows=tuple(rows))
