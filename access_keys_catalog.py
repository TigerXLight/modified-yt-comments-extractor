from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    ConnectionTestStatus,
    CredentialStatus,
)
from asr_provider_metadata import (
    CREDENTIAL_API_KEY,
    CREDENTIAL_LOCAL_BINARY,
    CREDENTIAL_NONE,
    CREDENTIAL_OAUTH,
    PROVIDER_STATUS_BLOCKED,
    available_asr_provider_metadata,
)
from source_adapters import AVAILABLE_SOURCE_ADAPTERS


SECTION_ASR = ("asr_providers", "ASR Providers", 10)
SECTION_SOCIAL = ("social_media", "Social Media", 20)
SECTION_NEWS = ("news_websites", "News Websites", 30)
SECTION_PROFESSIONAL = (
    "professional_jobs_experts_portfolios",
    "Professional, Jobs, Experts & Portfolios",
    40,
)
SECTION_WORKPLACE = (
    "workplace_chat_collaboration",
    "Workplace, Chat & Collaboration",
    50,
)
SECTION_ARCHIVE = ("archive_services", "Archive Services", 60)
SECTION_BROWSER = ("browser_assisted_capture", "Browser-Assisted Capture", 70)

TOP_LEVEL_SECTIONS = (
    SECTION_ASR,
    SECTION_SOCIAL,
    SECTION_NEWS,
    SECTION_PROFESSIONAL,
    SECTION_WORKPLACE,
    SECTION_ARCHIVE,
    SECTION_BROWSER,
)


@dataclass(frozen=True)
class AccessKeysEntryLayout:
    entry_id: str
    section_id: str
    section_label: str
    section_order: int
    subgroup_id: str = ""
    subgroup_label: str = ""
    subgroup_order: int = 0
    entry_order: int = 0
    canonical_name: str = ""
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    planned_capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "section_id": self.section_id,
            "section_label": self.section_label,
            "section_order": self.section_order,
            "subgroup_id": self.subgroup_id,
            "subgroup_label": self.subgroup_label,
            "subgroup_order": self.subgroup_order,
            "entry_order": self.entry_order,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "tags": list(self.tags),
            "planned_capabilities": list(self.planned_capabilities),
        }


@dataclass(frozen=True)
class AccessKeysCatalogBundle:
    catalog: AccessKeysCatalog
    layouts: tuple[AccessKeysEntryLayout, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "catalog": self.catalog.to_dict(),
            "layout_count": len(self.layouts),
            "layouts": [layout.to_dict() for layout in self.layouts],
        }


def _access_mode(
    credential_type: str,
    *,
    local_runtime: bool = False,
) -> AccessMode:
    if local_runtime or credential_type == CREDENTIAL_LOCAL_BINARY:
        return AccessMode.LOCAL_ONLY
    if credential_type == CREDENTIAL_NONE:
        return AccessMode.NO_CREDENTIALS_REQUIRED
    if credential_type == CREDENTIAL_API_KEY:
        return AccessMode.API_KEY
    if credential_type == CREDENTIAL_OAUTH:
        return AccessMode.OAUTH_OR_BROWSER_LOGIN
    return AccessMode.BLOCKED_OR_NOT_CONFIGURED


def _credential_status(
    *,
    credentials_required: bool,
    credentials_optional: bool = False,
    local_runtime: bool = False,
    blocked: bool = False,
) -> CredentialStatus:
    if local_runtime or (not credentials_required and not credentials_optional):
        return CredentialStatus.NOT_NEEDED
    if blocked:
        return CredentialStatus.UNSUPPORTED
    if credentials_required:
        return CredentialStatus.REQUIRED_MISSING
    return CredentialStatus.OPTIONAL


def _slug(value: str) -> str:
    chars: list[str] = []
    for char in value.casefold():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_")


