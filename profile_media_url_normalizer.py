"""Deterministic URL normalisation for Profile/Media link source objects.

This module is intentionally stdlib-only and offline. It parses URL wrappers
and common social/video URL shapes, but it never fetches the URL.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlparse, urlunparse


_REDIRECT_PARAMS = (
    "url",
    "u",
    "q",
    "target",
    "redirect",
    "redirect_url",
    "amp;url",
    "destination",
    "to",
    "r",
)

_COMMON_SECOND_LEVEL_TLDS = {
    "ac.uk",
    "co.uk",
    "gov.uk",
    "ltd.uk",
    "me.uk",
    "net.uk",
    "nhs.uk",
    "org.uk",
    "plc.uk",
    "sch.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "com.tr",
    "co.za",
    "com.sg",
    "com.my",
}

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "yclid",
    "msclkid",
    "vero_id",
    "spm",
}
_TRACKING_PREFIXES = ("utm_",)
_DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".rtf", ".txt", ".csv", ".xls", ".xlsx")


def _clean_url(url: object) -> str:
    text = str(url or "").strip()
    text = text.strip("<>\"'")
    text = re.sub(r"[\s\r\n]+$", "", text)
    return text.rstrip(".,;:)]}")


def _normalise_netloc(hostname: str, netloc: str) -> str:
    if not hostname:
        return netloc.lower()
    lower_host = hostname.lower()
    if "@" in netloc:
        return lower_host
    return lower_host


def _idna_host(hostname: str) -> str:
    try:
        return hostname.encode("idna").decode("ascii")
    except Exception:
        return hostname


def _registered_domain(hostname: str) -> str:
    host = _idna_host((hostname or "").strip(".").lower())
    if not host:
        return ""
    parts = [part for part in host.split(".") if part]
    if len(parts) <= 2:
        return host
    last_two = ".".join(parts[-2:])
    if last_two in _COMMON_SECOND_LEVEL_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last_two


def _domain_parts(hostname: str) -> tuple[str, str, str]:
    host = _idna_host((hostname or "").strip(".").lower())
    registered = _registered_domain(host)
    if not registered:
        return "", "", ""
    suffix = registered.split(".", 1)[1] if "." in registered else ""
    subdomain = host[: -(len(registered) + 1)] if host.endswith("." + registered) else ""
    return registered, suffix, subdomain


def _ensure_parseable(url: str) -> str:
    if re.match(r"^[a-z][a-z0-9+.-]*://", url, flags=re.IGNORECASE):
        return url
    if url.startswith("//"):
        return "https:" + url
    return "https://" + url


def _query_without_tracking(query: str) -> tuple[str, list[str]]:
    kept: list[tuple[str, str]] = []
    removed: list[str] = []
    for key, value in parse_qsl(query or "", keep_blank_values=True):
        lower = key.lower()
        if lower in _TRACKING_PARAMS or any(lower.startswith(prefix) for prefix in _TRACKING_PREFIXES):
            removed.append(key)
            continue
        kept.append((key, value))
    return urlencode(kept, doseq=True), removed


def _normalised_url(url: str) -> str:
    parsed = urlparse(_ensure_parseable(url))
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower()
    netloc = _normalise_netloc(hostname, parsed.netloc)
    path = parsed.path or ""
    query, _removed = _query_without_tracking(parsed.query)
    return urlunparse((scheme, netloc, path, "", query, parsed.fragment))


def _extract_wayback_target(parsed) -> tuple[str, str, str]:
    if parsed.hostname not in {"web.archive.org", "wayback.archive.org"}:
        return "none", "", ""
    path = parsed.path or ""
    match = re.match(r"^/web/(\*|\d{6,14}[a-z_,-]*)/(https?://.+)$", path, flags=re.IGNORECASE)
    if not match:
        return "none", "", ""
    stamp, target = match.groups()
    kind = "archive_index" if stamp == "*" else "archived_copy"
    timestamp_match = re.match(r"(\d{6,14})", stamp)
    return kind, unquote(target), timestamp_match.group(1) if timestamp_match else ""


def _archive_kind_and_target(parsed) -> tuple[str, str, str]:
    host = (parsed.hostname or "").lower()
    if host in {"web.archive.org", "wayback.archive.org"}:
        return _extract_wayback_target(parsed)
    if host.startswith("webcache.") or host in {"webcache.googleusercontent.com"}:
        query = parse_qs(parsed.query or "")
        for key in ("q", "url"):
            for value in query.get(key, ()):
                if value.startswith(("http://", "https://")):
                    return "archived_copy", value, ""
        return "archived_copy", "", ""
    if host in {"archive.today", "archive.ph", "archive.is", "ghostarchive.org"}:
        query = parse_qs(parsed.query or "")
        for values in query.values():
            for value in values:
                if value.startswith(("http://", "https://")):
                    return "archived_copy", value, ""
        return "archived_copy", "", ""
    return "none", "", ""


def _redirect_target(parsed) -> str:
    query = parse_qs(parsed.query or "", keep_blank_values=False)
    for key in _REDIRECT_PARAMS:
        for value in query.get(key, ()):
            decoded = unquote(value)
            if decoded.startswith(("http://", "https://")):
                return decoded
    for values in query.values():
        for value in values:
            decoded = unquote(value)
            if decoded.startswith(("http://", "https://")):
                return decoded
    decoded_path = unquote((parsed.path or "") + ("?" + (parsed.query or "") if parsed.query else ""))
    match = re.search(r"https?://[^\s&]+", decoded_path, flags=re.IGNORECASE)
    if match:
        return match.group(0).rstrip(".,;:)]}")
    match = re.search(r"\bwww\.[^\s&]+", decoded_path, flags=re.IGNORECASE)
    if match:
        return "https://" + match.group(0).rstrip(".,;:)]}")
    return ""


def _document_fields(parsed) -> dict[str, object]:
    path = (parsed.path or "").lower()
    extension = ""
    match = re.search(r"\.([a-z0-9]{1,8})$", path)
    if match:
        extension = "." + match.group(1)
    return {
        "is_document_url": extension in _DOCUMENT_EXTENSIONS,
        "document_extension": extension if extension in _DOCUMENT_EXTENSIONS else "",
        "is_pdf_url": extension == ".pdf",
    }


def _social_video_fields(parsed) -> dict[str, object]:
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path or ""
    query = parse_qs(parsed.query or "")
    output = {
        "is_social_url": False,
        "social_platform": "",
        "social_object_type": "",
        "social_object_id": "",
        "is_video_url": False,
        "video_platform": "",
        "video_id": "",
    }
    if host in {"x.com", "twitter.com", "mobile.twitter.com", "mobile.x.com"}:
        match = re.search(r"/(?:i/web/)?status(?:es)?/([0-9]+)", path, flags=re.IGNORECASE)
        handle_match = re.match(r"/([^/?#]+)/?", path)
        output.update(
            {
                "is_social_url": True,
                "social_platform": "x_twitter",
                "social_object_type": "status" if match else "profile_or_timeline",
                "social_object_id": match.group(1) if match else "",
                "social_profile_handle": handle_match.group(1) if handle_match and handle_match.group(1) not in {"i", "intent", "share"} else "",
            }
        )
    elif host == "facebook.com" or host.endswith(".facebook.com"):
        match = re.search(r"/(?:posts|permalink\.php|story\.php)/?([^/?#]+)?", path, flags=re.IGNORECASE)
        profile_match = re.match(r"/([^/?#]+)/?", path)
        output.update(
            {
                "is_social_url": True,
                "social_platform": "facebook",
                "social_object_type": "post" if match else "page_or_profile",
                "social_object_id": (match.group(1) or "") if match else "",
                "social_profile_handle": profile_match.group(1) if profile_match else "",
            }
        )
    elif host in {"youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}:
        video_id = ""
        channel_id = ""
        channel_handle = ""
        if host == "youtu.be":
            video_id = path.strip("/").split("/")[0]
        else:
            shorts_match = re.search(r"/(?:shorts|embed|live)/([^/?#]+)", path, flags=re.IGNORECASE)
            if shorts_match:
                video_id = shorts_match.group(1)
            video_id = video_id or (query.get("v") or [""])[0]
            channel_match = re.search(r"/channel/([^/?#]+)", path, flags=re.IGNORECASE)
            handle_match = re.search(r"/@([^/?#]+)", path, flags=re.IGNORECASE)
            user_match = re.search(r"/user/([^/?#]+)", path, flags=re.IGNORECASE)
            channel_id = channel_match.group(1) if channel_match else ""
            channel_handle = (handle_match.group(1) if handle_match else "") or (user_match.group(1) if user_match else "")
        output.update(
            {
                "is_social_url": True,
                "social_platform": "youtube",
                "social_object_type": "video" if video_id else "channel" if channel_id or channel_handle else "page",
                "social_object_id": video_id or channel_id or channel_handle,
                "social_profile_handle": channel_handle,
                "youtube_channel_id": channel_id,
                "is_video_url": bool(video_id),
                "video_platform": "youtube",
                "video_id": video_id,
            }
        )
    elif host == "vimeo.com" or host.endswith(".vimeo.com"):
        match = re.search(r"/(\d+)", path)
        output.update(
            {
                "is_social_url": True,
                "social_platform": "vimeo",
                "social_object_type": "video" if match else "page",
                "social_object_id": match.group(1) if match else "",
                "is_video_url": bool(match),
                "video_platform": "vimeo",
                "video_id": match.group(1) if match else "",
            }
        )
    elif host == "tiktok.com" or host.endswith(".tiktok.com"):
        match = re.search(r"/video/([0-9]+)", path)
        handle_match = re.search(r"/@([^/?#]+)", path)
        output.update(
            {
                "is_social_url": True,
                "social_platform": "tiktok",
                "social_object_type": "video" if match else "profile_or_page",
                "social_object_id": match.group(1) if match else "",
                "social_profile_handle": handle_match.group(1) if handle_match else "",
                "is_video_url": bool(match),
                "video_platform": "tiktok",
                "video_id": match.group(1) if match else "",
            }
        )
    elif host == "instagram.com" or host.endswith(".instagram.com"):
        match = re.search(r"/(p|reel|tv)/([^/?#]+)", path)
        profile_match = re.match(r"/([^/?#]+)/?", path)
        output.update(
            {
                "is_social_url": True,
                "social_platform": "instagram",
                "social_object_type": match.group(1) if match else "profile_or_page",
                "social_object_id": match.group(2) if match else "",
                "social_profile_handle": profile_match.group(1) if profile_match and not match else "",
                "is_video_url": bool(match and match.group(1) in {"reel", "tv"}),
                "video_platform": "instagram" if match and match.group(1) in {"reel", "tv"} else "",
                "video_id": match.group(2) if match and match.group(1) in {"reel", "tv"} else "",
            }
        )
    return output


def normalise_url_record(url: str) -> dict[str, object]:
    """Return parsed URL metadata without network access."""

    raw_url = _clean_url(url)
    original_parsed = urlparse(_ensure_parseable(raw_url)) if raw_url else urlparse("")
    _clean_query, removed_tracking = _query_without_tracking(original_parsed.query)
    normalised = _normalised_url(raw_url) if raw_url else ""
    parsed = urlparse(normalised)
    hostname = (parsed.hostname or "").lower()
    registered_domain, domain_suffix, subdomain = _domain_parts(hostname)
    archive_kind, archive_target_url, archive_capture_timestamp = _archive_kind_and_target(parsed)
    redirect_target_url = _redirect_target(original_parsed) or _redirect_target(parsed)
    output: dict[str, object] = {
        "url": raw_url,
        "normalised_url": normalised,
        "display_url": normalised,
        "scheme": parsed.scheme,
        "hostname": hostname,
        "hostname_idna": _idna_host(hostname),
        "registered_domain": registered_domain,
        "domain_suffix": domain_suffix,
        "subdomain": subdomain,
        "path": parsed.path or "",
        "query": parsed.query or "",
        "fragment": parsed.fragment or "",
        "is_archive_url": archive_kind != "none",
        "archive_kind": archive_kind,
        "archive_target_url": archive_target_url,
        "archive_capture_timestamp": archive_capture_timestamp,
        "archive_capture_url": normalised if archive_kind == "archived_copy" else "",
        "archive_index_url": normalised if archive_kind == "archive_index" else "",
        "is_redirect_wrapper": bool(redirect_target_url),
        "redirect_target_url": redirect_target_url,
        "tracking_params_removed": removed_tracking,
    }
    output.update(_social_video_fields(parsed))
    output.update(_document_fields(parsed))
    return output
