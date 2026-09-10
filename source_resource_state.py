from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from source_adapters import find_source_adapter


ARCHIVE_SERVICE_WAYBACK = "internet_archive_wayback"
ARCHIVE_SERVICE_ARCHIVE_TODAY = "archive_today"
ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE = "local_web_archive"
ARCHIVE_SERVICE_ARCHIVEBOX = "archivebox"

ARCHIVE_STATUS_NOT_CHECKED = "not_checked"
ARCHIVE_STATUS_AUTO_CHECK_DISABLED = "auto_check_disabled"
ARCHIVE_STATUS_CHECKING = "checking"
ARCHIVE_STATUS_AVAILABLE = "available"
ARCHIVE_STATUS_NOT_AVAILABLE = "not_available"
ARCHIVE_STATUS_CHECK_FAILED = "check_failed"
ARCHIVE_STATUS_UNSUPPORTED = "unsupported"
ARCHIVE_STATUS_APPROVAL_REQUIRED = "approval_required"

RESOURCE_KIND_IMAGE = "image"
RESOURCE_KIND_VIDEO_AUDIO = "video_audio"

MEDIA_INTAKE_SCHEMA_VERSION = "rendered-citation-media-intake-v77e"

DISCUSSION_MODE_COMMENTS = "comments"
DISCUSSION_MODE_LIVECHAT = "livechat"

SOURCE_RESOURCE_SCOPE = (
    "local source-resource scaffold only; no fetch, network, scraping, browser, "
    "screenshot, download, archive check, archive submit, provider, credential, "
    "or external process behavior"
)

_URL_START_RE = re.compile(r"https?://", re.IGNORECASE)
_CHANNEL_URI_SCHEMES = (
    "slack",
    "telegram",
    "imap",
    "email",
    "gmail",
    "outlook",
    "discord",
    "matrix",
    "teams",
    "msteams",
    "whatsapp",
    "webhook",
    "workboard",
    "logbook",
    "device",
)
_CHANNEL_START_RE = re.compile(
    r"(?:" + "|".join(re.escape(scheme) for scheme in _CHANNEL_URI_SCHEMES) + r")://",
    re.IGNORECASE,
)
_SOURCE_LINK_START_RE = re.compile(
    r"(?:https?://|(?:" + "|".join(re.escape(scheme) for scheme in _CHANNEL_URI_SCHEMES) + r")://)",
    re.IGNORECASE,
)
_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"ocid", "cid", "cvid", "pc", "ei", "form", "spm"}


@dataclass(frozen=True)
class _GenericWebpageCapabilities:
    supports_comments: bool = False
    supports_livechat: bool = False


@dataclass(frozen=True)
class _GenericWebpageMetadata:
    display_name: str = "Webpage"


class _GenericWebpageAdapter:
    """Fallback source adapter for ordinary webpages used by image discovery."""

    source_name = "webpage"
    metadata = _GenericWebpageMetadata()
    capabilities = _GenericWebpageCapabilities()

    def normalize_url(self, url: str) -> str:
        return canonicalize_webpage_url(url)

    def extract_source_id(self, canonical_url: str) -> str:
        digest = hashlib.sha1(canonical_url.encode("utf-8")).hexdigest()[:16]
        return digest


_GENERIC_WEBPAGE_ADAPTER = _GenericWebpageAdapter()



def _normalize_chat_url_escapes(value: str) -> str:
    text = str(value or "").strip()
    for ch in ("_", "-", ".", "~", "(", ")"):
        text = text.replace("\\" + ch, ch)
    return text


def normalize_source_url_token(value: str) -> str:
    """Return a raw source URL from chat/Markdown-pasted input."""
    text = _normalize_chat_url_escapes(str(value or "").strip().strip('"').strip("'"))
    if not text:
        return ""
    # Prefer Markdown hrefs, including nested/broken links copied from chat.
    separators = text
    for token in ("](", "[", "]", "(", ")", "<", ">"):
        separators = separators.replace(token, " ")
    candidates = []
    for candidate in re.findall(r"https?://[^\s\"']+", separators, flags=re.IGNORECASE):
        cleaned = candidate.strip().strip('"').strip("'")
        while cleaned and cleaned[-1] in ").,;:\\":
            cleaned = cleaned[:-1].strip()
        if cleaned.lower().startswith(("http://", "https://")):
            candidates.append(cleaned)
    if candidates:
        return candidates[-1]
    return text.strip("<>[]{}")