def _planned_entry(
    *,
    entry_id: str,
    entry_kind: AccessEntryKind,
    display_name: str,
    section: tuple[str, str, int],
    subgroup_id: str,
    subgroup_label: str,
    subgroup_order: int,
    entry_order: int,
    aliases: Sequence[str] = (),
    tags: Sequence[str] = (),
    planned_capabilities: Sequence[str] = (),
    access_mode: AccessMode = AccessMode.BLOCKED_OR_NOT_CONFIGURED,
    setup_hint: str = "",
    privacy_notes: str = "",
    access_limitations: str = "",
) -> tuple[AccessEntryMetadata, AccessKeysEntryLayout]:
    section_id, section_label, section_order = section
    metadata = AccessEntryMetadata(
        entry_id=entry_id,
        entry_kind=entry_kind,
        display_name=display_name,
        platform_family=section_id,
        access_mode=access_mode,
        credential_status=CredentialStatus.UNSUPPORTED,
        implementation_state="planned metadata only",
        project_status="planned; no adapter or runtime access",
        setup_hint=setup_hint or (
            "No operational adapter or credential workflow is implemented for "
            "this entry."
        ),
        privacy_notes=privacy_notes,
        access_limitations=access_limitations or (
            "Catalog metadata only. This entry does not authenticate, fetch, "
            "capture, scrape, browse, archive, or call an external service."
        ),
        last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
    )
    layout = AccessKeysEntryLayout(
        entry_id=entry_id,
        section_id=section_id,
        section_label=section_label,
        section_order=section_order,
        subgroup_id=subgroup_id,
        subgroup_label=subgroup_label,
        subgroup_order=subgroup_order,
        entry_order=entry_order,
        canonical_name=display_name,
        aliases=tuple(aliases),
        tags=tuple(tags),
        planned_capabilities=tuple(planned_capabilities),
    )
    return metadata, layout


def _source_layout(source_name: str, display_name: str) -> AccessKeysEntryLayout:
    if source_name == "youtube":
        section_id, section_label, section_order = SECTION_SOCIAL
        return AccessKeysEntryLayout(
            entry_id="source:youtube",
            section_id=section_id,
            section_label=section_label,
            section_order=section_order,
            subgroup_id="video_social_video",
            subgroup_label="Video & Social Video Platforms",
            subgroup_order=10,
            entry_order=10,
            canonical_name="YouTube",
            aliases=("youtube video", "google video"),
            tags=("video", "social video", "comments", "live chat"),
        )
    if source_name == "news_website":
        section_id, section_label, section_order = SECTION_NEWS
        return AccessKeysEntryLayout(
            entry_id="source:news_website",
            section_id=section_id,
            section_label=section_label,
            section_order=section_order,
            subgroup_id="site_specific_news",
            subgroup_label="Site-Specific / Site-Family Capture",
            subgroup_order=10,
            entry_order=10,
            canonical_name=display_name or "News Website",
            aliases=("news site", "article website", "publisher website"),
            tags=(
                "site-specific",
                "comments only",
                "visible preview",
                "article text",
                "screenshot",
                "archive check",
            ),
            planned_capabilities=(
                "site-specific comments capture",
                "visible headline or preview capture",
                "selected readable article text",
                "full-page screenshot",
                "archive check",
                "future media evidence",
            ),
        )
    section_id, section_label, section_order = SECTION_SOCIAL
    return AccessKeysEntryLayout(
        entry_id=f"source:{source_name}",
        section_id=section_id,
        section_label=section_label,
        section_order=section_order,
        subgroup_id="registered_source_adapters",
        subgroup_label="Registered Source Adapters",
        subgroup_order=900,
        entry_order=900,
        canonical_name=display_name or source_name,
        aliases=(source_name,),
        tags=("registered adapter",),
    )


