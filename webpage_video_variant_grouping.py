from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class VideoVariantGroup:
    """A group of direct media URLs that are likely quality renditions of one clip."""

    representative_id: str
    variant_ids: tuple[str, ...]


_DIMENSION_RE = re.compile(r"(?<!\d)(\d{2,5})x(\d{2,5})(?!\d)", re.IGNORECASE)
_QUALITY_TOKEN_RE = re.compile(
    r"(?i)(?:^|[_\-.])("
    r"\d{3,4}p|sd|hd|fhd|uhd|low|medium|high|mobile|desktop|small|large|"
    r"\d{2,5}x\d{2,5}"
    r")(?:$|[_\-.])"
)


def _resource_id_for_item(item: Any) -> str:
    return str(getattr(item, "resource_id", "") or "")


def _display_name_for_item(item: Any) -> str:
    return " ".join(str(getattr(item, "display_name", "") or getattr(item, "title", "") or "").split()).lower()


def _url_for_item(item: Any, media_url_getter: Callable[[Any], str]) -> str:
    try:
        return str(media_url_getter(item) or "").strip()
    except Exception:
        return ""


def dimensions_from_text(text: str) -> tuple[int, int]:
    match = _DIMENSION_RE.search(str(text or ""))
    if not match:
        return 0, 0
    try:
        return int(match.group(1)), int(match.group(2))
    except Exception:
        return 0, 0


def video_variant_dimensions(item: Any) -> tuple[int, int]:
    """Return dimensions from item metadata, or from URL/display-name tokens."""
    try:
        width = int(getattr(item, "width", 0) or 0)
        height = int(getattr(item, "height", 0) or 0)
    except Exception:
        width, height = 0, 0
    if width > 0 and height > 0:
        return width, height
    media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "")
    width, height = dimensions_from_text(media_url)
    if width > 0 and height > 0:
        return width, height
    return dimensions_from_text(_display_name_for_item(item))


def video_variant_quality_score(item: Any) -> tuple[int, int, int, str]:
    """Sort best-quality variants first without requiring a Content-Length probe."""
    width, height = video_variant_dimensions(item)
    pixels = max(0, width) * max(0, height)
    max_side = max(width, height)
    min_side = min(width, height) if width and height else 0
    media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "")
    return (pixels, max_side, min_side, media_url)


def video_variant_quality_label(item: Any) -> str:
    """Short label for the grouped quality button shown on a video card."""
    width, height = video_variant_dimensions(item)
    ext = str(getattr(item, "extension", "") or Path(urlparse(str(getattr(item, "reference_url", "") or "")).path).suffix or "").lower()
    ext_label = ext.lstrip(".").upper() if ext else "VIDEO"
    if width > 0 and height > 0:
        return f"{width}x{height} {ext_label}"
    return f"quality unknown {ext_label}"


def normalize_video_rendition_content_key(media_url: str, *, title: str = "") -> str:
    """Normalize direct-video URLs so same-content quality renditions group together.

    Example Metro-style names:
    ``1024x576_MP4_7351137571375236737.mp4`` and
    ``480x270_MP4_7351137571375236737.mp4`` normalize to the same content key.
    """
    text = str(media_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    path = unquote(parsed.path or "").lower()
    name = Path(path).name
    if not name:
        return ""
    stem = Path(name).stem
    # Remove leading rendition tokens and common quality labels while preserving
    # the actual asset id/title stem.
    stem = re.sub(r"^(?:\d{2,5}x\d{2,5}|[a-z]{0,3}\d{3,4}p)[_\-.]+", "", stem, flags=re.IGNORECASE)
    stem = _DIMENSION_RE.sub("", stem)
    stem = _QUALITY_TOKEN_RE.sub("_", stem)
    stem = re.sub(r"(?i)(?:^|[_\-.])(?:mp4|webm|m4v|mov)(?:$|[_\-.])", "_", stem)
    stem = re.sub(r"[_\-.]+", "_", stem).strip("_-.")
    if len(stem) < 4:
        return ""
    parent_parts = [
        part
        for part in path.split("/")[:-1]
        if part and not _DIMENSION_RE.fullmatch(part) and not _QUALITY_TOKEN_RE.search(f"_{part}_")
    ]
    parent_key = "/".join(parent_parts[-4:])
    # V78R: do not include the UI/display title in the key for direct media
    # rendition grouping. Static candidates, rendered candidates, and browser
    # network candidates can label the same MP4 asset differently (for example
    # article title vs. "file MP4 from source").  The URL asset stem/path is
    # the stable identity; mixing display title into the key prevented the
    # quality selector from appearing for same-content Metro renditions.
    return f"{host}/{parent_key}/{stem}"


def group_video_rendition_items(
    items: tuple[Any, ...] | list[Any],
    *,
    media_url_getter: Callable[[Any], str],
) -> tuple[tuple[Any, ...], dict[str, tuple[Any, ...]], dict[str, str]]:
    """Collapse same-content direct-video quality variants to one representative.

    Returns:
    - display items with duplicate renditions collapsed
    - representative resource id -> sorted variant tuple
    - variant resource id -> representative resource id
    """
    original_items = tuple(items or ())
    buckets: dict[str, list[Any]] = {}
    key_by_resource_id: dict[str, str] = {}
    ordered_keys: list[str] = []
    for item in original_items:
        resource_id = _resource_id_for_item(item)
        media_url = _url_for_item(item, media_url_getter)
        key = normalize_video_rendition_content_key(media_url, title=_display_name_for_item(item))
        if not resource_id or not key:
            continue
        if key not in buckets:
            buckets[key] = []
            ordered_keys.append(key)
        buckets[key].append(item)
        key_by_resource_id[resource_id] = key

    grouped_keys = {key for key, values in buckets.items() if len(values) > 1}
    groups_by_rep_id: dict[str, tuple[Any, ...]] = {}
    rep_id_by_variant_id: dict[str, str] = {}
    display: list[Any] = []
    emitted_group_keys: set[str] = set()

    for item in original_items:
        resource_id = _resource_id_for_item(item)
        key = key_by_resource_id.get(resource_id, "")
        if not key or key not in grouped_keys:
            display.append(item)
            continue
        if key in emitted_group_keys:
            continue
        emitted_group_keys.add(key)
        variants = tuple(sorted(buckets[key], key=video_variant_quality_score, reverse=True))
        representative = variants[0]
        rep_id = _resource_id_for_item(representative)
        if not rep_id:
            display.append(item)
            continue
        groups_by_rep_id[rep_id] = variants
        for variant in variants:
            variant_id = _resource_id_for_item(variant)
            if variant_id:
                rep_id_by_variant_id[variant_id] = rep_id
        display.append(representative)

    return tuple(display), groups_by_rep_id, rep_id_by_variant_id


__all__ = [
    "VideoVariantGroup",
    "dimensions_from_text",
    "group_video_rendition_items",
    "normalize_video_rendition_content_key",
    "video_variant_dimensions",
    "video_variant_quality_label",
    "video_variant_quality_score",
]
