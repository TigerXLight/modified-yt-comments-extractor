from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from youtube_url_utils import extract_youtube_video_id, normalize_youtube_url


from urllib.parse import urlsplit, urlunsplit


NEWS_WEBSITE_HOST_SUFFIXES = ("telegraph.co.uk",)
MSN_HOST_SUFFIXES = ("msn.com",)
TWITTER_X_HOST_SUFFIXES = ("x.com", "twitter.com")


def _normalize_basic_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("source URL must use http or https")
    host = (parsed.netloc or "").lower()
    if not host:
        raise ValueError("source URL must include a host")
    path = parsed.path or "/"
    return urlunsplit(("https", host, path, "", ""))


def _host_matches_suffix(host: str, suffix: str) -> bool:
    normalized_host = host.lower()
    normalized_suffix = suffix.lower()
    return normalized_host == normalized_suffix or normalized_host.endswith(
        f".{normalized_suffix}"
    )


def _is_supported_news_website_host(host: str) -> bool:
    return any(
        _host_matches_suffix(host, suffix)
        for suffix in NEWS_WEBSITE_HOST_SUFFIXES
    )


def _is_supported_twitter_x_host(host: str) -> bool:
    return any(
        _host_matches_suffix(host, suffix)
        for suffix in TWITTER_X_HOST_SUFFIXES
    )


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


@dataclass(frozen=True)
class SourceMethodProfile:
    profile_id: str
    adapter_id: str
    display_name: str
    method_family: str
    supported_modes: tuple[str, ...] = ()
    expected_artifact_types: tuple[str, ...] = ()
    required_operator_fields: tuple[str, ...] = ()
    approval_required: bool = True
    manual_operator_only: bool = True
    live_execution_default_enabled: bool = False
    archive_fallback_supported: bool = False
    manual_import_supported: bool = False
    network_actions_performed: bool = False
    browser_automation_performed: bool = False
    provider_api_calls_performed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "approval_required": self.approval_required,
            "archive_fallback_supported": self.archive_fallback_supported,
            "browser_automation_performed": self.browser_automation_performed,
            "display_name": self.display_name,
            "expected_artifact_types": list(self.expected_artifact_types),
            "live_execution_default_enabled": self.live_execution_default_enabled,
            "manual_import_supported": self.manual_import_supported,
            "manual_operator_only": self.manual_operator_only,
            "method_family": self.method_family,
            "network_actions_performed": self.network_actions_performed,
            "notes": self.notes,
            "profile_id": self.profile_id,
            "provider_api_calls_performed": self.provider_api_calls_performed,
            "required_operator_fields": list(self.required_operator_fields),
            "supported_modes": list(self.supported_modes),
        }


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



