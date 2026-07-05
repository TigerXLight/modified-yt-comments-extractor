from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "YTCE_ASR_TopicResolver"
CACHE_FILE = CACHE_DIR / "topic_glossary_cache.json"

CACHE_TTL_SECONDS = int(os.environ.get("ASR_TOPIC_RESOLVER_CACHE_SECONDS", str(7 * 24 * 60 * 60)))
REMOTE_TIMEOUT_SECONDS = float(os.environ.get("ASR_TOPIC_RESOLVER_TIMEOUT", "8"))

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "he", "i", "in", "is", "it", "its", "of", "on", "or", "she", "that",
    "the", "their", "this", "to", "was", "were", "with", "you", "your",
    "watch", "shorts", "youtube", "youtu", "http", "https", "www", "com",
    "social", "media", "community", "discord", "twitter", "twitch",
    "instagram", "spotify", "listen", "music", "official", "video",
    "started", "streaming", "details", "games", "wiki", "fandom", "page",
    "edit", "source", "category", "navigation",
}


def _read_cache() -> Dict[str, Any]:
    try:
        if not CACHE_FILE.exists():
            return {}

        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def _write_cache(cache: Dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _cache_key(context: Dict[str, Any], resolver_url: str) -> str:
    payload = {
        "resolver_url": resolver_url or "",
        "urls": context.get("urls") or [],
        "url_text": context.get("url_text") or "",
        "language": context.get("language") or "",
        "video_info": context.get("video_info") or {},
        "transcript_source": context.get("transcript_source") or "",
    }

    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe_terms(terms: List[str], max_terms: int = 80) -> List[str]:
    clean: List[str] = []
    seen = set()

    for term in terms:
        term = html.unescape(str(term or "")).strip()
        term = re.sub(r"\s+", " ", term)
        term = term.strip(" \t\r\n.,:;!?()[]{}<>\"'“”‘’")

        if len(term) < 3 or len(term) > 80:
            continue

        lowered = term.lower()

        if lowered in STOPWORDS:
            continue

        if term.isdigit():
            continue

        if lowered in seen:
            continue

        seen.add(lowered)
        clean.append(term)

        if len(clean) >= max_terms:
            break

    return clean


def _extract_urls(text: str) -> List[str]:
    urls: List[str] = []
    seen = set()

    for match in re.finditer(r"https?://[^\s<>\"]+", text or "", re.IGNORECASE):
        url = match.group(0).rstrip(").,;]")
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def _url_path_terms(url: str) -> List[str]:
    terms: List[str] = []

    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc or ""
        path = urllib.parse.unquote(parsed.path or "")
        query = urllib.parse.parse_qs(parsed.query or "")

        for piece in re.split(r"[./_\-#?=&+]+", host + " " + path):
            piece = piece.strip()

            if not piece:
                continue

            if piece.lower() in STOPWORDS:
                continue

            if len(piece) >= 3:
                terms.append(piece)

        # Preserve YouTube video IDs as context but keep them low value.
        for value in query.get("v", []):
            if value and len(value) >= 6:
                terms.append(value)

    except Exception:
        pass

    return terms


def _context_to_text(context: Dict[str, Any]) -> str:
    parts: List[str] = []

    for key in ("url_text", "transcript_source", "language"):
        value = context.get(key)

        if value:
            parts.append(str(value))

    urls = context.get("urls") or []

    if urls:
        parts.append("\n".join(str(url) for url in urls))

    video_info = context.get("video_info") or {}

    if isinstance(video_info, dict):
        for key in (
            "title",
            "video_title",
            "description",
            "channel_title",
            "channel",
            "author",
            "tags",
            "keywords",
            "category",
        ):
            value = video_info.get(key)

            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)

            if value:
                parts.append(f"{key}: {value}")

    for item in context.get("oembed") or []:
        if isinstance(item, dict):
            for key in ("title", "author_name", "provider_name"):
                value = item.get(key)
                if value:
                    parts.append(str(value))

    return "\n\n".join(parts)


