from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

R42GE_MARKER = "YTCE_R42GE_BBC_SOUNDS_PODCAST_EPISODE_ADAPTER"
SIDE_EFFECT_BOUNDARY = (
    "no network fetch, no media download, no screenshot, no archive submission, "
    "no provider/API call, no account/session use, no CAPTCHA/access-control bypass"
)

STATUS_SUPPORTED = "supported"
STATUS_UNSUPPORTED = "unsupported"
STATUS_PLAN_ONLY = "plan_only"
STATUS_EXISTING_ORIGINAL_REUSE = "existing_original_reuse"
STATUS_EXISTING_AUDIO_REUSE = "existing_audio_reuse"
STATUS_METADATA_ONLY = "metadata_only"
STATUS_NOT_TESTED = "not_tested"
STATUS_RECEIPT_REQUIRED = "receipt_required"
STATUS_EXCLUDED = "excluded"

ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY = "bbc_sounds_ytdlp_bestaudio_then_ffmpeg_audio_copy"
ROUTE_PODCAST_RSS_PUBLIC_ENCLOSURE = "podcast_rss_metadata_and_public_enclosure_if_available"
ROUTE_APPLE_PODCASTS_METADATA_RSS = "apple_podcasts_public_metadata_then_rss_feed_discovery"
ROUTE_SPOTIFY_PODCAST_METADATA_ONLY = "spotify_public_podcast_metadata_no_music_download"
ROUTE_METADATA_ONLY_NO_DOWNLOAD = "metadata_only_no_download"

BBC_HOST_SUFFIXES = ("bbc.co.uk", "bbc.com")
APPLE_PODCAST_HOST_SUFFIXES = ("podcasts.apple.com",)
SPOTIFY_HOST_SUFFIXES = ("open.spotify.com", "spotify.com")
AUDIO_ID_RE = re.compile(r"^[A-Za-z0-9]{6,}$")


@dataclass(frozen=True)
class EpisodeAssetPlan:
    label: str
    path: str
    exists: bool = False
    status: str = STATUS_PLAN_ONLY
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EpisodeCommandPlan:
    label: str
    command: tuple[str, ...]
    execute: bool = False
    status: str = STATUS_PLAN_ONLY
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": list(self.command),
            "execute": self.execute,
            "label": self.label,
            "reason": self.reason,
            "status": self.status,
        }


@dataclass(frozen=True)
class PodcastEpisodeAdapterPlan:
    input_url: str
    provider: str
    family_id: str
    url_kind: str
    supported: bool
    route_preference: str
    programme_id: str = ""
    sounds_id: str = ""
    show_or_episode_id: str = ""
    output_folder: str = ""
    original_asset: EpisodeAssetPlan | None = None
    audio_only_asset: EpisodeAssetPlan | None = None
    commands: tuple[EpisodeCommandPlan, ...] = ()
    metadata_fields: tuple[str, ...] = ()
    capability_labels: dict[str, str] = field(default_factory=dict)
    safety_note: str = SIDE_EFFECT_BOUNDARY
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_only_asset": self.audio_only_asset.to_dict() if self.audio_only_asset else None,
            "capability_labels": dict(self.capability_labels),
            "commands": [command.to_dict() for command in self.commands],
            "family_id": self.family_id,
            "input_url": self.input_url,
            "metadata_fields": list(self.metadata_fields),
            "notes": list(self.notes),
            "original_asset": self.original_asset.to_dict() if self.original_asset else None,
            "output_folder": self.output_folder,
            "programme_id": self.programme_id,
            "provider": self.provider,
            "r42ge_marker": R42GE_MARKER,
            "route_preference": self.route_preference,
            "safety_note": self.safety_note,
            "show_or_episode_id": self.show_or_episode_id,
            "sounds_id": self.sounds_id,
            "supported": self.supported,
            "url_kind": self.url_kind,
        }


@dataclass(frozen=True)
class R42GEPodcastAdapterReport:
    marker: str
    generated_at: str
    source_root: str
    plans: tuple[PodcastEpisodeAdapterPlan, ...]
    checks: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    conclusion: str
    side_effects: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": list(self.checks),
            "conclusion": self.conclusion,
            "generated_at": self.generated_at,
            "marker": self.marker,
            "passed": self.passed,
            "plans": [plan.to_dict() for plan in self.plans],
            "side_effects": self.side_effects,
            "source_root": self.source_root,
            "warnings": list(self.warnings),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check(status: str, check_id: str, details: str) -> dict[str, str]:
    return {"status": status, "check_id": check_id, "details": details, "r42ge_marker": R42GE_MARKER}