def _planned_source_entries() -> tuple[
    tuple[AccessEntryMetadata, AccessKeysEntryLayout], ...
]:
    items: list[tuple[AccessEntryMetadata, AccessKeysEntryLayout]] = []

    def add(
        name: str,
        subgroup_id: str,
        subgroup_label: str,
        subgroup_order: int,
        entry_order: int,
        *,
        aliases: Sequence[str] = (),
        tags: Sequence[str] = (),
    ) -> None:
        items.append(
            _planned_entry(
                entry_id=f"planned:source:{_slug(name)}",
                entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                display_name=name,
                section=SECTION_SOCIAL,
                subgroup_id=subgroup_id,
                subgroup_label=subgroup_label,
                subgroup_order=subgroup_order,
                entry_order=entry_order,
                aliases=aliases,
                tags=tags,
                planned_capabilities=("source-specific access/capture",),
            )
        )

    # YouTube is merged from the existing adapter.
    for order, name in enumerate(
        ("Vimeo", "TikTok", "Dailymotion", "Rumble", "PeerTube"),
        start=20,
    ):
        aliases = ("short-form video",) if name == "TikTok" else ()
        add(
            name,
            "video_social_video",
            "Video & Social Video Platforms",
            10,
            order,
            aliases=aliases,
            tags=("video", "social video"),
        )

    for order, name in enumerate(("Twitch", "Kick", "YouTube Live"), start=10):
        add(
            name,
            "live_streaming",
            "Live Streaming Platforms",
            20,
            order,
            aliases=("youtube livestream",) if name == "YouTube Live" else (),
            tags=("livestream", "live chat"),
        )

    for order, name in enumerate(("Nebula", "Floatplane"), start=10):
        add(
            name,
            "creator_owned_hubs",
            "Creator-Owned & Independent Hubs",
            30,
            order,
            tags=("creator-owned", "subscription video"),
        )

    for order, name in enumerate(("Odysee", "DTube"), start=10):
        add(
            name,
            "decentralised_blockchain_video",
            "Decentralised & Blockchain-Based Video",
            40,
            order,
            tags=("decentralised video", "blockchain video"),
        )

    add(
        "Triller",
        "short_form_entertainment",
        "Short-Form & Entertainment Mobile Apps",
        50,
        10,
        tags=("short-form", "music video"),
    )
    add(
        "Clapper",
        "short_form_entertainment",
        "Short-Form & Entertainment Mobile Apps",
        50,
        20,
        tags=("short-form", "community discussion", "livestream"),
    )

    for order, name in enumerate(("Bilibili", "Youku"), start=10):
        add(
            name,
            "global_regional_video",
            "Global & Regional Video Giants",
            60,
            order,
            tags=("regional video", "streaming"),
        )

    text_microblogging = (
        ("X / Twitter", ("x", "twitter", "x twitter")),
        ("Threads", ()),
        ("Bluesky", ("blue sky",)),
        ("Mastodon / Fediverse", ("mastodon", "fediverse")),
    )
    for order, (name, aliases) in enumerate(text_microblogging, start=10):
        add(
            name,
            "text_microblogging",
            "Text & Microblogging",
            70,
            order,
            aliases=aliases,
            tags=("microblogging", "text social"),
        )

    add(
        "Instagram",
        "mainstream_visual_social",
        "Mainstream Visual Social",
        80,
        10,
        tags=("photo", "video", "visual social"),
    )

    alternative_visual = (
        ("Pixelfed", ("pixel fed",)),
        ("Vero", ()),
        ("Monnett", ("monnet",)),
        ("Flashes", ("bluesky flashes",)),
    )
    for order, (name, aliases) in enumerate(alternative_visual, start=10):
        add(
            name,
            "alternative_visual_apps",
            "Alternative, Decentralised & Privacy-Focused Visual Apps",
            90,
            order,
            aliases=aliases,
            tags=("visual social", "alternative social"),
        )

    for order, name in enumerate(("VSCO", "Glass", "Flickr"), start=10):
        add(
            name,
            "photography_creator_hubs",
            "Pure Photography & Creator Hubs",
            100,
            order,
            aliases=("flicker",) if name == "Flickr" else (),
            tags=("photography", "creator hub"),
        )

    for order, name in enumerate(("BeReal", "Pinksky", "Locket"), start=10):
        add(
            name,
            "authentic_daily_sharing",
            "Authentic & Daily Sharing",
            110,
            order,
            tags=("daily sharing", "social photo"),
        )

    for order, name in enumerate(("Pinterest", "Lemon8"), start=10):
        add(
            name,
            "visual_discovery_commercial",
            "Visual Discovery & Commercial Platforms",
            120,
            order,
            tags=("visual discovery", "commercial platform"),
        )

    add(
        "Reddit",
        "general_community_discussion",
        "General Community & Discussion",
        130,
        10,
        tags=("community", "text posts", "comments"),
    )

    for order, name in enumerate(("Lemmy", "Kbin", "Discuit"), start=10):
        add(
            name,
            "decentralised_alternative_communities",
            "Decentralised & Alternative Communities",
            140,
            order,
            tags=("community", "alternative community"),
        )

    for order, name in enumerate(
        ("Squabbles", "Tildes", "Hacker News", "Lobsters"),
        start=10,
    ):
        add(
            name,
            "threaded_forums_link_aggregators",
            "Threaded Forums & Link Aggregators",
            150,
            order,
            aliases=("hn",) if name == "Hacker News" else (),
            tags=("threaded discussion", "link aggregator"),
        )

    for order, name in enumerate(("4chan", "Quora", "Tumblr"), start=10):
        add(
            name,
            "special_interest_anonymous_qa_blogging",
            "Special-Interest, Anonymous, Q&A & Blogging",
            160,
            order,
            tags=("community", "q&a", "blogging"),
        )

    return tuple(items)


