from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class SourceMethodStatus(str, Enum):
    EXISTING_SUPPORTED = "existing_supported"
    METADATA_AUDIT_READY = "metadata_audit_ready"
    PLANNED_ADAPTER_FAMILY = "planned_adapter_family"
    FUTURE_RESEARCH_REQUIRED = "future_research_required"
    LIVE_APPROVED_ONLY = "live_approved_only"


class AccessModeLabel(str, Enum):
    PUBLIC_ACCESS = "PUBLIC_ACCESS"
    USER_AUTHENTICATED_ACCESS = "USER_AUTHENTICATED_ACCESS"
    METERED_OR_PREVIEW_ACCESS = "METERED_OR_PREVIEW_ACCESS"
    BLOCKED_OR_PAYWALLED = "BLOCKED_OR_PAYWALLED"
    ARCHIVED_COPY = "ARCHIVED_COPY"
    MANUAL_IMPORT = "MANUAL_IMPORT"


class CapturePurpose(str, Enum):
    RESEARCH = "research"
    QUOTATION = "quotation"
    CRITICISM_REVIEW = "criticism_review"
    CURRENT_EVENTS_REFERENCE = "current_events_reference"
    ACADEMIC_ANALYSIS = "academic_analysis"
    PRESERVATION = "preservation"


@dataclass(frozen=True)
class SourceMethod:
    method_id: str
    display_name: str
    platform_family: str
    source_type: str
    status: SourceMethodStatus
    default_access_modes: tuple[AccessModeLabel, ...]
    supports_posts: bool = False
    supports_comments: bool = False
    supports_replies: bool = False
    supports_livechat: bool = False
    supports_captions_transcripts: bool = False
    supports_full_page_screenshot: bool = False
    supports_visible_page_text: bool = False
    supports_readable_article_text: bool = False
    supports_html_snapshot: bool = False
    supports_archive_check: bool = True
    supports_archive_submit: bool = False
    supports_media_evidence: bool = False
    credential_requirement: str = "not_needed_or_unknown"
    capture_boundary: str = "metadata_or_user_triggered_capture_only"
    implementation_note: str = ""
    test_status: str = "not_live_tested"
    known_limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        data["default_access_modes"] = [m.value for m in self.default_access_modes]
        return data


@dataclass(frozen=True)
class SourceMethodFamily:
    family_id: str
    display_name: str
    description: str
    methods: tuple[SourceMethod, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "display_name": self.display_name,
            "description": self.description,
            "method_count": len(self.methods),
            "methods": [m.to_dict() for m in self.methods],
        }


@dataclass(frozen=True)
class SourceWebsiteMethodCatalog:
    catalog_id: str
    families: tuple[SourceMethodFamily, ...]
    policy_summary: str = (
        "Evidence preservation and citation workflows are user-triggered and record provenance, "
        "access mode and capture method. The app does not make final legal conclusions."
    )

    def methods(self) -> tuple[SourceMethod, ...]:
        return tuple(method for family in self.families for method in family.methods)

    def find_method(self, method_id: str) -> SourceMethod | None:
        return next((m for m in self.methods() if m.method_id == method_id), None)

    def methods_by_status(self, status: SourceMethodStatus) -> tuple[SourceMethod, ...]:
        return tuple(m for m in self.methods() if m.status == status)

    def methods_by_family(self, family_id: str) -> tuple[SourceMethod, ...]:
        family = next((f for f in self.families if f.family_id == family_id), None)
        return family.methods if family else ()

    def to_dict(self) -> dict[str, object]:
        methods = self.methods()
        return {
            "catalog_id": self.catalog_id,
            "family_count": len(self.families),
            "method_count": len(methods),
            "existing_supported_count": len(self.methods_by_status(SourceMethodStatus.EXISTING_SUPPORTED)),
            "metadata_audit_ready_count": len(self.methods_by_status(SourceMethodStatus.METADATA_AUDIT_READY)),
            "planned_adapter_family_count": len(self.methods_by_status(SourceMethodStatus.PLANNED_ADAPTER_FAMILY)),
            "future_research_required_count": len(self.methods_by_status(SourceMethodStatus.FUTURE_RESEARCH_REQUIRED)),
            "policy_summary": self.policy_summary,
            "families": [f.to_dict() for f in self.families],
        }


def _method(
    method_id: str,
    display_name: str,
    platform_family: str,
    source_type: str,
    status: SourceMethodStatus,
    modes: Sequence[AccessModeLabel],
    **kwargs: object,
) -> SourceMethod:
    return SourceMethod(
        method_id=method_id,
        display_name=display_name,
        platform_family=platform_family,
        source_type=source_type,
        status=status,
        default_access_modes=tuple(modes),
        **kwargs,
    )


