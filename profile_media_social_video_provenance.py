"""Social-media/video provenance preview fields for Profile/Media HOME.

This module parses local notes only.  It separates provenance fields without
downloading media, contacting platforms, or deciding claim truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

PROFILE_MEDIA_SOCIAL_VIDEO_PROVENANCE_SCHEMA_VERSION = "profile-media-social-video-provenance-v76p"

URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)


@dataclass(frozen=True)
class SocialVideoProvenanceReview:
    uploader_account: str = ""
    speaker: str = ""
    original_programme_channel_source: str = ""
    clip_holder: str = ""
    transcripted_statement: str = ""
    archive_url: str = ""
    source_url: str = ""
    platform_logo_or_watermark: str = ""
    platform_marker_only: bool = False
    claim_affiliation_proven: bool = False
    claim_subject_affiliation_gap: bool = False
    review_lanes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    web_download_performed: bool = False
    crawling_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    schema_version: str = PROFILE_MEDIA_SOCIAL_VIDEO_PROVENANCE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_lanes"] = list(self.review_lanes)
        payload["warnings"] = list(self.warnings)
        return payload


def _dedupe(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return tuple(output)


def extract_urls(text: object) -> tuple[str, ...]:
    return _dedupe(match.group(0).rstrip(".,;]") for match in URL_RE.finditer(str(text or "")))


def _is_archive_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(part in host for part in ("web.archive.org", "archive.today", "archive.ph", "archive.is"))


def _field(text: str, *labels: str) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?im)^\s*(?:{label_pattern})\s*[:=-]\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else ""


def build_social_video_provenance_review(text: object, *, source_urls: Sequence[str] = (), media_reference_count: int = 0) -> SocialVideoProvenanceReview:
    raw = str(text or "")
    urls = tuple(source_urls) if source_urls else extract_urls(raw)
    archive_url = next((url for url in urls if _is_archive_url(url)), "")
    social_video_url = next(
        (
            url
            for url in urls
            if not _is_archive_url(url)
            and any(marker in url.lower() for marker in ("x.com", "twitter.com", "youtube.com", "youtu.be", "vimeo.com"))
        ),
        "",
    )
    source_url = social_video_url or next((url for url in urls if not _is_archive_url(url)), "")
    uploader = _field(raw, "uploader", "uploader/account", "account", "posted by")
    speaker = _field(raw, "speaker", "speaker/person")
    original_source = _field(raw, "original programme", "original program", "original channel", "original source", "programme", "channel")
    clip_holder = _field(raw, "clip holder", "holder")
    transcripted_statement = _field(raw, "transcripted statement", "transcript", "statement")
    logo = _field(raw, "platform logo", "watermark", "logo")
    if not logo:
        lowered = raw.lower()
        if "clash report" in lowered:
            logo = "Clash Report"
        elif "youtube" in lowered:
            logo = "YouTube"
        elif "x.com" in lowered or "twitter.com" in lowered:
            logo = "X/Twitter"

    platform_marker_only = bool(logo) and not bool(uploader or speaker or original_source or clip_holder)
    has_social_or_video = bool(urls or media_reference_count or uploader or speaker or original_source or clip_holder or transcripted_statement or logo)
    affiliation_proven = bool(re.search(r"(?im)^\s*(claim subject affiliation|affiliation)\s*[:=-]\s*(yes|true|explicit|shown)\s*$", raw))
    gap = has_social_or_video and not affiliation_proven
    lanes: list[str] = []
    warnings: list[str] = []
    if has_social_or_video:
        lanes.append("social_media_video_provenance_review")
    if gap:
        lanes.append("claim_subject_affiliation_review")
        warnings.append("claim_subject_affiliation_gap")
    if platform_marker_only:
        warnings.append("platform_logo_or_watermark_is_not_claim_affiliation")
    if source_url and not uploader:
        warnings.append("uploader_account_not_explicit")
    return SocialVideoProvenanceReview(
        uploader_account=uploader,
        speaker=speaker,
        original_programme_channel_source=original_source,
        clip_holder=clip_holder,
        transcripted_statement=transcripted_statement,
        archive_url=archive_url,
        source_url=source_url,
        platform_logo_or_watermark=logo,
        platform_marker_only=platform_marker_only,
        claim_affiliation_proven=affiliation_proven,
        claim_subject_affiliation_gap=gap,
        review_lanes=_dedupe(lanes),
        warnings=_dedupe(warnings),
    )