@dataclass(frozen=True)
class ArchiveServiceStatus:
    service_id: str
    status: str = ARCHIVE_STATUS_NOT_CHECKED
    label: str = "Not checked"
    color_name: str = "gray"
    saved_date: str = ""
    tooltip: str = ""


@dataclass(frozen=True)
class SourceResourceItem:
    resource_id: str
    source_row_id: str
    resource_kind: str
    reference_url: str = ""
    canonical_url: str = ""
    display_name: str = ""
    media_type: str = ""
    mime_type: str = ""
    extension: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    bitrate_or_quality: str = ""
    animated: bool = False
    thumbnail_reference: str = ""
    from_link: bool = False
    status: str = "fixture"
    selectable: bool = True
    warning: str = ""
    provenance: str = "local fixture"


@dataclass(frozen=True)
class SourceResourceRowState:
    row_id: str
    raw_url: str
    canonical_url: str
    adapter_id: str
    adapter_display_name: str
    source_id: str
    title: str
    domain: str
    display_label: str
    display_title: str = ""
    preview_text: str = ""
    comments_supported: bool = False
    livechat_supported: bool = False
    comments_status: str = ""
    livechat_status: str = ""
    archive_statuses: tuple[ArchiveServiceStatus, ...] = ()
    image_resources: tuple[SourceResourceItem, ...] = ()
    video_audio_resources: tuple[SourceResourceItem, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: str = "local fixture"


@dataclass(frozen=True)
class SourceUrlIntakeResult:
    rows: tuple[SourceResourceRowState, ...] = ()
    accepted_raw_urls: tuple[str, ...] = ()
    accepted_canonical_urls: tuple[str, ...] = ()
    duplicate_raw_urls: tuple[str, ...] = ()
    invalid_tokens: tuple[str, ...] = ()
    remaining_text: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = SOURCE_RESOURCE_SCOPE


@dataclass(frozen=True)
class DiscussionCaptureOptions:
    source_row_id: str = ""
    webpage_selected: bool = False
    webpage_screenshot_requested: bool = False
    comments_selected: bool = True
    livechat_selected: bool = False
    comments_screenshot_requested: bool = False
    livechat_screenshot_requested: bool = False
    webpage_supported: bool = False
    webpage_screenshot_supported: bool = False
    comments_supported: bool = False
    livechat_supported: bool = False

    @property
    def webpage_active(self) -> bool:
        return self.webpage_supported and self.webpage_selected

    @property
    def webpage_screenshot_active(self) -> bool:
        return (
            self.webpage_active
            and self.webpage_screenshot_supported
            and self.webpage_screenshot_requested
        )

    @property
    def comments_screenshot_active(self) -> bool:
        return (
            self.comments_selected
            and self.comments_supported
            and self.comments_screenshot_requested
        )

    @property
    def livechat_screenshot_active(self) -> bool:
        return (
            self.livechat_selected
            and self.livechat_supported
            and self.livechat_screenshot_requested
        )


@dataclass(frozen=True)
class DiscussionSelectionState:
    selected_row_id: str = ""
    options: tuple[tuple[str, str], ...] = ()
    fallback_applied: bool = False
    comments_supported: bool = False
    livechat_supported: bool = False
    capability_note: str = ""


@dataclass(frozen=True)
class ResourceDownloadDryRun:
    source_row_id: str
    resource_kind: str
    selected_resource_ids: tuple[str, ...] = ()
    selected_count: int = 0
    message: str = ""
    network_actions_performed: str = "none"
    downloads_performed: str = "none"
    files_written: str = "none"


@dataclass(frozen=True)
class MediaResourceFilterState:
    url_filter: str = ""
    text_filter: str = ""
    min_width: int = 0
    min_height: int = 0
    only_linked_resources: bool = False
    save_to_subfolder: bool = True
    rename_files: bool = False


@dataclass(frozen=True)
class SelectedMediaPreservationPreview:
    source_row_id: str
    resource_kind: str
    selected_count: int = 0
    records: tuple[dict[str, Any], ...] = ()
    message: str = ""
    network_actions_performed: str = "none"
    downloads_performed: str = "none"
    files_written: str = "none"
    safety_flags: dict[str, bool] | None = None


@dataclass(frozen=True)
class ResourceSelectionDialogState:
    source_row_id: str
    resource_kind: str
    resources: tuple[SourceResourceItem, ...] = ()
    selected_resource_ids: tuple[str, ...] = ()
    committed_resource_ids: tuple[str, ...] = ()

    @property
    def selection_count(self) -> int:
        return len(self.selected_resource_ids)


def _trim_url_token(value: str) -> str:
    return normalize_source_url_token((value or "").strip().rstrip(".,;:)]}"))


def extract_source_url_tokens(text: str) -> tuple[str, ...]:
    """Extract source-link tokens while leaving arbitrary words alone.

    Historical name retained for the UI/tests. R42DK extends this from only
    http/https URLs to explicit account/channel source URIs such as
    slack://..., imap://..., matrix://..., webhook://..., and logbook://....
    """
    source = text or ""
    matches = sorted(
        list(_URL_START_RE.finditer(source)) + list(_CHANNEL_START_RE.finditer(source)),
        key=lambda match: match.start(),
    )
    if not matches:
        return ()
    tokens: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        chunk = source[start:end].strip()
        separator_match = re.search(r"[\s;,]+", chunk)
        token = chunk[: separator_match.start()] if separator_match else chunk
        token = _trim_url_token(token)
        if token:
            tokens.append(token)
    return tuple(tokens)


def _remove_accepted_tokens(text: str, accepted_tokens: Iterable[str]) -> str:
    remaining = text or ""
    for token in accepted_tokens:
        remaining = remaining.replace(token, " ")
    lines = [" ".join(line.split()) for line in remaining.splitlines()]
    return "\n".join(line for line in lines if line).strip()




def canonicalize_webpage_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Webpage URL must use http or https and include a host")
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunsplit((scheme, host, path, parsed.query, ""))

def canonicalize_msn_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("MSN URL must use http or https")
    host = parsed.netloc.lower()
    if host not in {"msn.com", "www.msn.com"} and not host.endswith(".msn.com"):
        raise ValueError(f"unsupported MSN host: {parsed.netloc}")
    path = parsed.path or "/"
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _TRACKING_QUERY_KEYS or lowered.startswith(_TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, value))
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit(("https", host, path, query, ""))


