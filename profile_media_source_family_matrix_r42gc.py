from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

R42GC_MARKER = "YTCE_R42GC_UNIVERSAL_SOURCE_ADAPTER_FAMILY_MATRIX"
SIDE_EFFECT_BOUNDARY = (
    "no network fetch, no media download, no screenshot, no archive submission, "
    "no provider/API call, no account/session use, no CAPTCHA/access-control bypass"
)

STATUS_TESTED_TRUE = "tested_true"
STATUS_VALIDATED_PLAN = "validated_plan"
STATUS_IMPLEMENTED = "implemented"
STATUS_PROVEN_MANUAL_ROUTE = "proven_manual_route"
STATUS_BASELINE_EXISTS_NOT_CLOSED = "baseline_exists_not_closed"
STATUS_VALIDATED_CURRENT_METHOD = "validated_current_method"
STATUS_NOT_TESTED = "not_tested"
STATUS_SPECIALIST_REQUIRED = "specialist_required"
STATUS_UNSUPPORTED = "unsupported"
STATUS_BLOCKED = "blocked"

ROUTE_API3128_JDOWNLOADER_FIRST = "api3128_jdownloader_first_for_selected_public_media"
ROUTE_GENERIC_ARTICLE_CORE = "normal_access_then_rendered_browser_then_archive_material"
ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY = "bbc_sounds_ytdlp_bestaudio_then_ffmpeg_audio_copy"
ROUTE_PODCAST_RSS_ENCLOSURE = "podcast_rss_metadata_and_public_enclosure_if_available"
ROUTE_METADATA_ONLY = "metadata_only_no_download"
ROUTE_ARCHIVE_IMPORT_ONLY = "archive_material_lookup_or_operator_supplied_import"
ROUTE_LOCAL_ARCHIVE_IMPORT = "local_warc_wacz_import_only"


@dataclass(frozen=True)
class SourceFamilyCapability:
    family_id: str
    display_name: str
    adapter_hint: str
    route_preference: str
    article_text: str = STATUS_NOT_TESTED
    comments: str = STATUS_NOT_TESTED
    images: str = STATUS_NOT_TESTED
    video_audio: str = STATUS_NOT_TESTED
    screenshots: str = STATUS_NOT_TESTED
    warc: str = STATUS_NOT_TESTED
    archive_lookup: str = STATUS_NOT_TESTED
    source_role_material: str = STATUS_NOT_TESTED
    specialist_layer_required: bool = False
    safe_default_action: str = "plan_only"
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes"] = list(self.notes)
        data["r42gc_marker"] = R42GC_MARKER
        return data


@dataclass(frozen=True)
class SourceFamilyDecision:
    input_url: str
    family_id: str
    adapter_hint: str
    url_kind: str
    route_preference: str
    supported: bool = True
    normalized_host: str = ""
    reason: str = ""
    capability: SourceFamilyCapability | None = None
    safety_note: str = SIDE_EFFECT_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_hint": self.adapter_hint,
            "capability": self.capability.to_dict() if self.capability else None,
            "family_id": self.family_id,
            "input_url": self.input_url,
            "normalized_host": self.normalized_host,
            "r42gc_marker": R42GC_MARKER,
            "reason": self.reason,
            "route_preference": self.route_preference,
            "safety_note": self.safety_note,
            "supported": self.supported,
            "url_kind": self.url_kind,
        }


@dataclass(frozen=True)
class R42GCMatrixReport:
    marker: str
    generated_at: str
    source_root: str
    family_count: int
    required_families_present: tuple[str, ...]
    missing_required_families: tuple[str, ...]
    capabilities: tuple[SourceFamilyCapability, ...]
    sample_decisions: tuple[SourceFamilyDecision, ...]
    checks: tuple[dict[str, str], ...]
    conclusion: str
    side_effects: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return not self.missing_required_families and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "checks": list(self.checks),
            "conclusion": self.conclusion,
            "family_count": self.family_count,
            "generated_at": self.generated_at,
            "marker": self.marker,
            "missing_required_families": list(self.missing_required_families),
            "passed": self.passed,
            "required_families_present": list(self.required_families_present),
            "sample_decisions": [decision.to_dict() for decision in self.sample_decisions],
            "side_effects": self.side_effects,
            "source_root": self.source_root,
        }


