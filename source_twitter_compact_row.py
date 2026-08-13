from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from source_resource_state import SourceResourceRowState


TWITTER_COMPACT_MODES = ("Post", "Thread")
TWITTER_COMPACT_SETTING_KEYS = (
    "media_download",
    "disable_compact_selector",
    "capture_article_screenshot",
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
    compact_pattern: str = "youtube_v19_parity"
    icon_style: str = "x_twitter_dark"
    dropdown_options: tuple[str, ...] = TWITTER_COMPACT_MODES
    article_screenshot_checkbox_visible: bool = True
    visible_capture_options: tuple[str, ...] = ("article_screenshot",)
    media_download_inside_settings: bool = True
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
        account_thread_semantics=semantics,
    )
