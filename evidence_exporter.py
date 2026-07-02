from __future__ import annotations

import csv
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _safe_filename(value: str, fallback: str = "youtube_export") -> str:
    value = (value or "").strip()
    if not value:
        value = fallback

    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        value = value.replace(ch, "_")

    value = " ".join(value.split())
    return value[:120] or fallback


def _get_first_video_title(metadata: List[Dict[str, Any]]) -> str:
    if not metadata:
        return "youtube_export"

    first = metadata[0]
    for key in ("title", "video_title", "name"):
        if first.get(key):
            return str(first[key])

    return "youtube_export"


def _write_source_info(
    path: Path,
    metadata: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
    spam: List[Dict[str, Any]],
    source_urls: List[str],
    app_version: str,
    settings: Dict[str, Any],
    screenshots: List[str],
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with path.open("w", encoding="utf-8") as f:
        f.write("YouTube Comment Extractor - Evidence Package\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Created: {now}\n")
        f.write(f"App version: {app_version}\n\n")

        f.write("Source URLs:\n")
        if source_urls:
            for url in source_urls:
                f.write(f"- {url}\n")
        else:
            f.write("- Not recorded\n")

        f.write("\nExtraction Summary:\n")
        f.write(f"- Videos: {len(metadata)}\n")
        f.write(f"- Comments/replies: {len(comments)}\n")
        f.write(f"- Spam/filtered comments: {len(spam)}\n")
        f.write(f"- Screenshots attached: {len(screenshots)}\n\n")

        f.write("Settings:\n")
        for key, value in settings.items():
            f.write(f"- {key}: {value}\n")

        f.write("\nVideo Metadata:\n")
        if not metadata:
            f.write("- No metadata available\n")
        else:
            for i, item in enumerate(metadata, start=1):
                f.write(f"\nVideo {i}\n")
                for key, value in item.items():
                    f.write(f"- {key}: {value}\n")

        f.write("\nNotes:\n")
        f.write(
            "Screenshots are user-attached evidence files. "
            "They may reflect a manually prepared browser state, such as an expanded "
            "description, newest-first sorting, or a page scrolled to load more comments.\n"
        )


def _write_readable_txt(path: Path, comments: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("YouTube Comments - Readable Evidence Export\n")
        f.write("=" * 80 + "\n\n")

        if not comments:
            f.write("No comments found.\n")
            return

        for i, c in enumerate(comments, start=1):
            comment_type = c.get("type") or c.get("comment_type") or "Comment"
            author = c.get("author") or c.get("authorDisplayName") or "Unknown"
            date = c.get("published_at") or c.get("publishedAt") or ""
            likes = c.get("likes") or c.get("likeCount") or 0
            text = c.get("text") or c.get("textDisplay") or ""
            parent_id = c.get("parent_id") or c.get("parentId") or ""

            prefix = "↳ Reply" if str(comment_type).lower() == "reply" else f"[{i}] Parent Comment"

            f.write(f"{prefix}\n")
            f.write(f"Author: {author}\n")
            f.write(f"Date: {date}\n")
            f.write(f"Likes: {likes}\n")
            if parent_id:
                f.write(f"Parent ID: {parent_id}\n")
            f.write("\nText:\n")
            f.write(f"  {text}\n")
            f.write("\n" + "-" * 80 + "\n\n")


def _write_comments_csv(path: Path, comments: List[Dict[str, Any]]) -> None:
    if not comments:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return

    fieldnames = sorted({key for row in comments for key in row.keys()})

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comments)


def create_evidence_package(
    output_parent: str,
    metadata: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
    spam: List[Dict[str, Any]],
    screenshots: List[str],
    source_urls: List[str],
    app_version: str,
    settings: Dict[str, Any],
) -> str:
    """
    Creates a folder containing readable comments, CSV, source_info, and screenshots.
    Returns the created folder path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = _safe_filename(_get_first_video_title(metadata))
    package_dir = Path(output_parent) / f"{title}_evidence_{timestamp}"
    package_dir.mkdir(parents=True, exist_ok=True)

    screenshot_dir = package_dir / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    copied_screenshots = []

    for index, screenshot in enumerate(screenshots, start=1):
        src = Path(screenshot)
        if not src.exists():
            continue

        suffix = src.suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            continue

        dst = screenshot_dir / f"page_screenshot_{index:03d}{suffix}"
        shutil.copy2(src, dst)
        copied_screenshots.append(str(dst))

    _write_source_info(
        package_dir / "source_info.txt",
        metadata=metadata,
        comments=comments,
        spam=spam,
        source_urls=source_urls,
        app_version=app_version,
        settings=settings,
        screenshots=copied_screenshots,
    )

    _write_readable_txt(package_dir / "comments_readable.txt", comments)
    _write_comments_csv(package_dir / "comments.csv", comments)

    if spam:
        _write_comments_csv(package_dir / "spam_comments.csv", spam)

    return str(package_dir)