class NewsWebsiteSourceAdapter:
    source_name = "news_website"
    capabilities = SourceCapabilities(
        supports_timestamps=True,
    )
    metadata = SourceAdapterMetadata(
        display_name="News Website",
        platform_family=PLATFORM_NEWS_WEBSITE,
        credential_type=CREDENTIAL_NONE,
        credentials_required=False,
        credentials_optional=False,
        supports_browser_capture=False,
        supports_manual_import=True,
        setup_hint=(
            "Metadata-only Telegraph-style news website adapter skeleton. "
            "Future capture must remain site-specific or site-family-specific."
        ),
        test_connection_supported=False,
        privacy_notes=(
            "No request is made by this adapter skeleton; future browser/API capture may expose "
            "article access patterns to the target website or archive service."
        ),
        cost_or_rate_limit_notes=(
            "No cost or rate limits are used by this adapter skeleton because it performs no network calls."
        ),
        access_limitations=(
            "This adapter is a metadata/URL-recognition skeleton only for known non-MSN news website host suffixes. "
            "It does not fetch pages, scrape comments, capture screenshots, inspect archives, "
            "download media, bypass access controls, or integrate with the GUI."
        ),
    )

    def can_handle(self, url: str) -> bool:
        try:
            parsed = urlsplit((url or "").strip())
            if parsed.scheme.lower() not in ("http", "https"):
                return False
            return _is_supported_news_website_host(parsed.netloc)
        except ValueError:
            return False

    def normalize_url(self, url: str) -> str:
        normalized = _normalize_basic_url(url)
        parsed = urlsplit(normalized)
        if not _is_supported_news_website_host(parsed.netloc):
            raise ValueError(f"unsupported news website host: {parsed.netloc}")
        return normalized

    def extract_source_id(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlsplit(normalized)
        return f"{parsed.netloc}{parsed.path}"


class MsnSourceAdapter:
    source_name = "msn"
    capabilities = SourceCapabilities(
        supports_comments=True,
        supports_replies=True,
        supports_timestamps=True,
    )
    metadata = SourceAdapterMetadata(
        display_name="MSN",
        platform_family=PLATFORM_NEWS_WEBSITE,
        credential_type=CREDENTIAL_NONE,
        credentials_required=False,
        credentials_optional=False,
        supports_browser_capture=True,
        supports_manual_import=True,
        setup_hint=(
            "Production MSN adapter supports explicit headless browser capture plus local V34/V35 comments/profile imports. "
            "Visible browser mode is opt-in with headed/debug options."
        ),
        test_connection_supported=False,
        privacy_notes=(
            "No request is made by this adapter scaffold; future browser/API capture may expose "
            "article or comment access patterns to MSN or archive services."
        ),
        cost_or_rate_limit_notes=(
            "No cost or rate limits are used by this adapter scaffold because it performs no network calls."
        ),
        access_limitations=(
            "This adapter recognizes/canonicalizes MSN article URLs and routes explicit operator-invoked "
            "headless browser capture, article/comments screenshots, local comments/profile exports, article media "
            "receipts, and archive/viewer metadata. It does not use accounts/cookies, bypass access controls, "
            "open a visible browser by default, or claim WARC/WACZ replay success without validation metadata."
        ),
    )

    def can_handle(self, url: str) -> bool:
        try:
            parsed = urlsplit((url or "").strip())
            if parsed.scheme.lower() not in ("http", "https"):
                return False
            return any(_host_matches_suffix(parsed.netloc, suffix) for suffix in MSN_HOST_SUFFIXES)
        except ValueError:
            return False

    def normalize_url(self, url: str) -> str:
        from source_resource_state import canonicalize_msn_url

        return canonicalize_msn_url(url)

    def extract_source_id(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlsplit(normalized)
        return f"{parsed.netloc}{parsed.path}"


class TwitterXSourceAdapter:
    source_name = "twitter_x"
    capabilities = SourceCapabilities(
        supports_comments=True,
        supports_replies=True,
        supports_likes=True,
        supports_timestamps=True,
    )
    metadata = SourceAdapterMetadata(
        display_name="X / Twitter",
        platform_family=PLATFORM_TEXT_MICROBLOGGING,
        credential_type=CREDENTIAL_MANUAL,
        credentials_required=False,
        credentials_optional=True,
        supports_browser_capture=False,
        supports_manual_import=True,
        setup_hint="Local/manual import and archive-fallback profile only; no X/Twitter API or browser automation.",
        test_connection_supported=False,
        privacy_notes="No X/Twitter request is made by this adapter metadata path.",
        cost_or_rate_limit_notes="No API cost or rate limits are used because no network/API call is performed.",
        access_limitations=(
            "Recognizes public X/Twitter URLs for local review metadata and archive-fallback planning only. "
            "It does not browse X/Twitter, automate a browser, call the API, use cookies, or download media."
        ),
    )

    def can_handle(self, url: str) -> bool:
        try:
            parsed = urlsplit((url or "").strip())
            if parsed.scheme.lower() not in ("http", "https"):
                return False
            return _is_supported_twitter_x_host(parsed.netloc)
        except ValueError:
            return False

    def normalize_url(self, url: str) -> str:
        normalized = _normalize_basic_url(url)
        parsed = urlsplit(normalized)
        if not _is_supported_twitter_x_host(parsed.netloc):
            raise ValueError(f"unsupported X/Twitter host: {parsed.netloc}")
        return normalized

    def extract_source_id(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlsplit(normalized)
        return f"{parsed.netloc}{parsed.path}"


YOUTUBE_SOURCE_ADAPTER = YouTubeSourceAdapter()
MSN_SOURCE_ADAPTER = MsnSourceAdapter()
TWITTER_X_SOURCE_ADAPTER = TwitterXSourceAdapter()
NEWS_WEBSITE_SOURCE_ADAPTER = NewsWebsiteSourceAdapter()
AVAILABLE_SOURCE_ADAPTERS: Sequence[SourceAdapter] = (
    YOUTUBE_SOURCE_ADAPTER,
    MSN_SOURCE_ADAPTER,
    TWITTER_X_SOURCE_ADAPTER,
    NEWS_WEBSITE_SOURCE_ADAPTER,
)


MSN_ARTICLE_COMMENT_PROFILE = SourceMethodProfile(
    profile_id="msn_article_comments_shadow_manual_import",
    adapter_id="msn",
    display_name="MSN article/comments source adapter profile",
    method_family="article_comments_browser_and_local_import",
    supported_modes=(
        "posts",
        "comments",
        "replies",
        "live_chat_future",
        "captions_transcripts_future",
        "full_page_screenshot",
        "visible_page_text",
        "readable_article_text",
        "html_snapshot",
        "archive_check",
        "archive_submit",
        "video_media_evidence_future",
        "media_source_chain_fields",
        "disputed_framing_source_author_correction_notes",
        "source_role_labels",
    ),
    expected_artifact_types=(
        "raw_html",
        "rendered_page_html",
        "final_dom",
        "article_text",
        "comments_json",
        "comments_html",
        "profiles_json",
        "article_screenshot",
        "comments_stitched_screenshot",
        "media_receipt",
        "archive_result",
        "source_role_sidecar",
        "media_source_chain_sidecar",
        "disputed_framing_manual_notes",
    ),
    required_operator_fields=("source_url", "selected_modes", "manual_observation_reference", "operator_approval_for_live_capture"),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Production path supports explicit headless/browser-gated MSN article and comments capture plus V34/V35 local "
        "comments/profile imports. Live execution is opt-in; source-role/media-chain labels are preserved as metadata "
        "and do not automatically classify real-world incident claims."
    ),
)
TWITTER_X_ARCHIVE_FALLBACK_PROFILE = SourceMethodProfile(
    profile_id="twitter_x_post_reply_archive_fallback",
    adapter_id="twitter_x",
    display_name="X/Twitter post/reply archive fallback profile",
    method_family="post_reply_archive_fallback",
    supported_modes=("webpage", "comments", "archive_check", "archive_submit"),
    expected_artifact_types=("raw_sidecar", "archive_result", "comments_jsonl"),
    required_operator_fields=("source_url", "operator_supplied_export_or_archive_reference"),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes="Local/manual export and archive-fallback metadata only; no API, scraping, browser automation, or media download.",
)
TWITTER_X_PUBLIC_POST_ARCHIVE_PROFILE = SourceMethodProfile(
    profile_id="twitter_x_public_post_archive",
    adapter_id="twitter_x",
    display_name="X/Twitter public post archive audit profile",
    method_family="public_post_archive_manual_metadata",
    supported_modes=("webpage", "archive_check", "archive_import", "manual_import"),
    expected_artifact_types=("raw_sidecar", "archive_result", "screenshot", "dom_snapshot"),
    required_operator_fields=(
        "source_url",
        "canonical_url_expectation",
        "operator_supplied_archive_reference",
        "manual_observation_reference",
    ),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Metadata-backed public post/archive audit profile only; no X/Twitter API, "
        "browser automation, live archive call, screenshot capture, or media download."
    ),
)
TWITTER_X_REPLY_THREAD_ARCHIVE_PROFILE = SourceMethodProfile(
    profile_id="twitter_x_reply_thread_archive",
    adapter_id="twitter_x",
    display_name="X/Twitter reply thread archive audit profile",
    method_family="reply_thread_archive_manual_metadata",
    supported_modes=("comments", "archive_check", "archive_import", "manual_import"),
    expected_artifact_types=("comments_jsonl", "raw_sidecar", "archive_result", "dom_snapshot"),
    required_operator_fields=(
        "source_url",
        "parent_post_reference",
        "reply_id_list_or_thread_boundary",
        "operator_supplied_archive_reference",
        "manual_observation_reference",
    ),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Metadata-backed reply-thread/archive audit profile only; reply boundaries and "
        "deletion/completeness remain manual-review metadata, not live X/Twitter execution."
    ),
)
YOUTUBE_MEDIA_TRANSCRIPT_COMMENT_PROFILE = SourceMethodProfile(
    profile_id="youtube_media_transcript_comment",
    adapter_id="youtube",
    display_name="YouTube media/transcript/comment source profile",
    method_family="youtube_existing_runtime_metadata",
    supported_modes=("webpage", "comments", "livechat", "media", "transcript"),
    expected_artifact_types=("comments_jsonl", "livechat_jsonl", "media_inventory", "transcript"),
    required_operator_fields=("source_url", "existing_runtime_output_status"),
    manual_import_supported=True,
    notes="Binds existing YouTube runtime outputs into review metadata; this profile does not start YouTube runtime/API calls.",
)
GENERIC_ARTICLE_COMMENT_PROFILE = SourceMethodProfile(
    profile_id="generic_article_comment_manual",
    adapter_id="news_website",
    display_name="Generic article/comment manual profile",
    method_family="generic_article_comment_manual",
    supported_modes=("webpage", "comments", "archive_check"),
    expected_artifact_types=("raw_html", "article_text", "comments_text", "archive_result"),
    required_operator_fields=("source_url", "manual_source_material_reference"),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes="Manual/local supplied article and comment metadata only; no generic scraper is implied.",
)
GENERIC_ARTICLE_HTML_PROFILE = SourceMethodProfile(
    profile_id="generic_article_html",
    adapter_id="news_website",
    display_name="Generic article HTML audit profile",
    method_family="generic_article_html_manual_metadata",
    supported_modes=("webpage", "archive_check", "manual_import"),
    expected_artifact_types=("raw_html", "final_dom", "article_text", "page_outline", "screenshot", "archive_result"),
    required_operator_fields=(
        "source_url",
        "canonical_url",
        "html_snapshot_reference",
        "text_extraction_receipt_reference",
        "operator_review_note",
    ),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Metadata-backed generic article HTML audit profile; text extraction remains "
        "placeholder/receipt metadata until site-specific or supplied-content review."
    ),
)
GENERIC_ARTICLE_COMMENTS_PROFILE = SourceMethodProfile(
    profile_id="generic_article_comments",
    adapter_id="news_website",
    display_name="Generic article comments audit profile",
    method_family="generic_article_comments_manual_metadata",
    supported_modes=("comments", "archive_check", "manual_import"),
    expected_artifact_types=("comments_text", "comments_jsonl", "raw_sidecar", "archive_result"),
    required_operator_fields=(
        "source_url",
        "comment_tree_boundary",
        "manual_observation_reference",
        "selector_or_site_profile_note",
        "operator_review_note",
    ),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Metadata-backed generic comment audit profile; site-specific selectors and comment "
        "systems remain audit-required before live execution."
    ),
)
MANUAL_LOCAL_IMPORT_PROFILE = SourceMethodProfile(
    profile_id="manual_local_file_import",
    adapter_id="manual_local_import",
    display_name="Manual/local file import profile",
    method_family="manual_local_import",
    supported_modes=("manual_import", "media", "transcript", "archive_import"),
    expected_artifact_types=("raw_sidecar", "media", "extracted_text", "archive_result"),
    required_operator_fields=("local_file_name", "operator_review_note"),
    manual_import_supported=True,
    notes="User-supplied local files only; no file move or file-existence claim is made by metadata helpers.",
)
ARCHIVE_ONLY_IMPORT_PROFILE = SourceMethodProfile(
    profile_id="archive_only_import",
    adapter_id="manual_local_import",
    display_name="Archive-only import audit profile",
    method_family="archive_only_manual_import_metadata",
    supported_modes=("archive_import", "manual_import"),
    expected_artifact_types=("archive_result", "raw_sidecar"),
    required_operator_fields=(
        "archive_url",
        "original_url",
        "archive_provider_or_source_type",
        "retrieved_metadata_reference",
        "operator_signoff_status",
    ),
    archive_fallback_supported=True,
    manual_import_supported=True,
    notes=(
        "Metadata-backed archive-only import profile for operator-supplied archive URLs; "
        "no live site, archive provider lookup, submission, or retrieval is performed."
    ),
)
SOURCE_METHOD_PROFILES: Sequence[SourceMethodProfile] = (
    MSN_ARTICLE_COMMENT_PROFILE,
    TWITTER_X_ARCHIVE_FALLBACK_PROFILE,
    TWITTER_X_PUBLIC_POST_ARCHIVE_PROFILE,
    TWITTER_X_REPLY_THREAD_ARCHIVE_PROFILE,
    YOUTUBE_MEDIA_TRANSCRIPT_COMMENT_PROFILE,
    GENERIC_ARTICLE_COMMENT_PROFILE,
    GENERIC_ARTICLE_HTML_PROFILE,
    GENERIC_ARTICLE_COMMENTS_PROFILE,
    MANUAL_LOCAL_IMPORT_PROFILE,
    ARCHIVE_ONLY_IMPORT_PROFILE,
)


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