def _planned_professional_entries() -> tuple[
    tuple[AccessEntryMetadata, AccessKeysEntryLayout], ...
]:
    items: list[tuple[AccessEntryMetadata, AccessKeysEntryLayout]] = []

    groups = (
        (
            "professional_networks",
            "Professional Networks",
            10,
            (("LinkedIn", ()),),
        ),
        (
            "tech_startups_venture",
            "Tech, Startups & Venture Capital",
            20,
            (
                ("Wellfound / AngelList", ("wellfound", "angellist")),
                ("Hired", ()),
            ),
        ),
        (
            "anonymous_candid_professional",
            "Anonymous & Candid Professional Discussion",
            30,
            (
                ("TeamBlind / Blind", ("teamblind", "blind")),
                ("Fishbowl", ()),
            ),
        ),
        (
            "visual_creative_portfolios",
            "Visual & Creative Portfolios",
            40,
            (("Behance", ("adobe behance",)), ("Dribbble", ())),
        ),
        (
            "developers_academic_experts",
            "Developers & Academic Experts",
            50,
            (("GitHub", ("github developers",)), ("ResearchGate", ())),
        ),
        (
            "community_local_professional_matching",
            "Community, Local & Professional Matchmaking",
            60,
            (("Lunchclub", ()), ("Xing", ()), ("Alignable", ())),
        ),
    )

    for subgroup_id, subgroup_label, subgroup_order, entries in groups:
        for entry_order, (name, aliases) in enumerate(entries, start=10):
            items.append(
                _planned_entry(
                    entry_id=f"planned:professional:{_slug(name)}",
                    entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                    display_name=name,
                    section=SECTION_PROFESSIONAL,
                    subgroup_id=subgroup_id,
                    subgroup_label=subgroup_label,
                    subgroup_order=subgroup_order,
                    entry_order=entry_order,
                    aliases=aliases,
                    tags=("professional platform",),
                    planned_capabilities=("source-specific access/capture",),
                )
            )
    return tuple(items)


