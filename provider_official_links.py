from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse


LINK_TYPE_WEBSITE = "website"
LINK_TYPE_DEVELOPER_DOCS = "developer_docs"
LINK_TYPE_CREDENTIAL_SETUP = "credential_setup"
LINK_TYPE_PRICING = "pricing"
LINK_TYPE_SERVICE_STATUS = "service_status"
LINK_TYPE_REPOSITORY = "repository"
LINK_TYPE_RELEASES = "releases"

LINK_TYPES = (
    LINK_TYPE_WEBSITE,
    LINK_TYPE_DEVELOPER_DOCS,
    LINK_TYPE_CREDENTIAL_SETUP,
    LINK_TYPE_PRICING,
    LINK_TYPE_SERVICE_STATUS,
    LINK_TYPE_REPOSITORY,
    LINK_TYPE_RELEASES,
)


@dataclass(frozen=True)
class OfficialProviderLink:
    label: str
    url: str
    link_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "url": self.url,
            "link_type": self.link_type,
        }


@dataclass(frozen=True)
class OfficialProviderLinkMetadata:
    entry_id: str
    links: tuple[OfficialProviderLink, ...] = ()
    not_applicable: tuple[str, ...] = ()
    coverage_gaps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "links": [link.to_dict() for link in self.links],
            "not_applicable": list(self.not_applicable),
            "coverage_gaps": list(self.coverage_gaps),
        }


def _link(label: str, url: str, link_type: str) -> OfficialProviderLink:
    return OfficialProviderLink(label=label, url=url, link_type=link_type)


def website(url: str, label: str = "Provider website") -> OfficialProviderLink:
    return _link(label, url, LINK_TYPE_WEBSITE)


def docs(url: str) -> OfficialProviderLink:
    return _link("Developer documentation", url, LINK_TYPE_DEVELOPER_DOCS)


def credentials(
    url: str,
    label: str = "Get API key",
) -> OfficialProviderLink:
    return _link(label, url, LINK_TYPE_CREDENTIAL_SETUP)


def pricing(url: str) -> OfficialProviderLink:
    return _link("View current pricing", url, LINK_TYPE_PRICING)


def status(url: str) -> OfficialProviderLink:
    return _link("Service status", url, LINK_TYPE_SERVICE_STATUS)


def repository(url: str) -> OfficialProviderLink:
    return _link("Official repository", url, LINK_TYPE_REPOSITORY)


def releases(url: str) -> OfficialProviderLink:
    return _link("Downloads / releases", url, LINK_TYPE_RELEASES)


def _metadata(
    entry_id: str,
    links: Iterable[OfficialProviderLink] = (),
    *,
    not_applicable: Iterable[str] = (),
    coverage_gaps: Iterable[str] = (),
) -> OfficialProviderLinkMetadata:
    return OfficialProviderLinkMetadata(
        entry_id=entry_id,
        links=tuple(links),
        not_applicable=tuple(not_applicable),
        coverage_gaps=tuple(coverage_gaps),
    )


_NA_CONSUMER = (
    LINK_TYPE_DEVELOPER_DOCS,
    LINK_TYPE_CREDENTIAL_SETUP,
    LINK_TYPE_PRICING,
)
_NA_NO_PRICING = (LINK_TYPE_PRICING,)
_NA_LOCAL_KEY_PRICING = (
    LINK_TYPE_CREDENTIAL_SETUP,
    LINK_TYPE_PRICING,
)
_GAP_NO_VERIFIED_DEVELOPER = (
    LINK_TYPE_DEVELOPER_DOCS,
    LINK_TYPE_CREDENTIAL_SETUP,
)