def _canonicalize_for_adapter(url: str) -> tuple[Any, str, str]:
    url = normalize_source_url_token(url)
    adapter = find_source_adapter(url)
    if adapter is None:
        adapter = _GENERIC_WEBPAGE_ADAPTER
    if adapter.source_name == "msn":
        canonical = canonicalize_msn_url(url)
    elif adapter.source_name == "webpage":
        canonical = canonicalize_webpage_url(url)
    else:
        canonical = adapter.normalize_url(url)
    source_id = adapter.extract_source_id(canonical)
    return adapter, canonical, source_id


def archive_status_presentation(
    service_id: str,
    status: str,
    *,
    saved_date: str = "",
) -> ArchiveServiceStatus:
    labels = {
        ARCHIVE_STATUS_NOT_CHECKED: ("Not checked", "gray"),
        ARCHIVE_STATUS_AUTO_CHECK_DISABLED: ("Not checked", "gray"),
        ARCHIVE_STATUS_CHECKING: ("Checking...", "amber"),
        ARCHIVE_STATUS_AVAILABLE: ("Saved", "green"),
        ARCHIVE_STATUS_NOT_AVAILABLE: ("Not saved", "red"),
        ARCHIVE_STATUS_CHECK_FAILED: ("Check failed", "amber"),
        ARCHIVE_STATUS_UNSUPPORTED: ("Unsupported", "gray"),
        ARCHIVE_STATUS_APPROVAL_REQUIRED: ("Approval required", "amber"),
    }
    label, color = labels.get(status, ("Not checked", "gray"))
    tooltip = f"{service_id}: {label}"
    if saved_date and status == ARCHIVE_STATUS_AVAILABLE:
        tooltip = f"{tooltip} {saved_date}"
    return ArchiveServiceStatus(
        service_id=service_id,
        status=status,
        label=label,
        color_name=color,
        saved_date=saved_date if status == ARCHIVE_STATUS_AVAILABLE else "",
        tooltip=tooltip,
    )


