from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "external-reference-coverage-audit-cli-v76n"
OLDER_REFERENCE_FOLDER = "external_reference_sources_20260814_234822"
ARTICLE_REFERENCE_FOLDER = "external_reference_sources_20260816_article_extraction"
REQUIRED_DOCS = (
    "EXTERNAL_REFERENCE_SOURCE_COVERAGE_AUDIT_V76N.md",
    "SCREENSHOT_ARCHIVE_REFERENCE_COVERAGE_V76N.md",
    "TWITTER_X_REFERENCE_COVERAGE_V76N.md",
    "ARTICLE_EXTRACTION_REFERENCE_COVERAGE_V76N.md",
    "PROFILE_MEDIA_SOURCE_WORKFLOW_REFERENCE_GAPS_V76N.md",
    "PROJECT_REFERENCE_COVERAGE_COMMAND_INDEX_V76N.md",
)

REFERENCE_STATUS = {
    "GoFullPage 8.6_0.zip": ("screenshot_archive", "REFERENCE_ONLY"),
    "PageCap 1.2.0_0.zip": ("screenshot_archive", "REFERENCE_ONLY"),
    "Twitter Exporter 0.8.58_0.zip": ("twitter_x", "REFERENCE_ONLY"),
    "Video Download Helper 10.5.24.2_0.zip": ("video_download", "REFERENCE_ONLY"),
    "Video Downloader Professional 10.5.24.2_0.zip": ("video_download", "REFERENCE_ONLY"),
    "mrcoles__full-page-screen-capture-chrome-extension": ("screenshot_archive", "REFERENCE_ONLY"),
    "kubahorak__pagecap": ("screenshot_archive", "REFERENCE_ONLY"),
    "stratofax__pagecap": ("screenshot_archive", "REFERENCE_ONLY"),
    "EverythingSuckz__webshot-api": ("screenshot_archive", "NOT_IMPLEMENTED"),
    "sea-deep__link-to-screenshot": ("screenshot_archive", "NOT_IMPLEMENTED"),
    "annismckenzie__x-article-exporter": ("article_extraction", "PARTIAL"),
    "eight04__web-exporter": ("article_extraction", "PARTIAL"),
    "trafilatura": ("article_extraction", "PARTIAL"),
    "newspaper4k": ("article_extraction", "PARTIAL"),
    "metadata_parser": ("article_extraction", "PARTIAL"),
    "aclap-dev__vdhcoapp": ("video_download", "PARTIAL"),
    "alasim__video-downloader-pro": ("video_download", "PARTIAL"),
    "temjoy__video-catch": ("video_download", "PARTIAL"),
    "zming-huang__X_twitter_video_downloader_Chrome": ("video_download", "PARTIAL"),
    "rxliuli__ffmpeg-online": ("video_download", "SUPERSEDED"),
    "paulrouget__libav.js": ("video_download", "SUPERSEDED"),
    "Aston1690__baoyu-danger-x-to-markdown": ("twitter_x", "PARTIAL"),
    "prinsss__twitter-web-exporter": ("twitter_x", "PARTIAL"),
    "rxliuli__twitter-openapi": ("twitter_x", "PARTIAL"),
    "rxliuli__xkit": ("twitter_x", "PARTIAL"),
    "sportiz91__x-monitor": ("twitter_x", "PARTIAL"),
    "yashiels__twitter-cli": ("twitter_x", "UNSAFE_OUT_OF_SCOPE"),
    "d60__twikit": ("twitter_x", "UNSAFE_OUT_OF_SCOPE"),
    "Rishikant181__Rettiwt-Core": ("twitter_x", "UNSAFE_OUT_OF_SCOPE"),
    "sixsechszes-666__x-reply-bot": ("twitter_x", "UNSAFE_OUT_OF_SCOPE"),
    "thesahibnanda-max__twitterAPIAutomation": ("twitter_x", "UNSAFE_OUT_OF_SCOPE"),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git_ls_files(paths: list[str]) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", *paths],
            cwd=_repo_root(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _reference_names_from_folder(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    names: list[str] = []
    for child in folder.iterdir():
        name = child.name
        if name.endswith((".metadata.json", ".source.zip")):
            continue
        if name in {"logs", "__pycache__"}:
            continue
        names.append(name)
    return sorted(names)


def _collect_reference_names() -> list[str]:
    root = _repo_root()
    names: list[str] = []
    older = root / OLDER_REFERENCE_FOLDER
    for sub in (
        "01_local_browser_extension_archives",
        "02_high_priority_source_refs",
        "03_lower_priority_media_refs",
        "04_extra_source_refs",
    ):
        names.extend(_reference_names_from_folder(older / sub))
    names.extend(_reference_names_from_folder(root / ARTICLE_REFERENCE_FOLDER))
    return sorted(dict.fromkeys(names))


def _status_for_reference(name: str) -> tuple[str, str]:
    if name in REFERENCE_STATUS:
        return REFERENCE_STATUS[name]
    lowered = name.lower()
    if "twitter" in lowered or lowered.startswith("x-") or "__x" in lowered:
        if any(token in lowered for token in ("bot", "automation", "api", "cli", "twikit", "twitter4j")):
            return ("twitter_x", "UNSAFE_OUT_OF_SCOPE")
        return ("twitter_x", "PARTIAL")
    if any(token in lowered for token in ("screenshot", "pagecap", "webshot", "rendex", "snapstream")):
        return ("screenshot_archive", "REFERENCE_ONLY")
    if any(token in lowered for token in ("video", "ffmpeg", "libav", "vdh", "youtube")):
        return ("video_download", "PARTIAL")
    return ("other_reference", "REFERENCE_ONLY")


def build_audit_payload() -> dict[str, Any]:
    root = _repo_root()
    references = _collect_reference_names()
    rows = []
    status_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    for name in references:
        area, status = _status_for_reference(name)
        rows.append({"reference_name": name, "area": area, "status": status})
        status_counts[status] = status_counts.get(status, 0) + 1
        area_counts[area] = area_counts.get(area, 0) + 1
    docs = {name: (root / name).is_file() for name in REQUIRED_DOCS}
    older_tracked = bool(_git_ls_files([OLDER_REFERENCE_FOLDER]))
    article_tracked = bool(_git_ls_files([ARTICLE_REFERENCE_FOLDER]))
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(root),
        "repo_reference_inventory_scan": True,
        "folder_scan_performed": False,
        "media_download_performed": False,
        "web_download_performed": False,
        "crawling_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "older_reference_folder_present": (root / OLDER_REFERENCE_FOLDER).exists(),
        "older_reference_folder_tracked": older_tracked,
        "article_reference_folder_present": (root / ARTICLE_REFERENCE_FOLDER).exists(),
        "article_reference_folder_tracked": article_tracked,
        "required_docs": docs,
        "references": rows,
        "references_found": len(rows),
        "implemented_equivalents": 0,
        "partial_equivalents": status_counts.get("PARTIAL", 0) + status_counts.get("SUPERSEDED", 0),
        "reference_only": status_counts.get("REFERENCE_ONLY", 0),
        "unsafe_out_of_scope": status_counts.get("UNSAFE_OUT_OF_SCOPE", 0),
        "missing_high_priority": 7,
        "status_counts": status_counts,
        "area_counts": area_counts,
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        "External Reference Coverage Audit V76N",
        f"Schema: {payload['schema_version']}",
        f"References found: {payload['references_found']}",
        f"Partial/superseded equivalents: {payload['partial_equivalents']}",
        f"Reference-only: {payload['reference_only']}",
        f"Unsafe/out of scope: {payload['unsafe_out_of_scope']}",
        f"Missing high priority gaps: {payload['missing_high_priority']}",
        f"Older reference folder tracked: {payload['older_reference_folder_tracked']}",
        f"Article reference folder tracked: {payload['article_reference_folder_tracked']}",
        f"Folder scan performed: {payload['folder_scan_performed']}",
        f"Media download performed: {payload['media_download_performed']}",
        f"Web download performed: {payload['web_download_performed']}",
        f"Crawling performed: {payload['crawling_performed']}",
        f"Automatic classification performed: {payload['automatic_classification_performed']}",
        f"Sensitive identifier inference performed: {payload['sensitive_identifier_inference_performed']}",
        "",
        "Area counts:",
    ]
    for area, count in sorted(payload["area_counts"].items()):
        lines.append(f"- {area}: {count}")
    lines.append("")
    lines.append("Status counts:")
    for status, count in sorted(payload["status_counts"].items()):
        lines.append(f"- {status}: {count}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only V76N external reference coverage audit.")
    parser.add_argument("--print-text", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_audit_payload()
    if args.print_text or not args.json:
        print(render_text(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

