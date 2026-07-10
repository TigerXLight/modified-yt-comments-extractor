from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from youtube_url_utils import extract_youtube_video_id, normalize_youtube_url


CREDENTIAL_NONE = "none"
CREDENTIAL_API_KEY = "api_key"
CREDENTIAL_OAUTH = "oauth"
CREDENTIAL_APP_PASSWORD = "app_password"
CREDENTIAL_BROWSER_PROFILE = "browser_profile"
CREDENTIAL_MANUAL = "manual"

PLATFORM_VIDEO_SOCIAL = "video_social"
PLATFORM_LIVE_STREAMING = "live_streaming"
PLATFORM_TEXT_MICROBLOGGING = "text_microblogging"
PLATFORM_IMAGE_VISUAL = "image_visual"
PLATFORM_COMMUNITY_FORUM = "community_forum"
PLATFORM_NEWS_WEBSITE = "news_website"
PLATFORM_PROFESSIONAL = "professional"
PLATFORM_WORKPLACE_CHAT = "workplace_chat"
PLATFORM_ARCHIVE_SERVICE = "archive_service"
PLATFORM_ASR_PROVIDER = "asr_provider"
PLATFORM_OTHER = "other"


@dataclass(frozen=True)
class SourceCapabilities:
    supports_comments: bool = False
    supports_replies: bool = False
    supports_livechat: bool = False
    supports_likes: bool = False
    supports_timestamps: bool = False
    supports_author_channel_ids: bool = False
    supports_transcripts: bool = False


@dataclass(frozen=True)
class SourceAdapterMetadata:
    display_name: str = ""
    platform_family: str = PLATFORM_OTHER
    credential_type: str = CREDENTIAL_NONE
    credentials_required: bool = False
    credentials_optional: bool = False
    supports_browser_capture: bool = False
    supports_manual_import: bool = False
    setup_hint: str = ""
    test_connection_supported: bool = False
    privacy_notes: str = ""
    cost_or_rate_limit_notes: str = ""
    access_limitations: str = ""


class SourceAdapter(Protocol):
    source_name: str
    capabilities: SourceCapabilities
    metadata: SourceAdapterMetadata

    def can_handle(self, url: str) -> bool:
        ...

    def normalize_url(self, url: str) -> str:
        ...

    def extract_source_id(self, url: str) -> str:
        ...


class YouTubeSourceAdapter:
    source_name = "youtube"
    capabilities = SourceCapabilities(
        supports_comments=True,
        supports_replies=True,
        supports_livechat=True,
        supports_likes=True,
        supports_timestamps=True,
        supports_author_channel_ids=True,
        supports_transcripts=True,
    )
    metadata = SourceAdapterMetadata(
        display_name="YouTube",
        platform_family=PLATFORM_VIDEO_SOCIAL,
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        credentials_optional=False,
        supports_browser_capture=False,
        supports_manual_import=False,
        setup_hint="Configure a YouTube Data API key for current API-based comment fetching.",
        test_connection_supported=False,
        privacy_notes="YouTube API requests may expose requested video/comment access patterns to YouTube.",
        cost_or_rate_limit_notes="YouTube Data API usage is subject to quota and rate limits.",
        access_limitations=(
            "This adapter skeleton currently covers URL parsing/validation metadata only; "
            "existing YouTube fetching behavior remains implemented elsewhere."
        ),
    )

    def can_handle(self, url: str) -> bool:
        try:
            extract_youtube_video_id(url)
        except ValueError:
            return False
        return True

    def normalize_url(self, url: str) -> str:
        return normalize_youtube_url(url)

    def extract_source_id(self, url: str) -> str:
        return extract_youtube_video_id(url)


YOUTUBE_SOURCE_ADAPTER = YouTubeSourceAdapter()
AVAILABLE_SOURCE_ADAPTERS: Sequence[SourceAdapter] = (YOUTUBE_SOURCE_ADAPTER,)


def source_adapter_names(
    adapters: Sequence[SourceAdapter] = AVAILABLE_SOURCE_ADAPTERS,
) -> tuple[str, ...]:
    return tuple(adapter.source_name for adapter in adapters)


def find_source_adapter_by_name(
    source_name: str,
    adapters: Sequence[SourceAdapter] = AVAILABLE_SOURCE_ADAPTERS,
) -> SourceAdapter | None:
    normalized_source_name = (source_name or "").strip().lower()
    if not normalized_source_name:
        return None
    for adapter in adapters:
        if adapter.source_name.lower() == normalized_source_name:
            return adapter
    return None



def find_source_adapter(url: str) -> Optional[SourceAdapter]:
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        if adapter.can_handle(url):
            return adapter
    return None
