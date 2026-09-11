from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from webpage_video_api3128_route_r42fx import API3128_BACKEND_ID, API3128_ROUTE_USED, YTDLP_ROLE

R42FX_MARKER = "YTCE_R42FX_UNIVERSAL_SOURCE_CAPABILITY_MATRIX"
STATUS_TESTED_TRUE = "tested_true"
STATUS_IMPLEMENTED = "implemented"
STATUS_NOT_TESTED = "not_tested"
STATUS_BASELINE_EXISTS_NOT_CLOSED = "baseline_exists_not_closed"
STATUS_AVAILABLE = "available"
STATUS_SUPPLIED = "supplied"


@dataclass(frozen=True)
class UniversalSiteCapability:
    site_key: str
    adapter_id: str
    article_text: str
    comments: str
    screenshots: str
    warc: str
    images: str
    video_audio: str
    archive_lookup: str
    media_route_preference: str
    source_role_counter: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "archive_lookup": self.archive_lookup,
            "article_text": self.article_text,
            "comments": self.comments,
            "images": self.images,
            "media_route_preference": self.media_route_preference,
            "notes": list(self.notes),
            "r42fx_marker": R42FX_MARKER,
            "screenshots": self.screenshots,
            "site_key": self.site_key,
            "source_role_counter": self.source_role_counter,
            "video_audio": self.video_audio,
            "warc": self.warc,
        }


@dataclass(frozen=True)
class ArchiveCandidate:
    provider: str
    url: str
    status: str
    original_url: str = ""
    saved_at: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "original_url": self.original_url,
            "provider": self.provider,
            "saved_at": self.saved_at,
            "status": self.status,
            "url": self.url,
        }


@dataclass(frozen=True)
class UniversalSourceAvailabilityScan:
    live_url: str
    site_key: str
    capability: UniversalSiteCapability
    archive_candidates: tuple[ArchiveCandidate, ...]
    side_effects_performed: bool = False
    generated_at: str = ""
    summary_lines: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_candidates": [candidate.to_dict() for candidate in self.archive_candidates],
            "capability": self.capability.to_dict(),
            "generated_at": self.generated_at,
            "live_url": self.live_url,
            "r42fx_marker": R42FX_MARKER,
            "side_effects_performed": self.side_effects_performed,
            "site_key": self.site_key,
            "summary_lines": list(self.summary_lines),
        }


MSN_CAPABILITY = UniversalSiteCapability(
    site_key="msn",
    adapter_id="msn",
    article_text=STATUS_TESTED_TRUE,
    comments=STATUS_TESTED_TRUE,
    screenshots=STATUS_TESTED_TRUE,
    warc=STATUS_IMPLEMENTED,
    images=STATUS_IMPLEMENTED,
    video_audio=STATUS_IMPLEMENTED,
    archive_lookup=STATUS_IMPLEMENTED,
    media_route_preference="browser_edge_discovery_plus_jdownloader_api3128_where_media_candidates_exist",
    source_role_counter="works_from_material_receipts_when capture supplies article/comment material",
    notes=("Use MSN as the proven news-site model for universalising reusable browser/text/screenshot/WARC layers.",),
)

METRO_CAPABILITY = UniversalSiteCapability(
    site_key="metro",
    adapter_id="news_website",
    article_text=STATUS_TESTED_TRUE,
    comments=STATUS_NOT_TESTED,
    screenshots=STATUS_TESTED_TRUE,
    warc=STATUS_IMPLEMENTED,
    images=STATUS_IMPLEMENTED,
    video_audio=STATUS_IMPLEMENTED,
    archive_lookup=STATUS_IMPLEMENTED,
    media_route_preference="edge_browser_discovery_then_jdownloader_api3128_primary_for_selected_public_media",
    source_role_counter="needs archive/material role-counter replay before marking fully closed",
    notes=(
        "Metro article text extraction and screenshots are treated as tested true from project context.",
        "Metro comments remain NOT_TESTED until a real comment capture/review run exercises them.",
        "Archive.ph/Wayback inputs are scanned as supplied candidates without submitting new archives.",
    ),
)

TWITTER_X_CAPABILITY = UniversalSiteCapability(
    site_key="twitter_x",
    adapter_id="twitter_x",
    article_text="post_text_baseline",
    comments=STATUS_BASELINE_EXISTS_NOT_CLOSED,
    screenshots=STATUS_IMPLEMENTED,
    warc=STATUS_IMPLEMENTED,
    images=STATUS_IMPLEMENTED,
    video_audio=STATUS_IMPLEMENTED,
    archive_lookup=STATUS_IMPLEMENTED,
    media_route_preference="jdownloader_api3128_primary_for_public_media_candidates",
    source_role_counter="separate Twitter/X closeout still required",
    notes=("Do not mark Twitter/X closed from this Metro/source adapter patch.",),
)

YOUTUBE_CAPABILITY = UniversalSiteCapability(
    site_key="youtube",
    adapter_id="youtube",
    article_text="not_applicable",
    comments=STATUS_TESTED_TRUE,
    screenshots=STATUS_IMPLEMENTED,
    warc="not_primary_path",
    images=STATUS_IMPLEMENTED,
    video_audio=STATUS_TESTED_TRUE,
    archive_lookup="not_primary_path",
    media_route_preference="api3128_backed_jdownloader_internal_bridge_primary",
    source_role_counter="youtube runtime metadata/source rows available; not part of Metro archive scan",
    notes=(f"Backend {API3128_BACKEND_ID}/{API3128_ROUTE_USED}; yt-dlp role is {YTDLP_ROLE}.",),
)