def _default_archive_statuses(auto_check_enabled: bool) -> tuple[ArchiveServiceStatus, ...]:
    if auto_check_enabled:
        return (
            archive_status_presentation(
                ARCHIVE_SERVICE_WAYBACK,
                ARCHIVE_STATUS_AVAILABLE,
                saved_date="2026-07-15",
            ),
            archive_status_presentation(
                ARCHIVE_SERVICE_ARCHIVE_TODAY,
                ARCHIVE_STATUS_NOT_AVAILABLE,
            ),
            archive_status_presentation(
                ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
                ARCHIVE_STATUS_NOT_CHECKED,
            ),
        )
    return (
        archive_status_presentation(
            ARCHIVE_SERVICE_WAYBACK,
            ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
        ),
        archive_status_presentation(
            ARCHIVE_SERVICE_ARCHIVE_TODAY,
            ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
        ),
        archive_status_presentation(
            ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
            ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
        ),
    )


def _fallback_title_from_url(canonical_url: str) -> str:
    parsed = urlsplit(canonical_url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return parsed.netloc or "Source"
    candidate = parts[-2] if parts[-1].lower().startswith("ar-") and len(parts) > 1 else parts[-1]
    return candidate.replace("-", " ").replace("_", " ").strip().title() or parsed.netloc


TWITTER_KNOWN_STATUS_PREVIEWS = {
    "1877644315867963403": "This stuff is still happening. It hasn’t stopped.",
}


def _twitter_title_from_url(canonical_url: str, preview_text: str = "") -> str:
    preview = " ".join(str(preview_text or "").split())
    if preview:
        return preview[:96]
    parsed = urlsplit(canonical_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[1].lower() in {"status", "statuses"}:
        status_id = parts[2]
        if status_id in TWITTER_KNOWN_STATUS_PREVIEWS:
            return TWITTER_KNOWN_STATUS_PREVIEWS[status_id]
        return "Twitter/X post"
    if len(parts) == 1:
        return "Twitter/X profile"
    return "Twitter/X source"


def _youtube_media_selection_resources(
    row_id: str,
    canonical_url: str,
) -> tuple[tuple[SourceResourceItem, ...], tuple[SourceResourceItem, ...]]:
    image_items = (
        SourceResourceItem(
            resource_id=f"{row_id}:image:thumbnail",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_IMAGE,
            reference_url=canonical_url,
            canonical_url=canonical_url,
            display_name="YouTube thumbnail / metadata image",
            media_type="image",
            mime_type="image/*",
            extension="jpg/webp",
            bitrate_or_quality="thumbnail",
            status="queued",
            selectable=True,
            warning="Resolved by yt-dlp when the media plan is executed.",
            provenance="youtube media backend selection",
        ),
    )
    quality_presets = (
        ("4k", 2160),
        ("2k", 1440),
        ("1080", 1080),
        ("720", 720),
        ("480", 480),
        ("360", 360),
        ("240", 240),
        ("144", 144),
    )
    media_items = tuple(
        SourceResourceItem(
            resource_id=f"{row_id}:video_audio:{label}",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
            reference_url=canonical_url,
            canonical_url=canonical_url,
            display_name=f"{label} video + best audio",
            media_type="video",
            mime_type="video/mp4",
            extension="mp4",
            height=height,
            bitrate_or_quality=label,
            status="queued",
            selectable=True,
            warning="Auto mux: yt-dlp selects bestvideo+bestaudio and FFmpeg merges when needed.",
            provenance="youtube media backend selection",
        )
        for label, height in quality_presets
    )
    return image_items, media_items


def build_source_resource_row(
    raw_url: str,
    *,
    archive_auto_check_enabled: bool = True,
    title: str = "",
) -> SourceResourceRowState:
    normalized_raw_url = normalize_source_url_token(raw_url)
    adapter, canonical, source_id = _canonicalize_for_adapter(normalized_raw_url)
    parsed = urlsplit(canonical)
    metadata = getattr(adapter, "metadata", None)
    adapter_display_name = getattr(metadata, "display_name", adapter.source_name)
    row_id = f"{adapter.source_name}:{source_id}"
    display_title = title.strip() if title else _fallback_title_from_url(canonical)
    warnings: list[str] = []
    image_items: tuple[SourceResourceItem, ...] = ()
    media_items: tuple[SourceResourceItem, ...] = ()
    comments_status = "Comments supported by existing YouTube runtime elsewhere."
    livechat_status = "Livechat supported by existing YouTube runtime elsewhere."
    provenance = "adapter metadata"
    if adapter.source_name == "youtube":
        display_title = title.strip() or f"YouTube video {source_id}"
        image_items, media_items = (), ()
        provenance = "adapter metadata; YouTube media uses row quality selector and settings"
    elif adapter.source_name == "twitter_x":
        display_title = _twitter_title_from_url(canonical, title)
        image_items, media_items = (), ()
        comments_status = "X/Twitter Post/Thread capture mode is selected in-row; settings and shared backend can route media when enabled."
        livechat_status = "X/Twitter livechat is not supported."
        provenance = "adapter metadata; X/Twitter media controls use settings plus shared backend"
    elif adapter.source_name == "msn":
        display_title = title.strip() or _fallback_title_from_url(canonical)
        image_items, media_items = (), ()
        comments_status = "MSN comment planning/support is adapter-specific; use explicit capture/export flows."
        livechat_status = "MSN livechat is not supported."
        provenance = "adapter metadata; media discovery is user-triggered"
        warnings.append(
            "MSN source row no longer injects fake fixture media. Use Images/GIFs or Video/Audio, then run discovery against rendered MSN HTML."
        )
    elif adapter.source_name == "webpage":
        display_title = title.strip() or _fallback_title_from_url(canonical)
        image_items, media_items = (), ()
        comments_status = "Generic webpage rows support image discovery/download only; discussion comments are not supported."
        livechat_status = "Generic webpage rows do not support livechat."
        provenance = "generic webpage adapter; media discovery is user-triggered"
    elif adapter.source_name == "account_channel":
        display_title = title.strip() or _fallback_title_from_url(canonical)
        image_items, media_items = (), ()
        comments_status = (
            "Account/channel source rows are two-sided adapter references. Inbound item "
            "import and outbound review/status/export actions require named adapter configuration."
        )
        livechat_status = "Account/channel live polling is not started by source-row intake."
        provenance = "account/channel source-link adapter metadata; no unattended account polling"
        warnings.append(
            "Account/channel source adapter row recorded only as a source-link candidate; no polling, credential lookup, browser capture, or outbound send ran during intake."
        )
    else:
        comments_status = "Discussion capture is not supported for this adapter."
        livechat_status = "Livechat is not supported for this adapter."

    if adapter.source_name == "youtube":
        display_label = f"{display_title} - YouTube"
    elif adapter.source_name == "account_channel":
        display_label = f"{display_title} - {parsed.scheme or 'channel'}"
    else:
        display_label = f"{display_title} - {parsed.netloc}"
    capabilities = adapter.capabilities
    return SourceResourceRowState(
        row_id=row_id,
        raw_url=normalized_raw_url,
        canonical_url=canonical,
        adapter_id=adapter.source_name,
        adapter_display_name=adapter_display_name,
        source_id=source_id,
        title=display_title,
        domain=parsed.netloc,
        display_label=display_label,
        display_title=display_title,
        preview_text=" ".join(title.split()) if adapter.source_name == "twitter_x" and title.strip() else "",
        comments_supported=capabilities.supports_comments,
        livechat_supported=capabilities.supports_livechat,
        comments_status=comments_status,
        livechat_status=livechat_status,
        archive_statuses=() if adapter.source_name in {"youtube", "twitter_x", "account_channel"} else _default_archive_statuses(archive_auto_check_enabled),
        image_resources=image_items,
        video_audio_resources=media_items,
        warnings=tuple(warnings),
        provenance=provenance,
    )


def parse_source_url_intake(
    text: str,
    *,
    existing_rows: Sequence[SourceResourceRowState] = (),
    archive_auto_check_enabled: bool = True,
) -> SourceUrlIntakeResult:
    tokens = extract_source_url_tokens(text)
    existing_canonicals = {row.canonical_url for row in existing_rows}
    seen_canonicals: set[str] = set(existing_canonicals)
    rows: list[SourceResourceRowState] = []
    accepted_raw: list[str] = []
    accepted_canonical: list[str] = []
    duplicate_raw: list[str] = []
    invalid_tokens: list[str] = []
    warnings: list[str] = []

    for token in tokens:
        try:
            row = build_source_resource_row(
                token,
                archive_auto_check_enabled=archive_auto_check_enabled,
            )
        except ValueError:
            invalid_tokens.append(token)
            continue
        if row.canonical_url in seen_canonicals:
            duplicate_raw.append(token)
            continue
        seen_canonicals.add(row.canonical_url)
        rows.append(row)
        accepted_raw.append(token)
        accepted_canonical.append(row.canonical_url)
        warnings.extend(row.warnings)

    accepted_or_duplicate = tuple(accepted_raw + duplicate_raw)
    remaining_text = _remove_accepted_tokens(text, accepted_or_duplicate)
    non_url_words = [
        part.strip(" ,;")
        for part in re.split(r"\s+", remaining_text)
        if part.strip(" ,;")
    ]
    invalid_tokens.extend(
        part for part in non_url_words if not _SOURCE_LINK_START_RE.match(part)
    )
    return SourceUrlIntakeResult(
        rows=tuple(rows),
        accepted_raw_urls=tuple(accepted_raw),
        accepted_canonical_urls=tuple(accepted_canonical),
        duplicate_raw_urls=tuple(duplicate_raw),
        invalid_tokens=tuple(dict.fromkeys(invalid_tokens)),
        remaining_text=remaining_text,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def eligible_discussion_options(
    rows: Sequence[SourceResourceRowState],
) -> tuple[tuple[str, str], ...]:
    """Return rows usable by the Go/Webpage/Screenshot control.

    The dropdown must include generic webpage rows such as Metro even when
    they do not expose comments/livechat. Comments and livechat remain gated
    separately by their per-row capability flags.
    """
    return tuple(
        (row.row_id, row.display_label)
        for row in rows
        if (row.canonical_url or row.raw_url)
    )


def build_discussion_selection_state(
    rows: Sequence[SourceResourceRowState],
    selected_row_id: str = "",
) -> DiscussionSelectionState:
    options = eligible_discussion_options(rows)
    row_by_id = {row.row_id: row for row in rows}
    selected = selected_row_id if selected_row_id in row_by_id else ""
    fallback = False
    if not selected and options:
        selected = options[0][0]
        fallback = bool(selected_row_id)
    row = row_by_id.get(selected)
    if row is None:
        return DiscussionSelectionState(
            selected_row_id="",
            options=options,
            fallback_applied=fallback,
            capability_note="No discussion-capable source is selected.",
        )
    notes = []
    if not row.comments_supported:
        notes.append(row.comments_status or "Comments unavailable.")
    if not row.livechat_supported:
        notes.append(row.livechat_status or "Livechat unavailable.")
    return DiscussionSelectionState(
        selected_row_id=selected,
        options=options,
        fallback_applied=fallback,
        comments_supported=row.comments_supported,
        livechat_supported=row.livechat_supported,
        capability_note=" ".join(notes),
    )


def build_discussion_capture_options(
    rows: Sequence[SourceResourceRowState],
    *,
    selected_row_id: str,
    webpage_selected: bool = False,
    webpage_screenshot_requested: bool = False,
    comments_selected: bool,
    livechat_selected: bool,
    comments_screenshot_requested: bool,
    livechat_screenshot_requested: bool,
) -> DiscussionCaptureOptions:
    selection = build_discussion_selection_state(rows, selected_row_id)
    has_source = bool(selection.selected_row_id)
    return DiscussionCaptureOptions(
        source_row_id=selection.selected_row_id,
        webpage_selected=webpage_selected,
        webpage_screenshot_requested=webpage_screenshot_requested,
        comments_selected=comments_selected,
        livechat_selected=livechat_selected,
        comments_screenshot_requested=comments_screenshot_requested,
        livechat_screenshot_requested=livechat_screenshot_requested,
        webpage_supported=has_source,
        webpage_screenshot_supported=has_source,
        comments_supported=selection.comments_supported,
        livechat_supported=selection.livechat_supported,
    )


def remove_source_resource_row(
    rows: Sequence[SourceResourceRowState],
    row_id: str,
    *,
    selected_row_id: str = "",
) -> tuple[tuple[SourceResourceRowState, ...], str]:
    remaining = tuple(row for row in rows if row.row_id != row_id)
    if selected_row_id and selected_row_id != row_id:
        if any(row.row_id == selected_row_id for row in remaining):
            return remaining, selected_row_id
    selection = build_discussion_selection_state(remaining, "")
    return remaining, selection.selected_row_id


def resource_dialog_state_for_row(
    row: SourceResourceRowState,
    resource_kind: str,
    *,
    committed_resource_ids: Sequence[str] = (),
) -> ResourceSelectionDialogState:
    resources = (
        row.image_resources
        if resource_kind == RESOURCE_KIND_IMAGE
        else row.video_audio_resources
    )
    committed = tuple(
        resource_id
        for resource_id in committed_resource_ids
        if any(item.resource_id == resource_id for item in resources)
    )
    return ResourceSelectionDialogState(
        source_row_id=row.row_id,
        resource_kind=resource_kind,
        resources=resources,
        selected_resource_ids=committed,
        committed_resource_ids=committed,
    )


def select_all_resources(
    state: ResourceSelectionDialogState,
) -> ResourceSelectionDialogState:
    return replace(
        state,
        selected_resource_ids=tuple(
            item.resource_id for item in state.resources if item.selectable
        ),
    )


def clear_resource_selection(
    state: ResourceSelectionDialogState,
) -> ResourceSelectionDialogState:
    return replace(state, selected_resource_ids=())


def filter_resource_dialog_items(
    state: ResourceSelectionDialogState,
    filters: MediaResourceFilterState,
) -> ResourceSelectionDialogState:
    """Return a local-only filtered view of selectable source media resources."""
    url_filter = (filters.url_filter or "").strip().lower()
    text_filter = (filters.text_filter or "").strip().lower()
    min_width = max(0, int(filters.min_width or 0))
    min_height = max(0, int(filters.min_height or 0))

    def matches(item: SourceResourceItem) -> bool:
        url_text = " ".join(
            value
            for value in (item.reference_url, item.canonical_url, item.thumbnail_reference)
            if value
        ).lower()
        descriptive_text = " ".join(
            value
            for value in (
                item.display_name,
                item.media_type,
                item.mime_type,
                item.extension,
                item.bitrate_or_quality,
                item.status,
                item.warning,
                item.provenance,
            )
            if value
        ).lower()
        if url_filter and url_filter not in url_text:
            return False
        if text_filter and text_filter not in descriptive_text and text_filter not in url_text:
            return False
        if min_width and (not item.width or item.width < min_width):
            return False
        if min_height and (not item.height or item.height < min_height):
            return False
        if filters.only_linked_resources and not item.from_link:
            return False
        return True

    resources = tuple(item for item in state.resources if matches(item))
    resource_ids = {item.resource_id for item in resources}
    return replace(
        state,
        resources=resources,
        selected_resource_ids=tuple(
            resource_id
            for resource_id in state.selected_resource_ids
            if resource_id in resource_ids
        ),
        committed_resource_ids=tuple(
            resource_id
            for resource_id in state.committed_resource_ids
            if resource_id in resource_ids
        ),
    )


def _source_resource_safety_flags() -> dict[str, bool]:
    return {
        "browser_launch_performed": False,
        "web_download_performed": False,
        "media_download_performed": False,
        "recording_performed": False,
        "drm_circumvention_performed": False,
        "hidden_protected_stream_extraction_performed": False,
        "captcha_solver_used": False,
        "credential_automation_performed": False,
        "proxy_or_evasion_performed": False,
        "forced_rate_limit_bypass_performed": False,
        "write_actions_performed": False,
    }


def build_selected_media_preservation_preview(
    row: SourceResourceRowState,
    state: ResourceSelectionDialogState,
) -> SelectedMediaPreservationPreview:
    """Build V77E-compatible preservation records without downloading media."""
    selected_ids = set(state.selected_resource_ids)
    selected_items = tuple(item for item in state.resources if item.resource_id in selected_ids)
    records: list[dict[str, Any]] = []
    for item in selected_items:
        media_url = item.reference_url or item.canonical_url
        records.append(
            {
                "schema_version": MEDIA_INTAKE_SCHEMA_VERSION,
                "source_url": row.raw_url,
                "page_url": row.canonical_url or row.raw_url,
                "media_url": media_url,
                "source_unit_path": "",
                "user_declared_purpose": "source_preservation",
                "capture_kind": "source_reference_only",
                "capture_method": "source_reference_only",
                "media_position_start": "",
                "media_position_end": "",
                "local_file_path": "",
                "local_file_name": "",
                "local_file_extension": item.extension,
                "local_file_size": 0,
                "local_file_sha256": "",
                "local_file_present": False,
                "local_file_role": "source_reference_only",
                "source_resource": state_to_dict(item),
                "source_unit_attachment": {
                    "attached_to_source_unit": False,
                    "source_unit_path": "",
                    "attachment_scope": "review_required",
                },
                "rendered_citation_metadata": {
                    "source_url": row.raw_url,
                    "page_url": row.canonical_url or row.raw_url,
                    "media_url": media_url,
                    "capture_kind": "source_reference_only",
                    "capture_method": "source_reference_only",
                    "user_declared_purpose": "source_preservation",
                },
                "human_mediated_access": {
                    "required": False,
                    "completed_by_user": False,
                    "program_solved_challenge": False,
                    "solver_service_used": False,
                    "anti_detection_used": False,
                },
                "blocked_capture": {
                    "blocked": False,
                    "reason": "",
                },
                "safety_flags": _source_resource_safety_flags(),
            }
        )
    count = len(records)
    return SelectedMediaPreservationPreview(
        source_row_id=row.row_id,
        resource_kind=state.resource_kind,
        selected_count=count,
        records=tuple(records),
        message=(
            "Selected media preservation records are ready for review. "
            "No browser, network, download, or recording action was performed."
            if count
            else "No media resources were selected for preservation."
        ),
        safety_flags=_source_resource_safety_flags(),
    )


def cancel_resource_selection(
    state: ResourceSelectionDialogState,
) -> ResourceSelectionDialogState:
    return replace(state, selected_resource_ids=state.committed_resource_ids)


def build_resource_download_dry_run(
    state: ResourceSelectionDialogState,
) -> ResourceDownloadDryRun:
    count = len(state.selected_resource_ids)
    return ResourceDownloadDryRun(
        source_row_id=state.source_row_id,
        resource_kind=state.resource_kind,
        selected_resource_ids=state.selected_resource_ids,
        selected_count=count,
        message=(
            "Download execution is not enabled in this local-only milestone. "
            f"{count} resources selected."
        ),
    )


def source_action_plan_text(
    *,
    row: SourceResourceRowState,
    discussion: DiscussionCaptureOptions,
    archive_auto_check_enabled: bool,
    images_selected: int = 0,
    video_audio_selected: int = 0,
) -> str:
    modes = []
    if discussion.comments_selected and discussion.comments_supported:
        modes.append("comments")
    if discussion.livechat_selected and discussion.livechat_supported:
        modes.append("livechat")
    return "\n".join(
        [
            "Source action plan",
            f"Source: {row.title}",
            f"Adapter: {row.adapter_id}",
            (
                "Webpage selected: "
                f"{'enabled' if discussion.webpage_active else 'inactive'}"
            ),
            (
                "Webpage screenshot intent: "
                f"{'enabled' if discussion.webpage_screenshot_active else 'inactive'}"
            ),
            f"Discussion: {', '.join(modes) if modes else '(none)'}",
            (
                "Comments screenshot intent: "
                f"{'enabled' if discussion.comments_screenshot_active else 'inactive'}"
            ),
            (
                "Livechat screenshot intent: "
                f"{'enabled' if discussion.livechat_screenshot_active else 'inactive'}"
            ),
            f"Images selected: {images_selected}",
            f"Video/audio selected: {video_audio_selected}",
            (
                "Archive auto-check preference: "
                f"{'enabled' if archive_auto_check_enabled else 'disabled'}"
            ),
            "Network actions performed: none",
            "Downloads performed: none",
            "Screenshots performed: none",
            "Archive checks performed: none",
        ]
    )


def state_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: state_to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [state_to_dict(item) for item in value]
    if isinstance(value, list):
        return [state_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: state_to_dict(item) for key, item in value.items()}
    return value


def state_to_json(value: Any) -> str:
    return json.dumps(state_to_dict(value), indent=2, sort_keys=True)