def _planned_workplace_entries() -> tuple[
    tuple[AccessEntryMetadata, AccessKeysEntryLayout], ...
]:
    items: list[tuple[AccessEntryMetadata, AccessKeysEntryLayout]] = []
    groups = (
        (
            "mainstream_corporate_ecosystems",
            "Mainstream Corporate Ecosystems",
            10,
            ("Microsoft Teams", "Google Chat", "Webex App"),
        ),
        (
            "open_source_self_hosted",
            "Open-Source & Self-Hosted",
            20,
            ("Mattermost", "Rocket.Chat", "Zulip"),
        ),
        (
            "decentralised_encrypted_networks",
            "Decentralised & Encrypted Networks",
            30,
            ("Element / Matrix", "Wire"),
        ),
        (
            "hybrid_simple_alternatives",
            "Hybrid & Simple Alternatives",
            40,
            ("Guild", "Flock"),
        ),
    )

    limitation = (
        "Planned metadata only. Workplace/chat systems may require workspace "
        "permissions and must not be treated as public-web scraping targets."
    )
    for subgroup_id, subgroup_label, subgroup_order, entries in groups:
        for entry_order, name in enumerate(entries, start=10):
            aliases: tuple[str, ...] = ()
            if name == "Element / Matrix":
                aliases = ("element", "matrix")
            items.append(
                _planned_entry(
                    entry_id=f"planned:workplace:{_slug(name)}",
                    entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                    display_name=name,
                    section=SECTION_WORKPLACE,
                    subgroup_id=subgroup_id,
                    subgroup_label=subgroup_label,
                    subgroup_order=subgroup_order,
                    entry_order=entry_order,
                    aliases=aliases,
                    tags=("workplace", "chat", "collaboration"),
                    planned_capabilities=("workspace-authorised access",),
                    privacy_notes=(
                        "Future access must respect workspace permissions and "
                        "user authorisation."
                    ),
                    access_limitations=limitation,
                )
            )
    return tuple(items)


def _planned_archive_entries() -> tuple[
    tuple[AccessEntryMetadata, AccessKeysEntryLayout], ...
]:
    section = SECTION_ARCHIVE
    entries = (
        (
            "archive:wayback_check",
            "Wayback Machine Archive Check",
            10,
            ("internet archive", "wayback", "archive.org check"),
            ("archive check",),
            "Read-only lookup is planned; no external check is performed.",
        ),
        (
            "archive:wayback_submit",
            "Wayback / Internet Archive Submit-Save",
            20,
            ("internet archive save", "wayback save", "archive.org submit"),
            ("archive submit",),
            "Submission must remain explicit and user-triggered; no submission is implemented.",
        ),
        (
            "archive:archive_today",
            "archive.ph / archive.today-style Service",
            30,
            ("archive.ph", "archive.today", "archive is"),
            ("archive check", "archive submit"),
            "Optional independent service metadata only; no lookup or submission is implemented.",
        ),
        (
            "archive:local_archivebox",
            "Local ArchiveBox-Style Preservation",
            40,
            ("archivebox", "local archive box"),
            ("local preservation",),
            "Local process planning only; ArchiveBox is not executed.",
        ),
    )
    return tuple(
        _planned_entry(
            entry_id=entry_id,
            entry_kind=AccessEntryKind.ARCHIVE_SERVICE,
            display_name=display_name,
            section=section,
            subgroup_id="archive_services",
            subgroup_label="Archive Services & Local Preservation",
            subgroup_order=10,
            entry_order=entry_order,
            aliases=aliases,
            tags=("archive",),
            planned_capabilities=capabilities,
            access_mode=(
                AccessMode.LOCAL_ONLY
                if entry_id == "archive:local_archivebox"
                else AccessMode.BLOCKED_OR_NOT_CONFIGURED
            ),
            setup_hint=hint,
        )
        for entry_id, display_name, entry_order, aliases, capabilities, hint in entries
    )


def _planned_browser_entries() -> tuple[
    tuple[AccessEntryMetadata, AccessKeysEntryLayout], ...
]:
    section = SECTION_BROWSER
    limitation = (
        "Catalog metadata only. No browser profile is opened, inspected, or "
        "used, and no passwords or cookies are harvested."
    )
    return (
        _planned_entry(
            entry_id="browser:dedicated_capture_profile",
            entry_kind=AccessEntryKind.BROWSER_ASSISTED_CAPTURE,
            display_name="Dedicated Capture Browser Profile",
            section=section,
            subgroup_id="browser_profiles",
            subgroup_label="Browser Profile Strategies",
            subgroup_order=10,
            entry_order=10,
            aliases=("capture browser", "dedicated browser profile"),
            tags=("browser-assisted capture",),
            planned_capabilities=("browser-assisted capture",),
            access_mode=AccessMode.DEDICATED_CAPTURE_BROWSER_PROFILE,
            setup_hint=(
                "Future dedicated capture profile metadata only; no profile "
                "path or browser access exists."
            ),
            privacy_notes="No password, cookie, or session harvesting is permitted.",
            access_limitations=limitation,
        ),
        _planned_entry(
            entry_id="browser:existing_profile_advanced",
            entry_kind=AccessEntryKind.BROWSER_ASSISTED_CAPTURE,
            display_name="Advanced User-Selected Existing Browser Profile",
            section=section,
            subgroup_id="browser_profiles",
            subgroup_label="Browser Profile Strategies",
            subgroup_order=10,
            entry_order=20,
            aliases=("existing browser profile", "advanced browser profile"),
            tags=("browser-assisted capture", "advanced"),
            planned_capabilities=("user-approved browser-assisted capture",),
            access_mode=AccessMode.USER_AUTHENTICATED_BROWSER_PROFILE,
            setup_hint=(
                "Future advanced, explicitly user-approved option only; no "
                "profile path or browser access exists."
            ),
            privacy_notes="No password, cookie, or session harvesting is permitted.",
            access_limitations=limitation,
        ),
    )