REQUIRED_FAMILIES: tuple[str, ...] = (
    "generic_article",
    "generic_webpage_media",
    "bbc_sounds",
    "podcast_rss",
    "apple_podcasts",
    "spotify_podcast",
    "youtube",
    "twitter_x",
    "instagram",
    "archive_wayback",
    "archive_today",
    "local_warc_archive",
)


SOURCE_FAMILY_CAPABILITIES: tuple[SourceFamilyCapability, ...] = (
    SourceFamilyCapability(
        family_id="generic_article",
        display_name="Generic web article/news page",
        adapter_hint="news_website",
        route_preference=ROUTE_GENERIC_ARTICLE_CORE,
        article_text=STATUS_IMPLEMENTED,
        comments=STATUS_NOT_TESTED,
        images=STATUS_IMPLEMENTED,
        video_audio=STATUS_VALIDATED_PLAN,
        screenshots=STATUS_IMPLEMENTED,
        warc=STATUS_IMPLEMENTED,
        archive_lookup=STATUS_IMPLEMENTED,
        source_role_material="material_receipt_required_before_counter_green",
        specialist_layer_required=False,
        notes=(
            "Most public web articles belong here: normal access first, rendered/browser capture when needed, "
            "then archive/material-source fallback.",
            "Comments remain not_tested unless a site-specific comments path is actually exercised.",
            "Selected public page media can route through API3128/JDownloader first after R42GB validation.",
        ),
    ),
    SourceFamilyCapability(
        family_id="generic_webpage_media",
        display_name="Generic public webpage media candidate",
        adapter_hint="webpage_media",
        route_preference=ROUTE_API3128_JDOWNLOADER_FIRST,
        article_text=STATUS_NOT_TESTED,
        comments=STATUS_NOT_TESTED,
        images=STATUS_IMPLEMENTED,
        video_audio=STATUS_TESTED_TRUE,
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="download_manifest_or_media_receipt_required",
        specialist_layer_required=False,
        notes=(
            "R42GB validates API3128/JDownloader-first planning for selected public media candidates.",
            "Localhost/local fixture media must stay on direct/local test routes.",
            "yt-dlp is fallback/reference unless a specialist adapter has a proven route.",
        ),
    ),
    SourceFamilyCapability(
        family_id="bbc_sounds",
        display_name="BBC Sounds / BBC programme audio",
        adapter_hint="bbc_sounds",
        route_preference=ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY,
        article_text=STATUS_NOT_TESTED,
        comments=STATUS_UNSUPPORTED,
        images=STATUS_NOT_TESTED,
        video_audio=STATUS_PROVEN_MANUAL_ROUTE,
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="episode_metadata_and_audio_receipt_required",
        specialist_layer_required=True,
        notes=(
            "BBC programme/Sounds audio is a specialist broadcast-audio lane, not a generic article lane.",
            "The proven manual recipe is yt-dlp bestaudio to the original asset followed by ffmpeg audio-copy to M4A.",
            "Avoid re-downloading large BBC assets when the original file already exists.",
        ),
    ),
    SourceFamilyCapability(
        family_id="podcast_rss",
        display_name="Podcast RSS feed",
        adapter_hint="podcast_rss",
        route_preference=ROUTE_PODCAST_RSS_ENCLOSURE,
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_UNSUPPORTED,
        images=STATUS_IMPLEMENTED,
        video_audio="public_enclosure_if_available_not_music",
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="feed_entry_metadata_and_enclosure_receipt_required",
        specialist_layer_required=True,
        notes=(
            "Use for public podcast RSS feeds and episode enclosures.",
            "Do not treat DRM/login/audio-platform music pages as podcast RSS downloads.",
        ),
    ),
    SourceFamilyCapability(
        family_id="apple_podcasts",
        display_name="Apple Podcasts",
        adapter_hint="apple_podcasts",
        route_preference="apple_podcasts_public_metadata_then_rss_feed_discovery",
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_UNSUPPORTED,
        images=STATUS_IMPLEMENTED,
        video_audio="rss_or_public_enclosure_if_discovered",
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="episode_metadata_and_public_feed_receipt_required",
        specialist_layer_required=True,
        notes=(
            "Apple Podcasts should be used for podcast episode/show metadata and public RSS discovery.",
            "Do not expand this into Apple Music song downloading.",
        ),
    ),
    SourceFamilyCapability(
        family_id="spotify_podcast",
        display_name="Spotify podcasts",
        adapter_hint="spotify_podcast",
        route_preference="spotify_public_podcast_metadata_no_music_download",
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_UNSUPPORTED,
        images=STATUS_IMPLEMENTED,
        video_audio="metadata_or_public_podcast_route_only",
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="episode_or_show_metadata_receipt_required",
        specialist_layer_required=True,
        notes=(
            "Use only for Spotify show/episode podcast pages.",
            "Spotify track/album/playlist music URLs are not a podcast source and should not be downloaded by this adapter.",
        ),
    ),
    SourceFamilyCapability(
        family_id="youtube",
        display_name="YouTube",
        adapter_hint="youtube",
        route_preference="existing_youtube_runtime_plus_api3128_jdownloader_internal_media_route",
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_TESTED_TRUE,
        images=STATUS_IMPLEMENTED,
        video_audio=STATUS_IMPLEMENTED,
        screenshots=STATUS_NOT_TESTED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_IMPLEMENTED,
        source_role_material="existing_runtime_output_or_download_manifest_required",
        specialist_layer_required=True,
        notes=(
            "YouTube remains a specialist adapter with existing comment/livechat/transcript/media runtimes.",
            "JDownloader/API3128 is the preferred project-internal public media route; yt-dlp remains fallback/reference.",
        ),
    ),
    SourceFamilyCapability(
        family_id="twitter_x",
        display_name="X / Twitter",
        adapter_hint="twitter_x",
        route_preference="twitter_x_specialist_public_post_thread_profile_media_archive_profiles",
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_VALIDATED_CURRENT_METHOD,
        images=STATUS_VALIDATED_CURRENT_METHOD,
        video_audio=STATUS_VALIDATED_CURRENT_METHOD,
        screenshots=STATUS_VALIDATED_CURRENT_METHOD,
        warc=STATUS_IMPLEMENTED,
        archive_lookup=STATUS_IMPLEMENTED,
        source_role_material="public_post_archive_or_local_export_material_receipt_required",
        specialist_layer_required=True,
        notes=(
            "R42GF closes Twitter/X as a specialist current-method lane, not a generic article lane.",
            "Local exporter review flow stays USER_REVIEW_REQUIRED / USER_SUPPLIED_LOCAL_EXPORT and summary-only.",
            "Public status media stays on shared media backend planning; browser/session, screenshot, archive, and source-role claims remain receipt-gated.",
            "Protected/login-limited material remains requires_access or blocked; no API/cookie/token/CAPTCHA/rate-limit bypass.",
        ),
    ),
    SourceFamilyCapability(
        family_id="instagram",
        display_name="Instagram",
        adapter_hint="instagram",
        route_preference=ROUTE_METADATA_ONLY,
        article_text=STATUS_UNSUPPORTED,
        comments=STATUS_NOT_TESTED,
        images=STATUS_SPECIALIST_REQUIRED,
        video_audio=STATUS_SPECIALIST_REQUIRED,
        screenshots=STATUS_SPECIALIST_REQUIRED,
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_NOT_TESTED,
        source_role_material="manual_or_specialist_public_material_receipt_required",
        specialist_layer_required=True,
        notes=(
            "Instagram is a visual/social specialist lane.",
            "Do not bypass login/session/rate limits/CAPTCHA; fall back to manual/source-package receipts where needed.",
        ),
    ),
    SourceFamilyCapability(
        family_id="archive_wayback",
        display_name="Internet Archive Wayback",
        adapter_hint="archive_wayback",
        route_preference=ROUTE_ARCHIVE_IMPORT_ONLY,
        article_text="archive_material_if_available",
        comments="archive_material_if_available_not_tested",
        images="archive_material_if_available",
        video_audio="archive_material_if_available",
        screenshots="archive_material_if_available",
        warc=STATUS_IMPLEMENTED,
        archive_lookup=STATUS_IMPLEMENTED,
        source_role_material="archive_material_promotion_replay_required_before_counter_green",
        specialist_layer_required=True,
        notes=(
            "Wayback URLs and CDX-style metadata belong in the archive-source lane.",
            "R42FX Metro scan was side-effect-free availability/reporting; role-counter promotion still needs replay proof.",
        ),
    ),
    SourceFamilyCapability(
        family_id="archive_today",
        display_name="archive.today / archive.ph",
        adapter_hint="archive_today",
        route_preference=ROUTE_ARCHIVE_IMPORT_ONLY,
        article_text="archive_material_if_available",
        comments="archive_material_if_available_not_tested",
        images="archive_material_if_available",
        video_audio="archive_material_if_available",
        screenshots="archive_material_if_available",
        warc=STATUS_NOT_TESTED,
        archive_lookup=STATUS_IMPLEMENTED,
        source_role_material="archive_material_promotion_replay_required_before_counter_green",
        specialist_layer_required=True,
        notes=(
            "archive.ph/archive.today does not have the same clean CDX-style interface as Wayback.",
            "Treat as candidate material/import/handoff, not guaranteed live API availability.",
        ),
    ),
    SourceFamilyCapability(
        family_id="local_warc_archive",
        display_name="Local WARC/WACZ archive package",
        adapter_hint="local_warc_archive",
        route_preference=ROUTE_LOCAL_ARCHIVE_IMPORT,
        article_text="local_archive_material_if_present",
        comments="local_archive_material_if_present_not_tested",
        images="local_archive_material_if_present",
        video_audio="local_archive_material_if_present",
        screenshots="local_archive_material_if_present",
        warc=STATUS_IMPLEMENTED,
        archive_lookup=STATUS_UNSUPPORTED,
        source_role_material="local_archive_material_receipt_required",
        specialist_layer_required=True,
        notes=(
            "Use for local WARC/WARC.GZ/WACZ material and ArchiveBox-style local packages.",
            "Import/preview only by default; do not perform live crawling from this family matrix.",
        ),
    ),
)

