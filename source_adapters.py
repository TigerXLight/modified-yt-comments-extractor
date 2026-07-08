from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from youtube_url_utils import extract_youtube_video_id, normalize_youtube_url


@dataclass(frozen=True)
class SourceCapabilities:
    supports_comments: bool = False
    supports_replies: bool = False
    supports_livechat: bool = False
    supports_likes: bool = False
    supports_timestamps: bool = False
    supports_author_channel_ids: bool = False
    supports_transcripts: bool = False


class SourceAdapter(Protocol):
    source_name: str
    capabilities: SourceCapabilities

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


def find_source_adapter(url: str) -> Optional[SourceAdapter]:
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        if adapter.can_handle(url):
            return adapter
    return None