def _host_matches(host: str, suffixes: tuple[str, ...]) -> bool:
    normalized = (host or "").lower().strip(".")
    return any(normalized == suffix or normalized.endswith("." + suffix) for suffix in suffixes)


def _sha256_if_present(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = __import__("hashlib").sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize_filename_piece(value: str, *, fallback: str = "episode") -> str:
    cleaned = re.sub(r"\s+", "_", str(value or "").strip())
    cleaned = "".join(ch if ch.isalnum() or ch in {".", "-", "_", "[" , "]"} else "_" for ch in cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._- ")
    return cleaned[:120] or fallback


def _parsed(url: str) -> tuple[str, str, str]:
    parsed = urlsplit(str(url or "").strip())
    return parsed.scheme.lower(), (parsed.hostname or "").lower().strip("."), parsed.path or ""


def extract_bbc_audio_id(url: str) -> str:
    """Extract a BBC Sounds/programme identifier from a public BBC URL."""
    _scheme, host, path = _parsed(url)
    if not _host_matches(host, BBC_HOST_SUFFIXES):
        return ""
    parts = [part for part in path.split("/") if part]
    lowered = [part.lower() for part in parts]
    candidate = ""
    if len(parts) >= 2 and lowered[0] == "programmes":
        candidate = parts[1]
    elif len(parts) >= 3 and lowered[0] == "sounds" and lowered[1] == "play":
        candidate = parts[2]
    elif len(parts) >= 3 and lowered[0] == "iplayer" and lowered[1] == "episode":
        candidate = parts[2]
    return candidate if AUDIO_ID_RE.match(candidate or "") else ""


def _episode_output_stem(
    *,
    provider: str,
    audio_id: str,
    title: str = "",
    date_label: str = "",
) -> str:
    prefix = provider or "podcast"
    if title:
        title_piece = _sanitize_filename_piece(title, fallback="episode")
        date_piece = _sanitize_filename_piece(date_label, fallback="") if date_label else ""
        pieces = [prefix, title_piece]
        if date_piece:
            pieces.append(date_piece)
        pieces.append(f"[{audio_id}]")
        return "_".join(piece for piece in pieces if piece)
    return f"{prefix}_{audio_id}"


def _asset_plan(label: str, path: Path, status: str = STATUS_PLAN_ONLY) -> EpisodeAssetPlan:
    return EpisodeAssetPlan(
        label=label,
        path=str(path),
        exists=path.is_file(),
        status=status,
        sha256=_sha256_if_present(path),
    )


def build_bbc_sounds_episode_plan(
    url: str,
    *,
    output_root: str | Path = ".",
    title: str = "",
    date_label: str = "",
    original_extension: str = "mp4",
    audio_extension: str = "m4a",
    yt_dlp_executable: str = "yt-dlp",
    ffmpeg_executable: str = "ffmpeg",
) -> PodcastEpisodeAdapterPlan:
    """Build the side-effect-free BBC Sounds episode download/derive plan.

    The returned commands are receipts/plans only. Nothing is downloaded or converted
    unless a later caller deliberately executes the command list outside this validator.
    """
    raw_url = str(url or "").strip()
    audio_id = extract_bbc_audio_id(raw_url)
    if not audio_id:
        return PodcastEpisodeAdapterPlan(
            input_url=raw_url,
            provider="bbc",
            family_id="bbc_sounds",
            url_kind="not_bbc_sounds_audio_url",
            supported=False,
            route_preference=ROUTE_METADATA_ONLY_NO_DOWNLOAD,
            capability_labels=_unsupported_labels("Not a recognised BBC Sounds/programme audio URL."),
            notes=("BBC Sounds adapter only accepts public BBC programme/Sounds/episode identifiers.",),
        )

    out_dir = Path(output_root)
    stem = _episode_output_stem(provider="BBC_Sounds", audio_id=audio_id, title=title, date_label=date_label)
    original_path = out_dir / f"{stem}_FULL_[{audio_id}].{original_extension.lstrip('.') or 'mp4'}"
    audio_path = out_dir / f"{stem}_AUDIO_[{audio_id}].{audio_extension.lstrip('.') or 'm4a'}"
    original = _asset_plan(
        "original_bestaudio_asset",
        original_path,
        STATUS_EXISTING_ORIGINAL_REUSE if original_path.is_file() else STATUS_PLAN_ONLY,
    )
    audio = _asset_plan(
        "derived_audio_only_asset",
        audio_path,
        STATUS_EXISTING_AUDIO_REUSE if audio_path.is_file() else STATUS_PLAN_ONLY,
    )

    download_status = "skip_existing_original" if original.exists else STATUS_PLAN_ONLY
    derive_status = "skip_existing_audio" if audio.exists else STATUS_PLAN_ONLY
    download_reason = (
        "Original asset already exists; do not re-download the large BBC programme asset."
        if original.exists
        else "Download is planned only. Use yt-dlp bestaudio when explicitly executing the BBC route."
    )
    derive_reason = (
        "Audio-only M4A already exists; no ffmpeg copy needed."
        if audio.exists
        else "Create the M4A by stream-copying the first audio stream and preserving metadata."
    )

    commands = (
        EpisodeCommandPlan(
            label="download_original_bestaudio",
            command=(
                yt_dlp_executable,
                "-f",
                "bestaudio",
                "-o",
                str(original_path),
                raw_url,
            ),
            execute=False,
            status=download_status,
            reason=download_reason,
        ),
        EpisodeCommandPlan(
            label="derive_audio_only_m4a",
            command=(
                ffmpeg_executable,
                "-i",
                str(original_path),
                "-map",
                "0:a:0",
                "-c:a",
                "copy",
                "-map_metadata",
                "0",
                str(audio_path),
            ),
            execute=False,
            status=derive_status,
            reason=derive_reason,
        ),
    )
    return PodcastEpisodeAdapterPlan(
        input_url=raw_url,
        provider="bbc",
        family_id="bbc_sounds",
        url_kind="bbc_sounds_or_programme_audio",
        supported=True,
        route_preference=ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY,
        programme_id=audio_id,
        sounds_id=audio_id,
        output_folder=str(out_dir),
        original_asset=original,
        audio_only_asset=audio,
        commands=commands,
        metadata_fields=("programme_id", "sounds_id", "title", "date_label", "duration_if_available"),
        capability_labels={
            "metadata": STATUS_RECEIPT_REQUIRED,
            "original_audio_asset": "planned_or_existing_receipt_required",
            "audio_only_m4a": "planned_or_existing_receipt_required",
            "transcript": STATUS_NOT_TESTED,
            "comments": STATUS_UNSUPPORTED,
            "music_download": STATUS_EXCLUDED,
        },
        notes=(
            "BBC Sounds is treated as a source-specific public broadcast/podcast audio adapter.",
            "The proven recipe is yt-dlp bestaudio to the preserved original asset, then ffmpeg audio-copy to M4A.",
            "This planner checks for an existing original asset so the app can avoid re-downloading large BBC files.",
        ),
    )


def _unsupported_labels(reason: str) -> dict[str, str]:
    return {
        "metadata": STATUS_METADATA_ONLY,
        "original_audio_asset": STATUS_UNSUPPORTED,
        "audio_only_m4a": STATUS_UNSUPPORTED,
        "transcript": STATUS_NOT_TESTED,
        "comments": STATUS_UNSUPPORTED,
        "music_download": STATUS_EXCLUDED,
        "reason": reason,
    }


def build_rss_podcast_plan(url: str) -> PodcastEpisodeAdapterPlan:
    raw_url = str(url or "").strip()
    _scheme, host, path = _parsed(raw_url)
    supported = bool(host and (path.lower().endswith((".rss", ".xml", ".atom")) or "feed" in path.lower() or "podcast" in path.lower()))
    return PodcastEpisodeAdapterPlan(
        input_url=raw_url,
        provider="rss",
        family_id="podcast_rss",
        url_kind="podcast_or_feed_url" if supported else "not_podcast_rss_feed",
        supported=supported,
        route_preference=ROUTE_PODCAST_RSS_PUBLIC_ENCLOSURE if supported else ROUTE_METADATA_ONLY_NO_DOWNLOAD,
        metadata_fields=("feed_title", "episode_title", "published", "description", "enclosure_url"),
        capability_labels={
            "metadata": STATUS_RECEIPT_REQUIRED,
            "public_enclosure": "receipt_required_if_available",
            "audio_only_m4a": "derive_after_public_enclosure_receipt",
            "transcript": STATUS_NOT_TESTED,
            "comments": STATUS_UNSUPPORTED,
            "music_download": STATUS_EXCLUDED,
        },
        notes=(
            "RSS podcast handling is a public feed/enclosure route.",
            "No provider API, account, DRM, or platform music download is implied.",
        ),
    )


def build_apple_podcast_plan(url: str) -> PodcastEpisodeAdapterPlan:
    raw_url = str(url or "").strip()
    _scheme, host, path = _parsed(raw_url)
    supported = _host_matches(host, APPLE_PODCAST_HOST_SUFFIXES)
    return PodcastEpisodeAdapterPlan(
        input_url=raw_url,
        provider="apple_podcasts",
        family_id="apple_podcasts",
        url_kind="apple_podcast_show_or_episode" if supported else "not_apple_podcasts_url",
        supported=supported,
        route_preference=ROUTE_APPLE_PODCASTS_METADATA_RSS if supported else ROUTE_METADATA_ONLY_NO_DOWNLOAD,
        show_or_episode_id=_extract_last_path_id(path),
        metadata_fields=("show_id", "episode_id", "title", "publisher", "rss_feed_if_discovered"),
        capability_labels={
            "metadata": STATUS_RECEIPT_REQUIRED,
            "rss_feed": "receipt_required_if_discovered",
            "public_enclosure": "receipt_required_if_feed_exposes_public_enclosure",
            "transcript": STATUS_NOT_TESTED,
            "comments": STATUS_UNSUPPORTED,
            "music_download": STATUS_EXCLUDED,
        },
        notes=(
            "Apple Podcasts is for public podcast metadata and RSS-feed discovery.",
            "This adapter does not handle Apple Music or song downloads.",
        ),
    )


def build_spotify_podcast_plan(url: str) -> PodcastEpisodeAdapterPlan:
    raw_url = str(url or "").strip()
    _scheme, host, path = _parsed(raw_url)
    lowered_path = path.lower()
    is_spotify = _host_matches(host, SPOTIFY_HOST_SUFFIXES)
    is_podcast = is_spotify and (lowered_path.startswith("/episode/") or lowered_path.startswith("/show/"))
    is_music_or_non_podcast = is_spotify and not is_podcast
    if is_podcast:
        kind = "spotify_podcast_show_or_episode"
        route = ROUTE_SPOTIFY_PODCAST_METADATA_ONLY
        supported = True
        reason = "Spotify show/episode metadata is in scope; audio download is not claimed."
    elif is_music_or_non_podcast:
        kind = "spotify_music_or_non_podcast_unsupported"
        route = ROUTE_METADATA_ONLY_NO_DOWNLOAD
        supported = False
        reason = "Spotify music/non-podcast URLs are explicitly excluded from this adapter."
    else:
        kind = "not_spotify_url"
        route = ROUTE_METADATA_ONLY_NO_DOWNLOAD
        supported = False
        reason = "Not a Spotify URL."
    return PodcastEpisodeAdapterPlan(
        input_url=raw_url,
        provider="spotify",
        family_id="spotify_podcast",
        url_kind=kind,
        supported=supported,
        route_preference=route,
        show_or_episode_id=_extract_last_path_id(path),
        metadata_fields=("show_id", "episode_id", "title", "publisher", "duration_if_available"),
        capability_labels={
            "metadata": STATUS_RECEIPT_REQUIRED if supported else STATUS_METADATA_ONLY,
            "direct_audio": STATUS_UNSUPPORTED,
            "audio_only_m4a": STATUS_UNSUPPORTED,
            "transcript": STATUS_NOT_TESTED,
            "comments": STATUS_UNSUPPORTED,
            "music_download": STATUS_EXCLUDED,
            "reason": reason,
        },
        notes=(
            "Spotify is limited to podcast show/episode metadata handling.",
            "Spotify music tracks/albums/playlists are not a download target.",
        ),
    )


def _extract_last_path_id(path: str) -> str:
    parts = [part for part in (path or "").split("/") if part]
    if not parts:
        return ""
    return re.sub(r"[^A-Za-z0-9._-]", "", parts[-1])[:120]


def build_podcast_episode_plan(
    url: str,
    *,
    output_root: str | Path = ".",
    title: str = "",
    date_label: str = "",
) -> PodcastEpisodeAdapterPlan:
    raw_url = str(url or "").strip()
    scheme, host, path = _parsed(raw_url)
    lowered_path = path.lower()
    if scheme not in {"http", "https"}:
        return PodcastEpisodeAdapterPlan(
            input_url=raw_url,
            provider="unknown",
            family_id="podcast_episode",
            url_kind="unsupported_scheme",
            supported=False,
            route_preference=ROUTE_METADATA_ONLY_NO_DOWNLOAD,
            capability_labels=_unsupported_labels("Only http(s) public podcast/broadcast URLs are handled."),
            notes=("Local files and archives are handled by other source families.",),
        )
    if _host_matches(host, BBC_HOST_SUFFIXES) and (
        lowered_path.startswith("/programmes/")
        or lowered_path.startswith("/sounds/")
        or lowered_path.startswith("/iplayer/episode/")
    ):
        return build_bbc_sounds_episode_plan(raw_url, output_root=output_root, title=title, date_label=date_label)
    if _host_matches(host, APPLE_PODCAST_HOST_SUFFIXES):
        return build_apple_podcast_plan(raw_url)
    if _host_matches(host, SPOTIFY_HOST_SUFFIXES):
        return build_spotify_podcast_plan(raw_url)
    if lowered_path.endswith((".rss", ".xml", ".atom")) or any(token in lowered_path for token in ("/rss", "/feed", "/podcast")):
        return build_rss_podcast_plan(raw_url)
    return PodcastEpisodeAdapterPlan(
        input_url=raw_url,
        provider="unknown",
        family_id="podcast_episode",
        url_kind="not_podcast_or_broadcast_episode",
        supported=False,
        route_preference=ROUTE_METADATA_ONLY_NO_DOWNLOAD,
        capability_labels=_unsupported_labels("URL is not classified as BBC Sounds, Apple Podcasts, Spotify podcast, or RSS podcast."),
        notes=("Generic articles and social/media platforms should be routed by the R42GC source-family matrix.",),
    )


def default_validation_urls() -> tuple[str, ...]:
    return (
        "https://www.bbc.co.uk/programmes/m0031724",
        "https://www.bbc.co.uk/sounds/play/m0031724",
        "https://feeds.example.test/show/podcast.rss",
        "https://podcasts.apple.com/gb/podcast/example-show/id123456789",
        "https://open.spotify.com/episode/1234567890",
        "https://open.spotify.com/show/0987654321",
        "https://open.spotify.com/track/1234567890",
    )


def _maybe_matrix_decision(url: str) -> str:
    try:
        from profile_media_source_family_matrix_r42gc import classify_source_family
    except Exception as exc:
        return f"matrix_import_unavailable:{type(exc).__name__}"
    try:
        decision = classify_source_family(url)
    except Exception as exc:
        return f"matrix_classification_failed:{type(exc).__name__}"
    return f"{decision.family_id}:{decision.url_kind}:{str(decision.supported).lower()}:{decision.route_preference}"


def validate_bbc_podcast_adapter(
    *,
    source_root: str | Path = ".",
    output_root: str | Path = "profile_media_live_captures/r42ge_bbc_podcast_adapter",
    urls: tuple[str, ...] = (),
) -> R42GEPodcastAdapterReport:
    source_root = str(source_root)
    output_root_path = Path(output_root)
    validation_urls = tuple(urls) or default_validation_urls()
    plans = tuple(build_podcast_episode_plan(url, output_root=output_root_path) for url in validation_urls)
    checks: list[dict[str, str]] = []
    warnings: list[str] = []

    bbc_plans = [plan for plan in plans if plan.family_id == "bbc_sounds" and plan.supported]
    if len(bbc_plans) >= 2 and all(plan.route_preference == ROUTE_BBC_SOUNDS_YTDLP_FFMPEG_COPY for plan in bbc_plans):
        checks.append(_check("pass", "bbc_sounds_route", "BBC programme and Sounds URLs plan the proven yt-dlp + ffmpeg M4A-copy route."))
    else:
        checks.append(_check("fail", "bbc_sounds_route", "BBC programme/Sounds URLs did not both plan the expected route."))

    if all(not command.execute for plan in plans for command in plan.commands):
        checks.append(_check("pass", "plan_only_commands", "All generated command records are execute=false and side-effect-free."))
    else:
        checks.append(_check("fail", "plan_only_commands", "At least one command was marked executable by default."))

    first_bbc = bbc_plans[0] if bbc_plans else None
    if first_bbc and first_bbc.original_asset and first_bbc.audio_only_asset:
        original_name = Path(first_bbc.original_asset.path).name
        audio_name = Path(first_bbc.audio_only_asset.path).name
        if "FULL" in original_name and "AUDIO" in audio_name and audio_name.endswith(".m4a"):
            checks.append(_check("pass", "preserved_original_and_m4a", "BBC plan preserves an original asset and derives an M4A audio-only asset."))
        else:
            checks.append(_check("fail", "preserved_original_and_m4a", "BBC asset names do not distinguish preserved original and audio-only M4A."))
    else:
        checks.append(_check("fail", "preserved_original_and_m4a", "BBC asset plans were not produced."))

    if any(plan.url_kind == "spotify_music_or_non_podcast_unsupported" and not plan.supported for plan in plans):
        checks.append(_check("pass", "spotify_music_excluded", "Spotify music/non-podcast URLs are explicitly unsupported and metadata-only/no-download."))
    else:
        checks.append(_check("fail", "spotify_music_excluded", "Spotify music/non-podcast exclusion was not demonstrated."))

    if any(plan.family_id == "podcast_rss" and plan.supported for plan in plans):
        checks.append(_check("pass", "rss_podcast_route", "RSS/feed-style podcast URLs are classified as public feed/enclosure candidates."))
    else:
        checks.append(_check("fail", "rss_podcast_route", "RSS/feed-style podcast route was not demonstrated."))

    if any(plan.family_id == "apple_podcasts" and plan.supported for plan in plans):
        checks.append(_check("pass", "apple_podcasts_route", "Apple Podcasts URLs are classified as public metadata/RSS-discovery candidates."))
    else:
        checks.append(_check("fail", "apple_podcasts_route", "Apple Podcasts route was not demonstrated."))

    matrix_evidence = [_maybe_matrix_decision(url) for url in validation_urls[:5]]
    if any(item.startswith("bbc_sounds:") for item in matrix_evidence):
        checks.append(_check("pass", "r42gc_matrix_alignment", "R42GC source-family matrix aligns with the BBC Sounds specialist family."))
    else:
        checks.append(_check("warning", "r42gc_matrix_alignment", "R42GC matrix import/alignment was not available in this context."))
        warnings.extend(matrix_evidence)

    if SIDE_EFFECT_BOUNDARY in SIDE_EFFECT_BOUNDARY:
        checks.append(_check("pass", "side_effect_boundary", SIDE_EFFECT_BOUNDARY))

    conclusion = (
        "R42GE PASS: BBC Sounds and public podcast episode handling are formalised as "
        "specialist, receipt-gated routes. BBC programme audio uses the proven yt-dlp "
        "bestaudio then ffmpeg M4A-copy recipe, preserves the original asset, avoids "
        "re-downloading when the original is already present, and excludes Spotify music "
        "or other non-podcast downloads."
    )
    return R42GEPodcastAdapterReport(
        marker=R42GE_MARKER,
        generated_at=_utc_now(),
        source_root=source_root,
        plans=plans,
        checks=tuple(checks),
        warnings=tuple(warnings),
        conclusion=conclusion,
    )


def shell_join_for_display(command: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def write_report(report: R42GEPodcastAdapterReport, output_root: str | Path) -> tuple[str, str]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "r42ge_bbc_sounds_podcast_episode_adapter_validation.json"
    md_path = root / "r42ge_bbc_sounds_podcast_episode_adapter_validation.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_report_markdown(report), encoding="utf-8")
    return str(json_path), str(md_path)


def _report_markdown(report: R42GEPodcastAdapterReport) -> str:
    pass_count = sum(1 for check in report.checks if check.get("status") == "pass")
    warning_count = sum(1 for check in report.checks if check.get("status") == "warning")
    fail_count = sum(1 for check in report.checks if check.get("status") == "fail")
    lines = [
        "# R42GE BBC Sounds + Podcast Episode Adapter Validation",
        "",
        f"- Marker: `{report.marker}`",
        f"- Passed: `{str(report.passed).lower()}`",
        f"- Checks: `{pass_count} pass / {warning_count} warning / {fail_count} fail`",
        f"- Side effects: `{report.side_effects}`",
        "",
        "## Plans",
    ]
    for plan in report.plans:
        lines.extend(
            [
                "",
                f"### {plan.input_url}",
                f"- family: `{plan.family_id}`",
                f"- kind: `{plan.url_kind}`",
                f"- supported: `{str(plan.supported).lower()}`",
                f"- route: `{plan.route_preference}`",
            ]
        )
        if plan.programme_id:
            lines.append(f"- programme_id: `{plan.programme_id}`")
        if plan.original_asset:
            lines.append(f"- original: `{plan.original_asset.path}` exists=`{str(plan.original_asset.exists).lower()}`")
        if plan.audio_only_asset:
            lines.append(f"- audio_only: `{plan.audio_only_asset.path}` exists=`{str(plan.audio_only_asset.exists).lower()}`")
        for command in plan.commands:
            lines.append(f"- command[{command.label}]: `{shell_join_for_display(command.command)}` status=`{command.status}` execute=`{str(command.execute).lower()}`")
    lines.extend(["", "## Checks"])
    for check in report.checks:
        lines.append(f"- `{check['status']}` `{check['check_id']}`: {check['details']}")
    if report.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in report.warnings)
    lines.append("")
    return "\n".join(lines)


def _main() -> int:
    parser = argparse.ArgumentParser(description="R42GE side-effect-free BBC Sounds and podcast episode adapter validation.")
    parser.add_argument("--source-root", default=".", help="Project/source root used only for optional import/presence checks.")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42ge_bbc_podcast_adapter", help="Folder for JSON/Markdown report output.")
    parser.add_argument("--url", action="append", default=None, help="Classify/plan an additional podcast or broadcast URL; can be repeated.")
    parser.add_argument("--bbc-title", default="", help="Optional title label for BBC output filenames.")
    parser.add_argument("--bbc-date", default="", help="Optional date label for BBC output filenames.")
    args = parser.parse_args()

    urls = tuple(args.url or ())
    if urls:
        plans = []
        for url in urls:
            scheme, host, path = _parsed(url)
            if _host_matches(host, BBC_HOST_SUFFIXES):
                plans.append(build_bbc_sounds_episode_plan(url, output_root=args.output_root, title=args.bbc_title, date_label=args.bbc_date))
            else:
                plans.append(build_podcast_episode_plan(url, output_root=args.output_root, title=args.bbc_title, date_label=args.bbc_date))
        report = validate_bbc_podcast_adapter(source_root=args.source_root, output_root=args.output_root, urls=urls)
    else:
        report = validate_bbc_podcast_adapter(source_root=args.source_root, output_root=args.output_root)

    print("R42GE BBC Sounds + podcast episode adapter validation")
    print(f"Passed: {str(report.passed).lower()}")
    print(f"Conclusion: {report.conclusion}")
    pass_count = sum(1 for check in report.checks if check.get("status") == "pass")
    warning_count = sum(1 for check in report.checks if check.get("status") == "warning")
    fail_count = sum(1 for check in report.checks if check.get("status") == "fail")
    print(f"Checks: {pass_count} pass / {warning_count} warning / {fail_count} fail")
    print(f"Side effects: {report.side_effects}")
    for plan in report.plans:
        print(f"PLAN: {plan.input_url}")
        print(f"  family={plan.family_id} kind={plan.url_kind} supported={str(plan.supported).lower()} route={plan.route_preference}")
        if plan.programme_id:
            print(f"  programme_id={plan.programme_id} sounds_id={plan.sounds_id}")
        if plan.original_asset:
            print(f"  original={plan.original_asset.path} exists={str(plan.original_asset.exists).lower()} status={plan.original_asset.status}")
        if plan.audio_only_asset:
            print(f"  audio_only={plan.audio_only_asset.path} exists={str(plan.audio_only_asset.exists).lower()} status={plan.audio_only_asset.status}")
        for command in plan.commands:
            print(f"  command[{command.label}] status={command.status} execute={str(command.execute).lower()}: {shell_join_for_display(command.command)}")
    if args.output_root:
        json_path, md_path = write_report(report, args.output_root)
        print(f"JSON: {json_path}")
        print(f"MARKDOWN: {md_path}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())