_CAPABILITY_BY_FAMILY = {capability.family_id: capability for capability in SOURCE_FAMILY_CAPABILITIES}

ARCHIVE_TODAY_HOSTS = {
    "archive.ph",
    "archive.today",
    "archive.is",
    "archive.li",
    "archive.vn",
    "archive.fo",
    "archive.md",
}
INSTAGRAM_HOST_SUFFIXES = ("instagram.com",)
TWITTER_X_HOST_SUFFIXES = ("x.com", "twitter.com")
YOUTUBE_HOST_SUFFIXES = ("youtube.com", "youtu.be", "youtube-nocookie.com")
BBC_HOST_SUFFIXES = ("bbc.co.uk", "bbc.com")
APPLE_PODCAST_HOST_SUFFIXES = ("podcasts.apple.com",)
SPOTIFY_HOST_SUFFIXES = ("open.spotify.com", "spotify.com")
MEDIA_EXTENSIONS = (
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".ts",
    ".m2ts",
    ".m3u8",
    ".mpd",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wav",
    ".flac",
)
LOCAL_ARCHIVE_EXTENSIONS = (".warc", ".warc.gz", ".wacz")


def _host_matches(host: str, suffixes: Iterable[str]) -> bool:
    normalized = (host or "").lower()
    for suffix in suffixes:
        s = suffix.lower()
        if normalized == s or normalized.endswith("." + s):
            return True
    return False


