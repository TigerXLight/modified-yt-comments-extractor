from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from source_adapters import find_source_adapter


ARCHIVE_SERVICE_WAYBACK = "internet_archive_wayback"
ARCHIVE_SERVICE_ARCHIVE_TODAY = "archive_today"
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

DISCUSSION_MODE_COMMENTS = "comments"
DISCUSSION_MODE_LIVECHAT = "livechat"

SOURCE_RESOURCE_SCOPE = (
    "local source-resource scaffold only; no fetch, network, scraping, browser, "
    "screenshot, download, archive check, archive submit, provider, credential, "
    "or external process behavior"
)

_URL_START_RE = re.compile(r"https?://", re.IGNORECASE)
_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"ocid", "cid", "cvid", "pc", "ei", "form", "spm"}


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
    return (value or "").strip().strip("\"'<>[]{}").rstrip(".,;:)]}")


def extract_source_url_tokens(text: str) -> tuple[str, ...]:
    """Extract http/https URL tokens while leaving arbitrary words alone."""
    source = text or ""
    matches = list(_URL_START_RE.finditer(source))
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
    adapter = find_source_adapter(url)
    if adapter is None:
        raise ValueError(f"No supported source adapter for URL: {url}")
    if adapter.source_name == "msn":
        canonical = canonicalize_msn_url(url)
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
                ARCHIVE_SERVICE_ARCHIVEBOX,
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
            ARCHIVE_SERVICE_ARCHIVEBOX,
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


def _msn_fixture_resources(row_id: str) -> tuple[tuple[SourceResourceItem, ...], tuple[SourceResourceItem, ...]]:
    image_items = (
        SourceResourceItem(
            resource_id=f"{row_id}:image:hero",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_IMAGE,
            reference_url="fixture://msn/special-dj/hero.jpg",
            display_name="Special DJ hero image",
            media_type="image",
            mime_type="image/jpeg",
            extension="jpg",
            width=1280,
            height=720,
        ),
        SourceResourceItem(
            resource_id=f"{row_id}:image:loop",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_IMAGE,
            reference_url="fixture://msn/special-dj/loop.gif",
            display_name="Special DJ animated image",
            media_type="gif",
            mime_type="image/gif",
            extension="gif",
            width=640,
            height=360,
            animated=True,
        ),
    )
    media_items = (
        SourceResourceItem(
            resource_id=f"{row_id}:media:clip",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
            reference_url="fixture://msn/special-dj/clip.mp4",
            display_name="Special DJ video clip",
            media_type="video",
            mime_type="video/mp4",
            extension="mp4",
            width=1920,
            height=1080,
            duration_seconds=42.5,
            bitrate_or_quality="1080p",
        ),
        SourceResourceItem(
            resource_id=f"{row_id}:media:audio",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
            reference_url="fixture://msn/special-dj/audio.mp3",
            display_name="Special DJ audio",
            media_type="audio",
            mime_type="audio/mpeg",
            extension="mp3",
            duration_seconds=42.5,
            bitrate_or_quality="128 kbps",
        ),
    )
    return image_items, media_items


def build_source_resource_row(
    raw_url: str,
    *,
    archive_auto_check_enabled: bool = True,
    title: str = "",
) -> SourceResourceRowState:
    adapter, canonical, source_id = _canonicalize_for_adapter(raw_url)
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
    if adapter.source_name == "msn":
        display_title = title.strip() or "Special DJ by TAKU INOUE"
        image_items, media_items = _msn_fixture_resources(row_id)
        comments_status = "MSN comment fixture support only; no live fetch."
        livechat_status = "MSN livechat is not supported."
        provenance = "local MSN fixture"
        warnings.append(
            "MSN source row uses deterministic local fixture data; no page fetch, shadow-root traversal, or comment capture performed."
        )
    elif adapter.source_name != "youtube":
        comments_status = "Discussion capture is not supported for this adapter."
        livechat_status = "Livechat is not supported for this adapter."

    display_label = f"{display_title} - {parsed.netloc}"
    capabilities = adapter.capabilities
    return SourceResourceRowState(
        row_id=row_id,
        raw_url=raw_url,
        canonical_url=canonical,
        adapter_id=adapter.source_name,
        adapter_display_name=adapter_display_name,
        source_id=source_id,
        title=display_title,
        domain=parsed.netloc,
        display_label=display_label,
        comments_supported=capabilities.supports_comments,
        livechat_supported=capabilities.supports_livechat,
        comments_status=comments_status,
        livechat_status=livechat_status,
        archive_statuses=_default_archive_statuses(archive_auto_check_enabled),
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
        part for part in non_url_words if not _URL_START_RE.match(part)
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
    return tuple(
        (row.row_id, row.display_label)
        for row in rows
        if row.comments_supported or row.livechat_supported
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
