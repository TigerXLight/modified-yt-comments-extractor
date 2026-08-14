from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from source_resource_state import SourceResourceRowState


TWITTER_COMPACT_MODES = ("Post", "Thread")
TWITTER_SCREENSHOT_MODES = ("None", "Post", "Both")
TWITTER_SCREENSHOT_MODE_VALUES = ("none", "post", "both")
TWITTER_COMPACT_ICON_ASSET = "assets/ytce_x_icon.png"
TWITTER_COMPACT_SETTING_KEYS = (
    "post",
    "threads",
    "media",
    "show_type_dropdown",
    "screenshot_mode",
)
REMOVED_TWITTER_BUTTON_LABELS = (
    "Twitter/X Local Export",
    "Add Review Draft",
    "Review Flow Summary",
)


@dataclass(frozen=True)
class TwitterCompactRowState:
    row_id: str
    source_url: str
    adapter_id: str
    display_title: str = "Twitter/X post"
    preview_text: str = ""
    compact_pattern: str = "youtube_v19_parity"
    compact_row_height: int = 72
    compact_control_width: int = 95
    compact_control_height: int = 28
    checkbox_position: str = "x4_y2_12x12_youtube_parity"
    checkbox_behavior: str = "checked_enables_inline_post_thread_selector"
    show_type_dropdown_setting_label: str = "Show type dropdown on X/Twitter source row"
    show_type_dropdown_default: bool = True
    settings_treatment: str = "compact_cog_inside_row_settings"
    delete_treatment: str = "youtube_compact_corner_remove_x"
    dropdown_behavior: str = "youtube_inline_menu_style"
    icon_style: str = "x_twitter_dark_large_source_downscaled"
    icon_asset: str = TWITTER_COMPACT_ICON_ASSET
    icon_position: str = "final_user_selected_post_w95_thread_w97_refresh_rebuild"
    dropdown_options: tuple[str, ...] = TWITTER_COMPACT_MODES
    screenshot_options: tuple[str, ...] = TWITTER_SCREENSHOT_MODES
    screenshot_option_values: tuple[str, ...] = TWITTER_SCREENSHOT_MODE_VALUES
    article_screenshot_checkbox_visible: bool = False
    article_screenshot_location: str = "settings_screenshot_section"
    visible_capture_options: tuple[str, ...] = ("post", "thread", "screenshot_post", "screenshot_both")
    media_download_inside_settings: bool = True
    media_download_main_row_button_visible: bool = False
    settings_keys: tuple[str, ...] = TWITTER_COMPACT_SETTING_KEYS
    removed_buttons_hidden: tuple[str, ...] = REMOVED_TWITTER_BUTTON_LABELS
    archive_controls_visible: bool = False
    local_export_button_visible: bool = False
    add_review_draft_button_visible: bool = False
    review_flow_summary_button_visible: bool = False
    account_thread_semantics: str = "x.com account URL: Thread means account/timeline posts amount/path; Post means profile/basic post target"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def is_twitter_account_url(url: str) -> bool:
    parsed = urlsplit(str(url or ""))
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 1:
        return False
    if parts[0].lower() in {"i", "home", "search", "settings", "notifications", "messages"}:
        return False
    return True


def is_twitter_status_url(url: str) -> bool:
    parsed = urlsplit(str(url or ""))
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 3 and parts[1].lower() in {"status", "statuses"}


def twitter_default_display_title(row: SourceResourceRowState) -> tuple[str, str]:
    source_id = str(getattr(row, "source_id", "") or "").strip()
    generic_titles = {"Twitter/X post", "Twitter/X profile", "Twitter/X source"}

    for candidate in (
        getattr(row, "preview_text", ""),
        getattr(row, "display_title", ""),
        getattr(row, "title", ""),
    ):
        title = str(candidate or "").strip()
        if title and not title.isdigit() and title != source_id and title not in generic_titles:
            return title, title

    if is_twitter_status_url(row.canonical_url):
        return "Twitter/X post", ""
    if is_twitter_account_url(row.canonical_url):
        return "Twitter/X profile", ""
    return "Twitter/X source", ""


def build_twitter_compact_row_state(row: SourceResourceRowState) -> TwitterCompactRowState:
    if row.adapter_id != "twitter_x":
        raise ValueError("Twitter compact row state only applies to X/Twitter source rows")
    semantics = (
        "x.com account URL: Thread means account/timeline posts amount/path; Post means profile/basic post target"
        if is_twitter_account_url(row.canonical_url)
        else "post URL: Post captures the post target; Thread captures reply/thread context"
    )
    return TwitterCompactRowState(
        row_id=row.row_id,
        source_url=row.raw_url or row.canonical_url,
        adapter_id=row.adapter_id,
        display_title=twitter_default_display_title(row)[0],
        preview_text=twitter_default_display_title(row)[1],
        account_thread_semantics=semantics,
    )