def _parsed_host(url: str) -> tuple[str, str, str]:
    parsed = urlsplit((url or "").strip())
    return (parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.path or "")


def _looks_like_local_path(value: str) -> bool:
    text = str(value or "").strip().strip('"').strip("'")
    if re.match(r"^[a-zA-Z]:[\\/]", text):
        return True
    if text.startswith("\\\\"):
        return True
    if text.lower().startswith("file://"):
        return True
    return False


def _lowered_path_for_local(value: str) -> str:
    text = str(value or "").strip().strip('"').strip("'").replace("\\", "/").lower()
    return text


def _is_local_archive(value: str) -> bool:
    lowered = _lowered_path_for_local(value)
    return _looks_like_local_path(value) and lowered.endswith(LOCAL_ARCHIVE_EXTENSIONS)


def _is_media_candidate_path(path: str) -> bool:
    lowered = (path or "").lower()
    return any(lowered.endswith(ext) or ext + "?" in lowered for ext in MEDIA_EXTENSIONS)


def _capability(family_id: str) -> SourceFamilyCapability:
    return _CAPABILITY_BY_FAMILY[family_id]


def _decision(
    url: str,
    family_id: str,
    *,
    url_kind: str,
    supported: bool = True,
    normalized_host: str = "",
    reason: str = "",
    route_preference: str | None = None,
) -> SourceFamilyDecision:
    capability = _capability(family_id)
    return SourceFamilyDecision(
        input_url=url,
        family_id=family_id,
        adapter_hint=capability.adapter_hint,
        url_kind=url_kind,
        route_preference=route_preference or capability.route_preference,
        supported=supported,
        normalized_host=normalized_host,
        reason=reason,
        capability=capability,
    )