def _extract_terms_from_text(text: str, urls: Optional[List[str]] = None, max_terms: int = 80) -> List[str]:
    terms: List[str] = []

    urls = urls or []

    for url in urls:
        terms.extend(_url_path_terms(url))

    value = text or ""

    # Hashtags: #codzombies, #bo7, #bo7zombies.
    for match in re.findall(r"#([\w][\w\-]{2,50})", value, flags=re.UNICODE):
        terms.append(match)

    # Quoted topic/title terms: The 'Kowakujō' Situation.
    for match in re.findall(r"[\"'“‘]([^\"'”’]{3,80})[\"'”’]", value, flags=re.UNICODE):
        terms.append(match)

    # Multi-word title-case phrases.
    phrase_re = re.compile(
        r"\b(?:[A-Z][A-Za-z0-9'’\-]{2,}\s+){1,4}[A-Z][A-Za-z0-9'’\-]{2,}\b"
    )

    terms.extend(phrase_re.findall(value))

    # Rare/proper/mixed tokens, including Unicode terms.
    token_re = re.compile(r"\b[^\W\d_][\w'’\-]{2,50}\b", flags=re.UNICODE)

    for token in token_re.findall(value):
        ascii_has_signal = (
            any(char.isupper() for char in token[1:])
            or token[:1].isupper()
            or any(char.isdigit() for char in token)
        )
        unicode_has_signal = any(ord(char) > 127 for char in token)

        if ascii_has_signal or unicode_has_signal:
            terms.append(token)

    return _dedupe_terms(terms, max_terms=max_terms)


def _fetch_json(url: str, timeout: float = REMOTE_TIMEOUT_SECONDS) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YTCE-ASR-TopicResolver/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(300000)

    data = json.loads(raw.decode("utf-8", errors="replace"))

    if isinstance(data, dict):
        return data

    return {}


def _youtube_oembed(url: str) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(url)

    if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
        return {}

    endpoint = (
        "https://www.youtube.com/oembed?format=json&url="
        + urllib.parse.quote(url, safe="")
    )

    return _fetch_json(endpoint, timeout=min(REMOTE_TIMEOUT_SECONDS, 5.0))


def _remote_resolver_request(
    resolver_url: str,
    resolver_key: str,
    context: Dict[str, Any],
    local_terms: List[str],
    max_terms: int,
) -> Dict[str, Any]:
    payload = {
        "context": context,
        "local_terms": local_terms,
        "max_terms": max_terms,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "YTCE-ASR-TopicResolver/1.0",
    }

    if resolver_key:
        headers["Authorization"] = f"Bearer {resolver_key}"
        headers["X-ASR-Resolver-Key"] = resolver_key

    request = urllib.request.Request(
        resolver_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=REMOTE_TIMEOUT_SECONDS) as response:
        raw = response.read(500000)

    data = json.loads(raw.decode("utf-8", errors="replace"))

    if isinstance(data, list):
        return {"terms": data}

    if isinstance(data, dict):
        return data

    return {}


def _terms_from_remote_result(result: Dict[str, Any], max_terms: int) -> List[str]:
    terms_raw = result.get("terms") or result.get("glossary") or result.get("keywords") or []
    terms: List[str] = []

    if isinstance(terms_raw, str):
        terms_raw = re.split(r"[,;\n]+", terms_raw)

    if isinstance(terms_raw, list):
        for item in terms_raw:
            if isinstance(item, dict):
                value = item.get("term") or item.get("text") or item.get("name")
            else:
                value = item

            if value:
                terms.append(str(value))

    return _dedupe_terms(terms, max_terms=max_terms)