def build_default_source_website_method_catalog() -> SourceWebsiteMethodCatalog:
    public = (AccessModeLabel.PUBLIC_ACCESS,)
    public_manual_archive = (AccessModeLabel.PUBLIC_ACCESS, AccessModeLabel.MANUAL_IMPORT, AccessModeLabel.ARCHIVED_COPY)
    mixed = (AccessModeLabel.PUBLIC_ACCESS, AccessModeLabel.USER_AUTHENTICATED_ACCESS, AccessModeLabel.METERED_OR_PREVIEW_ACCESS)
    archived = (AccessModeLabel.ARCHIVED_COPY, AccessModeLabel.MANUAL_IMPORT)

    youtube = SourceMethodFamily(
        family_id="video_youtube",
        display_name="YouTube",
        description="Existing YouTube comments/livechat/transcripts plus future selected public media evidence.",
        methods=(
            _method("youtube_transcripts", "YouTube transcripts/captions", "youtube", "captions_transcripts", SourceMethodStatus.EXISTING_SUPPORTED, public, supports_captions_transcripts=True, supports_archive_check=True, implementation_note="Existing transcript/caption workflow remains supported."),
            _method("youtube_comments", "YouTube comments and replies", "youtube", "comments", SourceMethodStatus.EXISTING_SUPPORTED, public, supports_comments=True, supports_replies=True, implementation_note="Existing YouTube comment fetching/export behavior must remain unchanged."),
            _method("youtube_livechat", "YouTube live chat", "youtube", "livechat", SourceMethodStatus.EXISTING_SUPPORTED, public, supports_livechat=True, implementation_note="Existing livechat export remains text/event oriented."),
            _method("youtube_public_media_future", "YouTube public video/media evidence", "youtube", "media", SourceMethodStatus.PLANNED_ADAPTER_FAMILY, public, supports_media_evidence=True, known_limitations=("Private, unavailable, restricted or inaccessible videos are not download targets.", "ASR execution stays separate from media selection.")),
        ),
    )

    generic = SourceMethodFamily(
        family_id="generic_web",
        display_name="Generic web/article capture",
        description="Generic articles, visible page text, screenshots, comments and manual/archive imports.",
        methods=(
            _method("generic_article_text", "Generic readable article text", "generic_web", "article_text", SourceMethodStatus.METADATA_AUDIT_READY, mixed, supports_readable_article_text=True, supports_html_snapshot=True, implementation_note="Selector/JSON-LD/article/main/text-density fallback with reviewable confidence."),
            _method("generic_visible_page_text", "Generic visible page text outline", "generic_web", "page_outline", SourceMethodStatus.METADATA_AUDIT_READY, mixed, supports_visible_page_text=True, supports_full_page_screenshot=True),
            _method("generic_full_page_screenshot", "Generic full-page screenshot", "generic_web", "screenshot", SourceMethodStatus.METADATA_AUDIT_READY, mixed, supports_full_page_screenshot=True, implementation_note="Faithful screenshot first; modified/stitched variants must be labelled as derived."),
            _method("generic_comments_manual_import", "Generic comments manual/import", "generic_web", "comments", SourceMethodStatus.METADATA_AUDIT_READY, public_manual_archive, supports_comments=True, supports_replies=True, known_limitations=("No universal selector claim.",)),
            _method("generic_comments_site_selector", "Generic comments site-specific selector", "generic_web", "comments_selector", SourceMethodStatus.LIVE_APPROVED_ONLY, mixed, supports_comments=True, supports_replies=True, known_limitations=("Requires named-site selector audit before live execution.",)),
            _method("archive_only_import", "Archive-only import", "archive", "archive_import", SourceMethodStatus.METADATA_AUDIT_READY, archived, supports_archive_check=True, implementation_note="Import archive URL and metadata without claiming original live capture."),
        ),
    )

    named_ready = SourceMethodFamily(
        family_id="named_ready",
        display_name="Named site packs already planned",
        description="Metadata-backed named-site source methods already represented by packs and command/checklist sidecars.",
        methods=(
            _method("msn_article", "MSN article", "msn", "article_text", SourceMethodStatus.METADATA_AUDIT_READY, public, supports_readable_article_text=True, supports_full_page_screenshot=True, known_limitations=("Live/manual smoke approval required.",)),
            _method("msn_shadow_dom_comments", "MSN shadow-DOM comments", "msn", "comments", SourceMethodStatus.METADATA_AUDIT_READY, public, supports_comments=True, supports_replies=True, known_limitations=("Open shadow-root/nested-scroll lazy loading needs named-site live approval.",)),
            _method("x_public_post_archive_manual", "X/Twitter public post archive/manual import", "twitter_x", "post", SourceMethodStatus.METADATA_AUDIT_READY, public_manual_archive, supports_posts=True, known_limitations=("No API/browser credential use in automated tests.")),
            _method("x_reply_thread_archive_manual", "X/Twitter reply-thread archive/manual import", "twitter_x", "reply_thread", SourceMethodStatus.METADATA_AUDIT_READY, public_manual_archive, supports_posts=True, supports_comments=True, supports_replies=True),
            _method("youtube_media_transcript_pack", "YouTube media/transcript pack", "youtube", "media_transcript", SourceMethodStatus.METADATA_AUDIT_READY, public, supports_media_evidence=True, supports_captions_transcripts=True, known_limitations=("No yt-dlp, FFmpeg, ASR or API execution without explicit approval.")),
        ),
    )

    future_social = SourceMethodFamily(
        family_id="future_social_comments",
        display_name="Future social/comment adapters",
        description="Social and comment-heavy adapters to be implemented adapter-by-adapter with access and credential notes.",
        methods=tuple(
            _method(method_id, display, family, source_type, SourceMethodStatus.PLANNED_ADAPTER_FAMILY, mixed, supports_posts=posts, supports_comments=comments, supports_replies=replies, supports_livechat=livechat, supports_media_evidence=media, credential_requirement=credential)
            for method_id, display, family, source_type, posts, comments, replies, livechat, media, credential in (
                ("reddit_comments", "Reddit posts/comments", "reddit", "comments", True, True, True, False, False, "optional_or_oauth_later"),
                ("tiktok_comments", "TikTok videos/comments", "tiktok", "video_comments", True, True, True, False, True, "restricted_or_research_api_later"),
                ("twitch_livechat", "Twitch live chat", "twitch", "livechat", False, True, True, True, True, "oauth_or_public_chat_later"),
                ("bluesky_threads", "Bluesky posts/replies", "bluesky", "post_thread", True, True, True, False, False, "api_or_public_later"),
                ("threads_posts", "Threads posts/replies", "threads", "post_thread", True, True, True, False, False, "login_or_public_later"),
                ("instagram_comments", "Instagram posts/comments", "instagram", "visual_comments", True, True, True, False, True, "login_likely_required"),
                ("facebook_comments", "Facebook posts/comments", "facebook", "comments", True, True, True, False, True, "login_likely_required"),
                ("pinterest_comments", "Pinterest pins/comments", "pinterest", "visual_comments", True, True, True, False, True, "public_or_login_later"),
                ("medium_responses", "Medium articles/responses", "medium", "article_comments", True, True, True, False, False, "mixed_access"),
                ("tumblr_posts_notes", "Tumblr posts/notes", "tumblr", "post_notes", True, True, True, False, True, "public_or_login_later"),
                ("linkedin_posts_comments", "LinkedIn posts/comments", "linkedin", "professional_comments", True, True, True, False, True, "user_authenticated_access"),
                ("quora_answers_comments", "Quora answers/comments", "quora", "qa_comments", True, True, True, False, False, "mixed_access"),
                ("forum_threads", "Forums and community threads", "forums", "thread_comments", True, True, True, False, False, "site_specific"),
                ("news_site_comments", "News-site comment systems", "news", "article_comments", True, True, True, False, True, "site_specific_mixed_access"),
            )
        ),
    )

    future_video = SourceMethodFamily(
        family_id="future_video_media",
        display_name="Future video/media platforms",
        description="Video and social video platforms to be implemented through normal browser/media discovery with DRM boundaries.",
        methods=tuple(
            _method(method_id, display, family, "media_comments", SourceMethodStatus.PLANNED_ADAPTER_FAMILY, mixed, supports_comments=True, supports_replies=True, supports_captions_transcripts=True, supports_media_evidence=True, credential_requirement=credential, known_limitations=("DRM bypass unsupported.", "Playback-gated discovery must be user approved."))
            for method_id, display, family, credential in (
                ("vimeo_media", "Vimeo media/comments", "vimeo", "public_or_authenticated"),
                ("dailymotion_media", "Dailymotion media/comments", "dailymotion", "public_or_authenticated"),
                ("rumble_media", "Rumble media/comments", "rumble", "public"),
                ("peertube_media", "PeerTube media/comments", "peertube", "public_or_instance_specific"),
                ("odysee_media", "Odysee media/comments", "odysee", "public_or_authenticated"),
                ("kick_livechat", "Kick streams/live chat", "kick", "public_or_authenticated"),
            )
        ),
    )

    return SourceWebsiteMethodCatalog(
        catalog_id="source_website_method_catalog_v1",
        families=(youtube, generic, named_ready, future_social, future_video),
    )


def source_method_catalog_summary_lines(catalog: SourceWebsiteMethodCatalog | None = None) -> list[str]:
    catalog = catalog or build_default_source_website_method_catalog()
    data = catalog.to_dict()
    return [
        f"Source method families: {data['family_count']}",
        f"Source methods: {data['method_count']}",
        f"Existing supported: {data['existing_supported_count']}",
        f"Metadata audit ready: {data['metadata_audit_ready_count']}",
        f"Planned adapter families: {data['planned_adapter_family_count']}",
        "Boundary: future adapter families are not live tested or executed by this catalogue.",
    ]