OFFICIAL_LINK_METADATA = (
    _metadata(
        "asr:elevenlabs_scribe",
        (
            website("https://elevenlabs.io/"),
            docs("https://elevenlabs.io/docs"),
            credentials("https://elevenlabs.io/app/settings/api-keys"),
            pricing("https://elevenlabs.io/pricing"),
            status("https://status.elevenlabs.io/"),
        ),
    ),
    _metadata(
        "asr:whisper_cpp_vulkan_large_v3_turbo",
        (
            repository("https://github.com/ggml-org/whisper.cpp"),
            docs("https://github.com/ggml-org/whisper.cpp/blob/master/README.md"),
            releases("https://github.com/ggml-org/whisper.cpp/releases"),
        ),
        not_applicable=_NA_LOCAL_KEY_PRICING,
    ),
    _metadata(
        "asr:assemblyai_universal_3_5_pro",
        (
            website("https://www.assemblyai.com/"),
            docs("https://www.assemblyai.com/docs"),
            credentials("https://www.assemblyai.com/dashboard/api-keys"),
            pricing("https://www.assemblyai.com/pricing"),
            status("https://status.assemblyai.com/"),
        ),
    ),
    _metadata(
        "asr:deepgram_nova_3",
        (
            website("https://deepgram.com/"),
            docs("https://developers.deepgram.com/"),
            credentials("https://console.deepgram.com/project/keys"),
            pricing("https://deepgram.com/pricing"),
            status("https://status.deepgram.com/"),
        ),
    ),
    _metadata(
        "asr:speechmatics_enhanced",
        (
            website("https://www.speechmatics.com/"),
            docs("https://docs.speechmatics.com/"),
            credentials("https://portal.speechmatics.com/manage-access"),
            pricing("https://www.speechmatics.com/pricing"),
            status("https://status.speechmatics.com/"),
        ),
    ),
    _metadata(
        "asr:azure_speech",
        (
            website("https://azure.microsoft.com/products/ai-services/speech-to-text"),
            docs("https://learn.microsoft.com/azure/ai-services/speech-service/"),
            credentials(
                "https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices",
                label="Create developer app",
            ),
            pricing(
                "https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/"
            ),
            status("https://status.azure.com/"),
        ),
    ),
    _metadata(
        "asr:google_stt_video_enhanced",
        (
            website("https://cloud.google.com/speech-to-text"),
            docs("https://cloud.google.com/speech-to-text/docs"),
            credentials("https://console.cloud.google.com/apis/credentials"),
            pricing("https://cloud.google.com/speech-to-text/pricing"),
            status("https://status.cloud.google.com/"),
        ),
    ),
    _metadata(
        "asr:cohere_transcribe",
        (
            website("https://cohere.com/"),
            docs("https://docs.cohere.com/"),
            credentials("https://dashboard.cohere.com/api-keys"),
            pricing("https://cohere.com/pricing"),
        ),
    ),
    _metadata(
        "asr:google_stt_latest_long",
        (
            website("https://cloud.google.com/speech-to-text"),
            docs("https://cloud.google.com/speech-to-text/docs"),
            credentials("https://console.cloud.google.com/apis/credentials"),
            pricing("https://cloud.google.com/speech-to-text/pricing"),
            status("https://status.cloud.google.com/"),
        ),
    ),
    _metadata(
        "asr:aws_transcribe_custom_vocabulary",
        (
            website("https://aws.amazon.com/transcribe/"),
            docs("https://docs.aws.amazon.com/transcribe/"),
            credentials(
                "https://console.aws.amazon.com/iam/home#/security_credentials",
                label="Manage API keys",
            ),
            pricing("https://aws.amazon.com/transcribe/pricing/"),
            status("https://health.aws.amazon.com/health/status"),
        ),
    ),
    _metadata(
        "source:youtube",
        (
            website("https://www.youtube.com/"),
            docs("https://developers.google.com/youtube/v3"),
            credentials(
                "https://console.cloud.google.com/apis/credentials",
                label="Manage API keys",
            ),
            status("https://status.cloud.google.com/"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:vimeo",
        (
            website("https://vimeo.com/"),
            docs("https://developer.vimeo.com/api/reference"),
            credentials("https://developer.vimeo.com/apps", label="Create developer app"),
            pricing("https://vimeo.com/upgrade"),
        ),
    ),
    _metadata(
        "planned:source:tiktok",
        (
            website("https://www.tiktok.com/"),
            docs("https://developers.tiktok.com/doc/overview"),
            credentials("https://developers.tiktok.com/apps", label="Create developer app"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:dailymotion",
        (
            website("https://www.dailymotion.com/"),
            docs("https://developers.dailymotion.com/"),
        ),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:rumble",
        (website("https://rumble.com/"),),
        coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER,
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:peertube",
        (
            website("https://joinpeertube.org/"),
            docs("https://docs.joinpeertube.org/api-rest-reference.html"),
            repository("https://github.com/Chocobozzz/PeerTube"),
            releases("https://github.com/Chocobozzz/PeerTube/releases"),
        ),
        not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:twitch",
        (
            website("https://www.twitch.tv/"),
            docs("https://dev.twitch.tv/docs/"),
            credentials("https://dev.twitch.tv/console/apps", label="Create developer app"),
            status("https://status.twitch.com/"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:kick",
        (
            website("https://kick.com/"),
            docs("https://docs.kick.com/"),
        ),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:youtube_live",
        (
            website("https://www.youtube.com/live"),
            docs("https://developers.google.com/youtube/v3/live"),
            credentials(
                "https://console.cloud.google.com/apis/credentials",
                label="Manage API keys",
            ),
            status("https://status.cloud.google.com/"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata("planned:source:nebula", (website("https://nebula.tv/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:floatplane",
        (website("https://www.floatplane.com/"),),
        not_applicable=_NA_CONSUMER,
    ),
    _metadata(
        "planned:source:odysee",
        (website("https://odysee.com/"), docs("https://odysee.com/$/api")),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata("planned:source:dtube", (website("https://d.tube/"),), coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER, not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:triller", (website("https://triller.co/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:source:clapper", (website("https://clapperapp.com/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:bilibili",
        (
            website("https://www.bilibili.com/"),
            docs("https://open.bilibili.com/"),
        ),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:youku",
        (
            website("https://www.youku.com/"),
            docs("https://open.youku.com/"),
        ),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:x_twitter",
        (
            website("https://x.com/"),
            docs("https://developer.x.com/en/docs"),
            credentials(
                "https://developer.x.com/en/portal/projects-and-apps",
                label="Create developer app",
            ),
            pricing("https://developer.x.com/en/products/x-api"),
        ),
    ),
    _metadata(
        "planned:source:threads",
        (
            website("https://www.threads.net/"),
            docs("https://developers.facebook.com/docs/threads"),
            credentials("https://developers.facebook.com/apps/", label="Create developer app"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:bluesky",
        (
            website("https://bsky.app/"),
            docs("https://docs.bsky.app/"),
            credentials(
                "https://bsky.app/settings/app-passwords",
                label="Manage API keys",
            ),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:mastodon_fediverse",
        (
            website("https://joinmastodon.org/"),
            docs("https://docs.joinmastodon.org/"),
        ),
        not_applicable=(LINK_TYPE_PRICING,),
        coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,),
    ),
    _metadata(
        "planned:source:instagram",
        (
            website("https://www.instagram.com/"),
            docs("https://developers.facebook.com/docs/instagram-platform"),
            credentials("https://developers.facebook.com/apps/", label="Create developer app"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata(
        "planned:source:pixelfed",
        (
            website("https://pixelfed.org/"),
            docs("https://docs.pixelfed.org/"),
            repository("https://github.com/pixelfed/pixelfed"),
            releases("https://github.com/pixelfed/pixelfed/releases"),
        ),
        not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata("planned:source:vero", (website("https://vero.co/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:monnett",
        (),
        coverage_gaps=(LINK_TYPE_WEBSITE, LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP),
        not_applicable=(LINK_TYPE_PRICING,),
    ),
    _metadata("planned:source:flashes", (website("https://flashes.blue/"),), coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER, not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:vsco", (website("https://www.vsco.co/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:source:glass", (website("https://glass.photo/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:flickr",
        (
            website("https://www.flickr.com/"),
            docs("https://www.flickr.com/services/api/"),
            credentials("https://www.flickr.com/services/apps/create/apply/", label="Create developer app"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata("planned:source:bereal", (website("https://bereal.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:source:pinksky", (website("https://pinksky.app/"),), coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER, not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:locket", (website("https://locket.camera/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:pinterest",
        (
            website("https://www.pinterest.com/"),
            docs("https://developers.pinterest.com/docs/"),
            credentials("https://developers.pinterest.com/apps/", label="Create developer app"),
        ),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata("planned:source:lemon8", (website("https://www.lemon8-app.com/"),), not_applicable=_NA_CONSUMER),
    _metadata(
        "planned:source:reddit",
        (
            website("https://www.reddit.com/"),
            docs("https://www.reddit.com/dev/api/"),
            credentials("https://www.reddit.com/prefs/apps", label="Create developer app"),
            pricing("https://redditinc.com/policies/data-api-terms"),
        ),
    ),
    _metadata(
        "planned:source:lemmy",
        (
            website("https://join-lemmy.org/"),
            docs("https://join-lemmy.org/docs/users/04-api.html"),
            repository("https://github.com/LemmyNet/lemmy"),
            releases("https://github.com/LemmyNet/lemmy/releases"),
        ),
        not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING),
    ),
    _metadata(
        "planned:source:kbin",
        (website("https://kbin.pub/"),),
        coverage_gaps=(LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP),
        not_applicable=_NA_NO_PRICING,
    ),
    _metadata("planned:source:discuit", (website("https://discuit.net/"),), coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER, not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:squabbles", (), coverage_gaps=(LINK_TYPE_WEBSITE, LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP), not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:tildes", (website("https://tildes.net/"), repository("https://gitlab.com/tildes/tildes")), coverage_gaps=(LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP), not_applicable=_NA_NO_PRICING),
    _metadata("planned:source:hacker_news", (website("https://news.ycombinator.com/"), docs("https://github.com/HackerNews/API")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("planned:source:lobsters", (website("https://lobste.rs/"), repository("https://github.com/lobsters/lobsters")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("planned:source:4chan", (website("https://www.4chan.org/"), docs("https://github.com/4chan/4chan-API")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("planned:source:quora", (website("https://www.quora.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:source:tumblr", (website("https://www.tumblr.com/"), docs("https://www.tumblr.com/docs/en/api/v2"), credentials("https://www.tumblr.com/oauth/apps", label="Create developer app")), not_applicable=_NA_NO_PRICING),
    _metadata("source:news_website", (), coverage_gaps=(LINK_TYPE_WEBSITE,), not_applicable=(LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("planned:professional:linkedin", (website("https://www.linkedin.com/"), docs("https://learn.microsoft.com/linkedin/"), credentials("https://www.linkedin.com/developers/apps", label="Create developer app")), not_applicable=_NA_NO_PRICING),
    _metadata("planned:professional:wellfound_angellist", (website("https://wellfound.com/"),), coverage_gaps=_GAP_NO_VERIFIED_DEVELOPER, not_applicable=_NA_NO_PRICING),
    _metadata("planned:professional:hired", (website("https://hired.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:professional:teamblind_blind", (website("https://www.teamblind.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:professional:fishbowl", (website("https://www.fishbowlapp.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:professional:behance", (website("https://www.behance.net/"),), coverage_gaps=(LINK_TYPE_DEVELOPER_DOCS, LINK_TYPE_CREDENTIAL_SETUP), not_applicable=_NA_NO_PRICING),
    _metadata("planned:professional:dribbble", (website("https://dribbble.com/"), docs("https://developer.dribbble.com/v2/"), credentials("https://dribbble.com/account/applications/new", label="Create developer app")), not_applicable=_NA_NO_PRICING),
    _metadata("planned:professional:github", (website("https://github.com/"), docs("https://docs.github.com/rest"), credentials("https://github.com/settings/developers", label="Create developer app"), pricing("https://github.com/pricing"), status("https://www.githubstatus.com/"))),
    _metadata("planned:professional:researchgate", (website("https://www.researchgate.net/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:professional:lunchclub", (website("https://lunchclub.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:professional:xing", (website("https://www.xing.com/"), docs("https://dev.xing.com/"), credentials("https://dev.xing.com/applications", label="Create developer app")), coverage_gaps=(LINK_TYPE_PRICING,)),
    _metadata("planned:professional:alignable", (website("https://www.alignable.com/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:workplace:microsoft_teams", (website("https://www.microsoft.com/microsoft-teams/group-chat-software"), docs("https://learn.microsoft.com/microsoftteams/platform/"), credentials("https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade", label="Create developer app"), pricing("https://www.microsoft.com/microsoft-teams/compare-microsoft-teams-options"), status("https://status.cloud.microsoft/"))),
    _metadata("planned:workplace:google_chat", (website("https://workspace.google.com/products/chat/"), docs("https://developers.google.com/workspace/chat"), credentials("https://console.cloud.google.com/apis/credentials", label="Manage API keys"), pricing("https://workspace.google.com/pricing.html"), status("https://status.cloud.google.com/"))),
    _metadata("planned:workplace:webex_app", (website("https://www.webex.com/"), docs("https://developer.webex.com/docs"), credentials("https://developer.webex.com/my-apps", label="Create developer app"), pricing("https://www.webex.com/pricing/index.html"), status("https://status.webex.com/"))),
    _metadata("planned:workplace:mattermost", (website("https://mattermost.com/"), docs("https://developers.mattermost.com/"), repository("https://github.com/mattermost/mattermost"), pricing("https://mattermost.com/pricing/"), status("https://status.mattermost.com/")), coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,)),
    _metadata("planned:workplace:rocket_chat", (website("https://www.rocket.chat/"), docs("https://developer.rocket.chat/"), repository("https://github.com/RocketChat/Rocket.Chat"), pricing("https://www.rocket.chat/pricing")), coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,)),
    _metadata("planned:workplace:zulip", (website("https://zulip.com/"), docs("https://zulip.com/api/"), credentials("https://zulip.com/api/api-keys", label="Manage API keys"), repository("https://github.com/zulip/zulip"), pricing("https://zulip.com/plans/"))),
    _metadata("planned:workplace:element_matrix", (website("https://element.io/"), docs("https://spec.matrix.org/latest/client-server-api/"), repository("https://github.com/element-hq/element-web"), pricing("https://element.io/pricing")), coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,)),
    _metadata("planned:workplace:wire", (website("https://wire.com/"), docs("https://docs.wire.com/"), repository("https://github.com/wireapp"), pricing("https://wire.com/pricing/")), coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,)),
    _metadata("planned:workplace:guild", (website("https://guild.co/"),), not_applicable=_NA_CONSUMER),
    _metadata("planned:workplace:flock", (website("https://www.flock.com/"), docs("https://docs.flock.com/display/flockos"), pricing("https://www.flock.com/pricing")), coverage_gaps=(LINK_TYPE_CREDENTIAL_SETUP,)),
    _metadata("archive:wayback_check", (website("https://web.archive.org/"), docs("https://archive.org/help/wayback_api.php")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("archive:wayback_submit", (website("https://web.archive.org/save"), docs("https://archive.org/help/wayback_api.php")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("archive:archive_today", (website("https://archive.ph/"),), coverage_gaps=(LINK_TYPE_DEVELOPER_DOCS,), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("archive:local_archivebox", (website("https://archivebox.io/"), docs("https://docs.archivebox.io/"), repository("https://github.com/ArchiveBox/ArchiveBox"), releases("https://github.com/ArchiveBox/ArchiveBox/releases")), not_applicable=(LINK_TYPE_CREDENTIAL_SETUP, LINK_TYPE_PRICING)),
    _metadata("browser:dedicated_capture_profile", (), not_applicable=LINK_TYPES),
    _metadata("browser:existing_profile_advanced", (), not_applicable=LINK_TYPES),
)


OFFICIAL_LINK_METADATA_BY_ENTRY_ID = {
    metadata.entry_id: metadata
    for metadata in OFFICIAL_LINK_METADATA
}


def official_link_metadata_for_entry(
    entry_id: str,
) -> OfficialProviderLinkMetadata | None:
    return OFFICIAL_LINK_METADATA_BY_ENTRY_ID.get(entry_id)


def all_official_link_metadata() -> tuple[OfficialProviderLinkMetadata, ...]:
    return OFFICIAL_LINK_METADATA


def official_link_buttons_for_entry(entry_id: str) -> tuple[tuple[str, str], ...]:
    metadata = official_link_metadata_for_entry(entry_id)
    if metadata is None:
        return ()
    return tuple((link.label, link.url) for link in metadata.links)


def official_url_for_label(entry_id: str, label: str) -> str:
    for link_label, url in official_link_buttons_for_entry(entry_id):
        if link_label == label:
            return url
    return ""


def is_safe_official_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if not parsed.netloc:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.netloc.casefold()
    forbidden_hosts = (
        "bit.ly",
        "t.co",
        "tinyurl.com",
        "goo.gl",
        "search.google.com",
        "google.com",
        "www.google.com",
    )
    return host not in forbidden_hosts


def is_trusted_official_link(entry_id: str, label: str, url: str) -> bool:
    if not is_safe_official_url(url):
        return False
    return official_url_for_label(entry_id, label) == url


def official_link_labels() -> tuple[str, ...]:
    labels: list[str] = []
    seen: set[str] = set()
    for metadata in OFFICIAL_LINK_METADATA:
        for link in metadata.links:
            if link.label not in seen:
                labels.append(link.label)
                seen.add(link.label)
    return tuple(labels)