def source_method_profile_ids(
    profiles: Sequence[SourceMethodProfile] = SOURCE_METHOD_PROFILES,
) -> tuple[str, ...]:
    return tuple(profile.profile_id for profile in profiles)


def find_source_method_profile(
    profile_id: str,
    profiles: Sequence[SourceMethodProfile] = SOURCE_METHOD_PROFILES,
) -> SourceMethodProfile | None:
    normalized_profile_id = (profile_id or "").strip().lower()
    if not normalized_profile_id:
        return None
    for profile in profiles:
        if profile.profile_id.lower() == normalized_profile_id:
            return profile
    return None


def default_source_method_profile_for_adapter(
    adapter_id: str,
    profiles: Sequence[SourceMethodProfile] = SOURCE_METHOD_PROFILES,
) -> SourceMethodProfile:
    normalized_adapter_id = (adapter_id or "").strip().lower()
    for profile in profiles:
        if profile.adapter_id.lower() == normalized_adapter_id:
            return profile
    if normalized_adapter_id == "manual_local_import":
        return MANUAL_LOCAL_IMPORT_PROFILE
    return GENERIC_ARTICLE_COMMENT_PROFILE


def find_source_adapter(url: str) -> Optional[SourceAdapter]:
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        if adapter.can_handle(url):
            return adapter
    return None