def _news_description_entry() -> tuple[AccessEntryMetadata, AccessKeysEntryLayout]:
    # Existing source:news_website is merged instead of duplicated.
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        if adapter.source_name == "news_website":
            metadata = adapter.metadata
            capabilities = adapter.capabilities
            entry = AccessEntryMetadata(
                entry_id="source:news_website",
                entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                display_name=metadata.display_name or "News Website",
                platform_family=SECTION_NEWS[0],
                access_mode=_access_mode(metadata.credential_type),
                credential_status=_credential_status(
                    credentials_required=metadata.credentials_required,
                    credentials_optional=metadata.credentials_optional,
                ),
                implementation_state="registered source adapter metadata",
                credential_type=metadata.credential_type,
                credentials_required=metadata.credentials_required,
                credentials_optional=metadata.credentials_optional,
                supports_browser_capture=metadata.supports_browser_capture,
                supports_manual_import=metadata.supports_manual_import,
                supports_connection_test=metadata.test_connection_supported,
                supports_comments=capabilities.supports_comments,
                supports_replies=capabilities.supports_replies,
                supports_live_chat=capabilities.supports_livechat,
                supports_captions_or_transcripts=capabilities.supports_transcripts,
                setup_hint=metadata.setup_hint,
                privacy_notes=metadata.privacy_notes,
                cost_or_rate_limit_notes=metadata.cost_or_rate_limit_notes,
                access_limitations=metadata.access_limitations,
                last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
            )
            return entry, _source_layout("news_website", entry.display_name)
    return _planned_entry(
        entry_id="source:news_website",
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        display_name="News Website",
        section=SECTION_NEWS,
        subgroup_id="site_specific_news",
        subgroup_label="Site-Specific / Site-Family Capture",
        subgroup_order=10,
        entry_order=10,
        aliases=("news site", "article website"),
        tags=("news", "site-specific"),
        planned_capabilities=(
            "comments-only capture",
            "visible preview capture",
            "selected article text",
            "full-page screenshot",
            "archive check",
            "future media evidence",
        ),
        setup_hint=(
            "News sites are too numerous for one generic adapter. Future work "
            "must use site-specific or site-family-specific rules."
        ),
        access_limitations=(
            "No generic scraper is implemented. Access mode must be recorded "
            "per URL, page, or session."
        ),
    )