GENERIC_NEWS_CAPABILITY = UniversalSiteCapability(
    site_key="generic_news",
    adapter_id="news_website",
    article_text="site_specific_or_manual_receipt_required",
    comments=STATUS_NOT_TESTED,
    screenshots=STATUS_IMPLEMENTED,
    warc=STATUS_IMPLEMENTED,
    images=STATUS_IMPLEMENTED,
    video_audio=STATUS_IMPLEMENTED,
    archive_lookup=STATUS_IMPLEMENTED,
    media_route_preference="edge_browser_discovery_then_jdownloader_api3128_for_selected_public_media",
    source_role_counter="depends_on_site_specific_material_receipts",
    notes=("Generic news rows should inherit universal capture scaffolding without pretending every site is tested.",),
)

SITE_CAPABILITY_MATRIX = {
    capability.site_key: capability
    for capability in (MSN_CAPABILITY, METRO_CAPABILITY, TWITTER_X_CAPABILITY, YOUTUBE_CAPABILITY, GENERIC_NEWS_CAPABILITY)
}


def detect_site_key(url: str) -> str:
    host = (urlsplit(str(url or "")).hostname or "").lower()
    if host.endswith("msn.com"):
        return "msn"
    if host.endswith("metro.co.uk"):
        return "metro"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "twitter_x"
    if "youtube.com" in host or host == "youtu.be":
        return "youtube"
    return "generic_news"


def classify_archive_candidate(url: str, *, live_url: str = "") -> ArchiveCandidate:
    text = str(url or "").strip()
    parsed = urlsplit(text)
    host = (parsed.hostname or "").lower()
    provider = "unknown"
    saved_at = ""
    original_url = live_url
    if host == "web.archive.org":
        provider = "wayback"
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "web":
            raw_stamp = parts[1]
            if raw_stamp.isdigit() and len(raw_stamp) >= 8:
                saved_at = raw_stamp
            if len(parts) >= 3:
                original_url = "/".join(parts[2:])
                if original_url.startswith(("http:/", "https:/")) and not original_url.startswith(("http://", "https://")):
                    original_url = original_url.replace("http:/", "http://", 1).replace("https:/", "https://", 1)
    elif host in {"archive.ph", "archive.today", "archive.is", "archive.vn", "archive.md"} or host.endswith("archive.ph") or host.endswith("archive.today"):
        provider = "archive_today"
    elif "ghostarchive" in host:
        provider = "ghostarchive"
    elif text:
        provider = host or "manual"
    return ArchiveCandidate(
        provider=provider,
        url=text,
        status=STATUS_SUPPLIED if text else STATUS_NOT_TESTED,
        original_url=original_url,
        saved_at=saved_at,
    )


def build_metro_archive_availability_scan(
    *,
    live_url: str,
    wayback_url: str = "",
    archive_today_url: str = "",
    extra_archive_urls: Sequence[str] = (),
) -> UniversalSourceAvailabilityScan:
    site_key = detect_site_key(live_url)
    capability = SITE_CAPABILITY_MATRIX.get(site_key, GENERIC_NEWS_CAPABILITY)
    archive_urls = tuple(url for url in (wayback_url, archive_today_url, *extra_archive_urls) if str(url or "").strip())
    candidates = tuple(classify_archive_candidate(url, live_url=live_url) for url in archive_urls)
    summary = (
        "R42FX Metro archive/source-adapter availability scan",
        f"Live URL: {live_url}",
        f"Site capability: {capability.site_key}/{capability.adapter_id}",
        f"Article text: {capability.article_text}",
        f"Screenshot: {capability.screenshots}",
        f"Comments: {capability.comments}",
        f"Media route preference: jdownloader_internal_api3128 ({API3128_ROUTE_USED})",
        "Deep Video & Audio route: api3128_jdownloader_primary_for_selected_public_candidates",
        f"Archive candidates: {len(candidates)} supplied",
        "Side effects: no network fetch, no archive submission, no media download, no screenshot, no CAPTCHA/access bypass.",
    )
    return UniversalSourceAvailabilityScan(
        live_url=live_url,
        site_key=site_key,
        capability=capability,
        archive_candidates=candidates,
        side_effects_performed=False,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        summary_lines=summary,
    )


def write_scan_report(scan: UniversalSourceAvailabilityScan, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "r42fx_metro_archive_availability_scan.json"
    md_path = root / "r42fx_metro_archive_availability_scan.md"
    json_path.write_text(json.dumps(scan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# R42FX Metro archive/source-adapter availability scan", ""]
    lines.extend(f"- {line}" for line in scan.summary_lines[1:])
    lines.append("")
    lines.append("## Archive candidates")
    for candidate in scan.archive_candidates:
        saved = f" saved_at={candidate.saved_at}" if candidate.saved_at else ""
        lines.append(f"- {candidate.provider}: {candidate.status}{saved} :: {candidate.url}")
    lines.append("")
    lines.append("## Capability notes")
    lines.extend(f"- {note}" for note in scan.capability.notes)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R42FX Metro archive/source-adapter availability scan")
    parser.add_argument("--live-url", required=True)
    parser.add_argument("--wayback-url", default="")
    parser.add_argument("--archive-today-url", default="")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42fx_metro_archive_scan")
    args = parser.parse_args(argv)
    scan = build_metro_archive_availability_scan(
        live_url=args.live_url,
        wayback_url=args.wayback_url,
        archive_today_url=args.archive_today_url,
    )
    json_path, md_path = write_scan_report(scan, args.output_root)
    for line in scan.summary_lines:
        print(line)
    print(f"JSON: {json_path}")
    print(f"MARKDOWN: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