def classify_source_family(url: str) -> SourceFamilyDecision:
    """Classify a URL/path into the side-effect-free R42GC source-family matrix.

    This function performs no network access, provider API calls, browser work, media
    downloads, screenshots, archive submissions, account/session work, or CAPTCHA/
    access-control bypass. It only inspects the supplied string.
    """
    raw = str(url or "").strip()
    if not raw:
        return _decision(raw, "generic_article", url_kind="empty_input", supported=False, reason="No source URL/path was supplied.")

    if _looks_like_local_path(raw):
        if _is_local_archive(raw):
            return _decision(raw, "local_warc_archive", url_kind="local_archive_package", normalized_host="local", reason="Local WARC/WARC.GZ/WACZ package path.")
        return _decision(raw, "generic_article", url_kind="local_non_archive_path", supported=False, normalized_host="local", route_preference="manual_local_import_only", reason="Local path is not a WARC/WACZ archive package.")

    scheme, host, path = _parsed_host(raw)

    lowered_path = (path or "").lower()
    if scheme not in {"http", "https"}:
        return _decision(raw, "generic_article", url_kind="unsupported_scheme", supported=False, normalized_host=host, reason="Only http(s), file/local archive paths, and explicit local WARC/WACZ packages are classified here.")

    if host == "web.archive.org" and lowered_path.startswith("/web/"):
        return _decision(raw, "archive_wayback", url_kind="wayback_capture_url", normalized_host=host, reason="Wayback capture URL.")
    if host in ARCHIVE_TODAY_HOSTS or host.endswith(".archive.ph"):
        return _decision(raw, "archive_today", url_kind="archive_today_capture_url", normalized_host=host, reason="archive.today/archive.ph candidate URL.")

    if _host_matches(host, YOUTUBE_HOST_SUFFIXES):
        return _decision(raw, "youtube", url_kind="youtube_url", normalized_host=host, reason="YouTube specialist source.")
    if _host_matches(host, TWITTER_X_HOST_SUFFIXES):
        return _decision(raw, "twitter_x", url_kind="twitter_x_public_url", normalized_host=host, reason="X/Twitter specialist public post/profile/thread/media lane.")
    if _host_matches(host, INSTAGRAM_HOST_SUFFIXES):
        return _decision(raw, "instagram", url_kind="instagram_public_url", normalized_host=host, reason="Instagram visual/social specialist lane.")

    if _host_matches(host, BBC_HOST_SUFFIXES) and (
        lowered_path.startswith("/sounds/")
        or lowered_path.startswith("/programmes/")
        or "/sounds/play/" in lowered_path
    ):
        return _decision(raw, "bbc_sounds", url_kind="bbc_sounds_or_programme_audio", normalized_host=host, reason="BBC Sounds/programme audio specialist lane.")

    if _host_matches(host, APPLE_PODCAST_HOST_SUFFIXES):
        return _decision(raw, "apple_podcasts", url_kind="apple_podcast_show_or_episode", normalized_host=host, reason="Apple Podcasts public metadata/RSS-discovery lane.")

    if _host_matches(host, SPOTIFY_HOST_SUFFIXES):
        if lowered_path.startswith("/episode/") or lowered_path.startswith("/show/"):
            return _decision(raw, "spotify_podcast", url_kind="spotify_podcast_show_or_episode", normalized_host=host, reason="Spotify podcast show/episode lane.")
        return _decision(
            raw,
            "spotify_podcast",
            url_kind="spotify_music_or_non_podcast_unsupported",
            supported=False,
            normalized_host=host,
            route_preference=ROUTE_METADATA_ONLY,
            reason="Spotify URL is not a podcast show/episode; music track/album/playlist downloads are out of scope.",
        )

    if lowered_path.endswith((".rss", ".xml", ".atom")) or any(token in lowered_path for token in ("/rss", "/feed", "/podcast")):
        return _decision(raw, "podcast_rss", url_kind="podcast_or_feed_url", normalized_host=host, reason="RSS/feed-style podcast candidate.")

    if _is_media_candidate_path(lowered_path):
        return _decision(raw, "generic_webpage_media", url_kind="direct_public_media_candidate", normalized_host=host, reason="Public direct media/manifest candidate path.")

    return _decision(raw, "generic_article", url_kind="generic_public_webpage_or_article", normalized_host=host, reason="Default public webpage/article family; specialist adapters can override where detected.")