def build_default_access_keys_catalog_bundle() -> AccessKeysCatalogBundle:
    entries: list[AccessEntryMetadata] = []
    layouts: list[AccessKeysEntryLayout] = []

    section_id, section_label, section_order = SECTION_ASR
    for provider_order, provider in enumerate(
        available_asr_provider_metadata(),
        start=10,
    ):
        entry_id = f"asr:{provider.provider_id}"
        entries.append(
            AccessEntryMetadata(
                entry_id=entry_id,
                entry_kind=AccessEntryKind.ASR_PROVIDER,
                display_name=provider.display_name,
                platform_family=section_id,
                access_mode=_access_mode(
                    provider.credential_type,
                    local_runtime=provider.local_runtime,
                ),
                credential_status=_credential_status(
                    credentials_required=provider.credentials_required,
                    local_runtime=provider.local_runtime,
                    blocked=(
                        provider.access_limitations != ""
                        and provider.status == PROVIDER_STATUS_BLOCKED
                    ),
                ),
                implementation_state=(
                    "local runtime metadata"
                    if provider.local_runtime
                    else "provider metadata only"
                ),
                credential_type=provider.credential_type,
                credentials_required=provider.credentials_required,
                supports_connection_test=provider.test_connection_supported,
                project_status=provider.status,
                setup_hint=provider.setup_hint,
                privacy_notes=provider.privacy_notes,
                cost_or_rate_limit_notes=provider.cost_or_rate_limit_notes,
                access_limitations=provider.access_limitations,
                last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
            )
        )
        layouts.append(
            AccessKeysEntryLayout(
                entry_id=entry_id,
                section_id=section_id,
                section_label=section_label,
                section_order=section_order,
                subgroup_id="local_cloud_asr",
                subgroup_label="Local & Cloud ASR Providers",
                subgroup_order=10,
                entry_order=provider_order,
                canonical_name=provider.display_name,
                aliases=(provider.provider_id,),
                tags=("asr", "speech recognition"),
            )
        )

    handled_sources: set[str] = set()
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        if adapter.source_name == "news_website":
            continue
        metadata = adapter.metadata
        capabilities = adapter.capabilities
        entry_id = f"source:{adapter.source_name}"
        entries.append(
            AccessEntryMetadata(
                entry_id=entry_id,
                entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                display_name=metadata.display_name or adapter.source_name,
                platform_family=(
                    SECTION_SOCIAL[0]
                    if adapter.source_name == "youtube"
                    else metadata.platform_family
                ),
                access_mode=_access_mode(metadata.credential_type),
                credential_status=_credential_status(
                    credentials_required=metadata.credentials_required,
                    credentials_optional=metadata.credentials_optional,
                ),
                implementation_state="registered source adapter metadata",
                credential_type=metadata.credential_type,
                credentials_required=metadata.credentials_required,
                credentials_optional=metadata.credentials_optional,
                supports_browser_capture=metadata.supports_browser_capture,
                supports_manual_import=metadata.supports_manual_import,
                supports_connection_test=metadata.test_connection_supported,
                supports_comments=capabilities.supports_comments,
                supports_replies=capabilities.supports_replies,
                supports_live_chat=capabilities.supports_livechat,
                supports_captions_or_transcripts=capabilities.supports_transcripts,
                setup_hint=metadata.setup_hint,
                privacy_notes=metadata.privacy_notes,
                cost_or_rate_limit_notes=metadata.cost_or_rate_limit_notes,
                access_limitations=metadata.access_limitations,
                last_test_status=ConnectionTestStatus.TEST_NOT_SUPPORTED,
            )
        )
        layouts.append(
            _source_layout(
                adapter.source_name,
                metadata.display_name or adapter.source_name,
            )
        )
        handled_sources.add((metadata.display_name or adapter.source_name).casefold())

    for metadata, layout in _planned_source_entries():
        if layout.canonical_name.casefold() in handled_sources:
            continue
        entries.append(metadata)
        layouts.append(layout)

    news_entry, news_layout = _news_description_entry()
    entries.append(news_entry)
    layouts.append(news_layout)

    for planned_group in (
        _planned_professional_entries(),
        _planned_workplace_entries(),
        _planned_archive_entries(),
        _planned_browser_entries(),
    ):
        for metadata, layout in planned_group:
            entries.append(metadata)
            layouts.append(layout)

    return AccessKeysCatalogBundle(
        catalog=AccessKeysCatalog(entries=tuple(entries)),
        layouts=tuple(layouts),
    )


def build_default_access_keys_catalog() -> AccessKeysCatalog:
    return build_default_access_keys_catalog_bundle().catalog


def layout_by_entry_id(
    layouts: Iterable[AccessKeysEntryLayout],
) -> dict[str, AccessKeysEntryLayout]:
    return {layout.entry_id: layout for layout in layouts}