def build_topic_prompt(terms: List[str], base_prompt: Optional[str] = None, max_terms: int = 80) -> Optional[str]:
    clean_terms = _dedupe_terms(terms, max_terms=max_terms)
    parts: List[str] = []

    if base_prompt:
        parts.append(str(base_prompt).strip())

    if clean_terms:
        # Whisper prompts behave more like prior transcript/context than
        # instructions. Keep this as compact glossary context.
        parts.append(", ".join(clean_terms))

    prompt = "\n\n".join(part for part in parts if part)

    return prompt or None


def resolve_asr_topic_glossary(
    context: Dict[str, Any],
    base_prompt: Optional[str] = None,
    max_terms: int = 80,
) -> Dict[str, Any]:
    """Resolve background topic terms for ASR.

    Optional environment variables:
    - ASR_TOPIC_RESOLVER_URL: remote resolver endpoint.
    - ASR_TOPIC_RESOLVER_KEY: optional bearer/shared key.
    - ASR_TOPIC_RESOLVER_DISABLE=1: disables remote lookup.
    """
    context = dict(context or {})
    urls = list(context.get("urls") or [])

    extra_urls = _extract_urls(context.get("url_text") or "")
    for url in extra_urls:
        if url not in urls:
            urls.append(url)

    context["urls"] = urls

    errors: List[str] = []
    oembed_items: List[Dict[str, Any]] = []

    for url in urls[:3]:
        try:
            item = _youtube_oembed(url)
            if item:
                oembed_items.append(item)
        except Exception as error:
            errors.append(f"YouTube oEmbed failed for {url}: {error}")

    if oembed_items:
        context["oembed"] = oembed_items

    local_text = _context_to_text(context)
    local_terms = _extract_terms_from_text(local_text, urls=urls, max_terms=max_terms)

    resolver_url = os.environ.get("ASR_TOPIC_RESOLVER_URL", "").strip()
    resolver_key = os.environ.get("ASR_TOPIC_RESOLVER_KEY", "").strip()
    remote_disabled = os.environ.get("ASR_TOPIC_RESOLVER_DISABLE", "").strip().lower() in {"1", "true", "yes", "on"}

    cache_key = _cache_key(context, resolver_url)
    cache = _read_cache()
    cached = cache.get(cache_key)

    remote_terms: List[str] = []
    remote_sources: List[Dict[str, Any]] = []
    remote_used = False
    cache_hit = False

    if isinstance(cached, dict):
        cached_at = float(cached.get("cached_at") or 0)
        if time.time() - cached_at <= CACHE_TTL_SECONDS:
            remote_terms = list(cached.get("remote_terms") or [])
            remote_sources = list(cached.get("sources") or [])
            cache_hit = True

    if resolver_url and not remote_disabled and not cache_hit:
        try:
            remote_result = _remote_resolver_request(
                resolver_url=resolver_url,
                resolver_key=resolver_key,
                context=context,
                local_terms=local_terms,
                max_terms=max_terms,
            )

            remote_terms = _terms_from_remote_result(remote_result, max_terms=max_terms)
            remote_sources = list(remote_result.get("sources") or [])
            remote_used = True

            cache[cache_key] = {
                "cached_at": time.time(),
                "remote_terms": remote_terms,
                "sources": remote_sources,
            }
            _write_cache(cache)

        except Exception as error:
            errors.append(f"Remote topic resolver failed: {error}")

    combined_terms = _dedupe_terms(list(remote_terms) + list(local_terms), max_terms=max_terms)
    prompt = build_topic_prompt(combined_terms, base_prompt=base_prompt, max_terms=max_terms)

    return {
        "terms": combined_terms,
        "local_terms": local_terms,
        "remote_terms": remote_terms,
        "sources": remote_sources,
        "errors": errors,
        "prompt": prompt,
        "resolver_url_configured": bool(resolver_url),
        "remote_used": remote_used,
        "remote_disabled": remote_disabled,
        "cache_hit": cache_hit,
        "oembed_count": len(oembed_items),
    }