def source_family_ids() -> tuple[str, ...]:
    return tuple(capability.family_id for capability in SOURCE_FAMILY_CAPABILITIES)


def build_sample_decisions() -> tuple[SourceFamilyDecision, ...]:
    samples = (
        "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        "https://cdn.example.test/video.mp4",
        "https://www.bbc.co.uk/programmes/m0031724",
        "https://feeds.example.test/show/podcast.rss",
        "https://podcasts.apple.com/gb/podcast/example-show/id123456789",
        "https://open.spotify.com/episode/1234567890",
        "https://open.spotify.com/track/1234567890",
        "https://www.youtube.com/watch?v=aB3_dE-9xYz",
        "https://x.com/example/status/1234567890",
        "https://www.instagram.com/p/ABC123/",
        "https://web.archive.org/web/20260717224516/https://metro.co.uk/example/",
        "https://archive.ph/6mr3C",
        r"C:\captures\example.warc.gz",
    )
    return tuple(classify_source_family(sample) for sample in samples)


def _check(status: str, check_id: str, detail: str) -> dict[str, str]:
    return {"check_id": check_id, "status": status, "detail": detail}


def validate_source_family_matrix(source_root: str | Path = ".") -> R42GCMatrixReport:
    root = Path(source_root)
    family_ids = source_family_ids()
    present = tuple(family_id for family_id in REQUIRED_FAMILIES if family_id in family_ids)
    missing = tuple(family_id for family_id in REQUIRED_FAMILIES if family_id not in family_ids)
    decisions = build_sample_decisions()
    decision_by_kind = {decision.url_kind: decision for decision in decisions}
    checks: list[dict[str, str]] = []

    checks.append(_check("pass" if not missing else "fail", "required_families_present", f"Required families present: {', '.join(present)}; missing: {', '.join(missing) or 'none'}"))
    checks.append(_check("pass" if len(set(family_ids)) == len(family_ids) else "fail", "family_ids_unique", "Family IDs are unique."))
    checks.append(_check("pass" if all(cap.safe_default_action == "plan_only" for cap in SOURCE_FAMILY_CAPABILITIES) else "fail", "plan_only_defaults", "All family capabilities default to plan-only classification."))

    expected_kinds = {
        "generic_public_webpage_or_article": "generic_article",
        "direct_public_media_candidate": "generic_webpage_media",
        "bbc_sounds_or_programme_audio": "bbc_sounds",
        "podcast_or_feed_url": "podcast_rss",
        "apple_podcast_show_or_episode": "apple_podcasts",
        "spotify_podcast_show_or_episode": "spotify_podcast",
        "youtube_url": "youtube",
        "twitter_x_public_url": "twitter_x",
        "instagram_public_url": "instagram",
        "wayback_capture_url": "archive_wayback",
        "archive_today_capture_url": "archive_today",
        "local_archive_package": "local_warc_archive",
    }
    for kind, expected_family in expected_kinds.items():
        decision = decision_by_kind.get(kind)
        ok = decision is not None and decision.family_id == expected_family and decision.supported
        checks.append(_check("pass" if ok else "fail", f"classifies_{expected_family}", f"{kind} -> {expected_family}"))

    spotify_music = decision_by_kind.get("spotify_music_or_non_podcast_unsupported")
    spotify_music_ok = bool(spotify_music and spotify_music.family_id == "spotify_podcast" and not spotify_music.supported)
    checks.append(_check("pass" if spotify_music_ok else "fail", "spotify_music_not_downloadable", "Spotify music/non-podcast URLs are classified as unsupported, not as downloadable podcast audio."))

    generic_media = _capability("generic_webpage_media")
    checks.append(_check("pass" if generic_media.route_preference == ROUTE_API3128_JDOWNLOADER_FIRST and generic_media.video_audio == STATUS_TESTED_TRUE else "fail", "generic_media_api3128_first", "Generic public webpage media route reflects the R42GB API3128/JDownloader-first validation."))

    bbc = _capability("bbc_sounds")
    bbc_ok = bbc.route_preference == ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY and bbc.video_audio == STATUS_PROVEN_MANUAL_ROUTE
    checks.append(_check("pass" if bbc_ok else "fail", "bbc_sounds_proven_manual_route", "BBC Sounds is source-specific: yt-dlp bestaudio plus ffmpeg audio-copy route, not a global yt-dlp replacement."))

    twitter = _capability("twitter_x")
    checks.append(_check("pass" if twitter.video_audio == STATUS_VALIDATED_CURRENT_METHOD and twitter.comments == STATUS_VALIDATED_CURRENT_METHOD else "fail", "twitter_specialist_current_method", "Twitter/X is validated as a specialist current-method lane after R42GF; completed evidence remains receipt-gated."))

    instagram = _capability("instagram")
    checks.append(_check("pass" if instagram.specialist_layer_required and instagram.video_audio == STATUS_SPECIALIST_REQUIRED else "fail", "instagram_specialist_required", "Instagram remains a specialist visual/social lane with no bypass behaviour."))

    source_adapters_present = (root / "source_adapters.py").is_file()
    r42gb_present = (root / "webpage_video_api3128_route_validation_r42gb.py").is_file()
    checks.append(_check("pass" if source_adapters_present else "warning", "source_adapters_context_present", "source_adapters.py present in supplied source root." if source_adapters_present else "source_adapters.py not present; matrix still runs standalone."))
    checks.append(_check("pass" if r42gb_present else "warning", "r42gb_context_present", "R42GB validation module present in supplied source root." if r42gb_present else "R42GB validation module not present; matrix still runs standalone."))

    conclusion = (
        "R42GC PASS: universal source handling is represented as a source-family capability router. "
        "Generic article/webpage-media paths cover ordinary websites, while BBC Sounds, podcasts, "
        "YouTube, Twitter/X, Instagram, and archive sources remain explicit specialist lanes with "
        "honest tested/not_tested/baseline status boundaries."
    )
    if missing or any(check["status"] == "fail" for check in checks):
        conclusion = "R42GC FAIL: source-family matrix has missing or failed validation checks."

    return R42GCMatrixReport(
        marker=R42GC_MARKER,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(root),
        family_count=len(SOURCE_FAMILY_CAPABILITIES),
        required_families_present=present,
        missing_required_families=missing,
        capabilities=SOURCE_FAMILY_CAPABILITIES,
        sample_decisions=decisions,
        checks=tuple(checks),
        conclusion=conclusion,
    )


def write_report(report: R42GCMatrixReport, output_root: str | Path) -> tuple[Path, Path]:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "r42gc_universal_source_family_matrix.json"
    md_path = out / "r42gc_universal_source_family_matrix.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    pass_count = sum(1 for check in report.checks if check.get("status") == "pass")
    warning_count = sum(1 for check in report.checks if check.get("status") == "warning")
    fail_count = sum(1 for check in report.checks if check.get("status") == "fail")
    lines = [
        "# R42GC Universal Source Adapter Family Matrix",
        "",
        f"Marker: `{report.marker}`",
        f"Passed: `{str(report.passed).lower()}`",
        f"Families: `{report.family_count}`",
        f"Checks: `{pass_count} pass / {warning_count} warning / {fail_count} fail`",
        f"Side effects: `{report.side_effects}`",
        "",
        "## Conclusion",
        "",
        report.conclusion,
        "",
        "## Capability families",
        "",
    ]
    for capability in report.capabilities:
        lines.extend(
            [
                f"### {capability.family_id}",
                "",
                f"- Display: {capability.display_name}",
                f"- Adapter hint: `{capability.adapter_hint}`",
                f"- Route preference: `{capability.route_preference}`",
                f"- Article text: `{capability.article_text}`",
                f"- Comments: `{capability.comments}`",
                f"- Images: `{capability.images}`",
                f"- Video/audio: `{capability.video_audio}`",
                f"- Screenshots: `{capability.screenshots}`",
                f"- WARC: `{capability.warc}`",
                f"- Archive lookup: `{capability.archive_lookup}`",
                f"- Source-role material: `{capability.source_role_material}`",
                f"- Specialist layer required: `{str(capability.specialist_layer_required).lower()}`",
                "",
            ]
        )
        for note in capability.notes:
            lines.append(f"  - {note}")
        lines.append("")
    lines.extend(["## Sample decisions", ""])
    for decision in report.sample_decisions:
        lines.append(
            f"- `{decision.input_url}` -> `{decision.family_id}` / `{decision.url_kind}` / supported=`{str(decision.supported).lower()}`"
        )
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(f"- `{check['status']}` `{check['check_id']}`: {check['detail']}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _main() -> int:
    parser = argparse.ArgumentParser(description="R42GC side-effect-free universal source-family matrix validation.")
    parser.add_argument("--source-root", default=".", help="Project/source root used only for presence checks.")
    parser.add_argument("--output-root", default="", help="Optional folder for JSON/Markdown report output.")
    parser.add_argument("--url", action="append", default=None, help="Classify an additional URL/path; can be supplied multiple times.")
    args = parser.parse_args()

    report = validate_source_family_matrix(args.source_root)
    print("R42GC universal source adapter family matrix")
    print(f"Passed: {str(report.passed).lower()}")
    print(f"Conclusion: {report.conclusion}")
    pass_count = sum(1 for check in report.checks if check.get("status") == "pass")
    warning_count = sum(1 for check in report.checks if check.get("status") == "warning")
    fail_count = sum(1 for check in report.checks if check.get("status") == "fail")
    print(f"Families: {report.family_count}")
    print(f"Checks: {pass_count} pass / {warning_count} warning / {fail_count} fail")
    print(f"Side effects: {report.side_effects}")
    for url in (args.url or ()):
        decision = classify_source_family(url)
        print(f"URL: {url}")
        print(f"  family={decision.family_id} kind={decision.url_kind} supported={str(decision.supported).lower()} route={decision.route_preference}")
    if args.output_root:
        json_path, md_path = write_report(report, args.output_root)
        print(f"JSON: {json_path}")
        print(f"MARKDOWN: {md_path}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())
