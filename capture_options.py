from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


CAPTURE_POSTS = "posts"
CAPTURE_COMMENTS = "comments"
CAPTURE_REPLIES = "replies"
CAPTURE_LIVE_CHAT = "live_chat"
CAPTURE_CAPTIONS_TRANSCRIPTS = "captions_transcripts"
CAPTURE_FULL_PAGE_SCREENSHOT = "full_page_screenshot"
CAPTURE_VISIBLE_PAGE_TEXT = "visible_page_text"
CAPTURE_READABLE_ARTICLE_TEXT = "readable_article_text"
CAPTURE_HTML_SNAPSHOT = "html_snapshot"
CAPTURE_ARCHIVE_CHECK = "archive_check"
CAPTURE_ARCHIVE_SUBMIT = "archive_submit"
CAPTURE_VIDEO_MEDIA_EVIDENCE = "video_media_evidence"
CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS = "media_source_chain_fields"
CAPTURE_DISPUTED_FRAMING_NOTES = "disputed_framing_notes"
CAPTURE_SOURCE_ROLE_LABELS = "source_role_labels"

CAPTURE_STAGE_AVAILABLE = "available"
CAPTURE_STAGE_PLANNED = "planned"
CAPTURE_STAGE_FUTURE_ONLY = "future_only"

CAPTURE_ACCESS_PUBLIC_ONLY = "public_only"
CAPTURE_ACCESS_VISIBLE_ONLY = "visible_only"
CAPTURE_ACCESS_USER_AUTHENTICATED_FUTURE = "user_authenticated_future"
CAPTURE_ACCESS_MANUAL_IMPORT = "manual_import"
CAPTURE_ACCESS_NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CaptureOptionMetadata:
    option_id: str
    display_name: str
    description: str = ""
    stage: str = CAPTURE_STAGE_PLANNED
    default_enabled_for_total_export: bool = False
    requires_user_confirmation: bool = False
    sends_data_to_external_service: bool = False
    access_mode_hint: str = CAPTURE_ACCESS_NOT_APPLICABLE
    evidence_oriented: bool = True
    safety_notes: str = ""
    implementation_notes: str = ""


@dataclass(frozen=True)
class CaptureOptionSelection:
    selected_option_ids: tuple[str, ...] = ()
    unknown_option_ids: tuple[str, ...] = ()
    duplicate_option_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


CAPTURE_OPTION_METADATA = (
    CaptureOptionMetadata(
        option_id=CAPTURE_POSTS,
        display_name="Posts",
        description="Future source-adapter metadata for source posts/items where supported.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
        implementation_notes="For non-YouTube source adapters; no current behavior is wired here.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_COMMENTS,
        display_name="Comments",
        description="Capture normal comments where the source adapter supports them.",
        stage=CAPTURE_STAGE_AVAILABLE,
        default_enabled_for_total_export=True,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
        implementation_notes="Current YouTube comment behavior remains implemented elsewhere.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_REPLIES,
        display_name="Replies",
        description="Capture nested replies where the source adapter supports them.",
        stage=CAPTURE_STAGE_AVAILABLE,
        default_enabled_for_total_export=True,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
        implementation_notes="Current YouTube reply behavior remains implemented elsewhere.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_LIVE_CHAT,
        display_name="Live chat",
        description="Capture live chat where available for the source.",
        stage=CAPTURE_STAGE_AVAILABLE,
        default_enabled_for_total_export=True,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
        implementation_notes="Current YouTube live chat behavior remains implemented elsewhere.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_CAPTIONS_TRANSCRIPTS,
        display_name="Captions/transcripts",
        description="Capture captions or transcript text where available and selected.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_FULL_PAGE_SCREENSHOT,
        display_name="Full-page screenshot",
        description="Future user-triggered full-page screenshot capture.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_VISIBLE_ONLY,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_VISIBLE_PAGE_TEXT,
        display_name="Visible page text",
        description="Future extraction of currently visible page text.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_VISIBLE_ONLY,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_READABLE_ARTICLE_TEXT,
        display_name="Readable/article text",
        description="Future readable/article text extraction when explicitly selected.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_VISIBLE_ONLY,
        safety_notes="Do not force article-body extraction when only comments are selected.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_HTML_SNAPSHOT,
        display_name="HTML snapshot",
        description="Future HTML/source snapshot where allowed and selected.",
        stage=CAPTURE_STAGE_PLANNED,
        access_mode_hint=CAPTURE_ACCESS_VISIBLE_ONLY,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_ARCHIVE_CHECK,
        display_name="Archive check",
        description="Read-only lookup for existing archive captures.",
        stage=CAPTURE_STAGE_PLANNED,
        default_enabled_for_total_export=True,
        requires_user_confirmation=False,
        sends_data_to_external_service=False,
        safety_notes="Read-only lookup; failure is not proof content did not exist.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_ARCHIVE_SUBMIT,
        display_name="Archive submit",
        description="Submit/save URL to an external archive service.",
        stage=CAPTURE_STAGE_PLANNED,
        default_enabled_for_total_export=False,
        requires_user_confirmation=True,
        sends_data_to_external_service=True,
        safety_notes="Explicit user action required because it submits a URL to an external archive service.",
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_VIDEO_MEDIA_EVIDENCE,
        display_name="Video/media evidence",
        description="Future selectable video/media evidence workflow.",
        stage=CAPTURE_STAGE_FUTURE_ONLY,
        default_enabled_for_total_export=False,
        requires_user_confirmation=True,
        access_mode_hint=CAPTURE_ACCESS_PUBLIC_ONLY,
        safety_notes=(
            "No DRM, paywall, login, bypass, private, or restricted capture; "
            "user-triggered evidence workflow only."
        ),
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS,
        display_name="Media source-chain fields",
        description="Future metadata fields for tracking where media was observed and reposted.",
        stage=CAPTURE_STAGE_FUTURE_ONLY,
        default_enabled_for_total_export=False,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_DISPUTED_FRAMING_NOTES,
        display_name="Disputed framing notes",
        description="Future notes for publisher framing disputes or source-author corrections.",
        stage=CAPTURE_STAGE_FUTURE_ONLY,
        default_enabled_for_total_export=False,
    ),
    CaptureOptionMetadata(
        option_id=CAPTURE_SOURCE_ROLE_LABELS,
        display_name="Source-role labels",
        description="Future claim/source role labels for evidence review.",
        stage=CAPTURE_STAGE_FUTURE_ONLY,
        default_enabled_for_total_export=False,
    ),
)


def available_capture_options() -> tuple[CaptureOptionMetadata, ...]:
    return CAPTURE_OPTION_METADATA


def get_capture_option(option_id: str) -> Optional[CaptureOptionMetadata]:
    for option in CAPTURE_OPTION_METADATA:
        if option.option_id == option_id:
            return option
    return None


def default_total_export_capture_option_ids() -> tuple[str, ...]:
    return tuple(
        option.option_id
        for option in CAPTURE_OPTION_METADATA
        if option.default_enabled_for_total_export
    )


def future_only_capture_option_ids() -> tuple[str, ...]:
    return tuple(
        option.option_id
        for option in CAPTURE_OPTION_METADATA
        if option.stage == CAPTURE_STAGE_FUTURE_ONLY
    )


def capture_options_requiring_confirmation() -> tuple[CaptureOptionMetadata, ...]:
    return tuple(
        option for option in CAPTURE_OPTION_METADATA if option.requires_user_confirmation
    )


def normalize_capture_option_ids(
    option_ids: Sequence[str],
    *,
    allow_unknown: bool = False,
) -> CaptureOptionSelection:
    known_ids = {option.option_id for option in CAPTURE_OPTION_METADATA}
    selected_option_ids = []
    unknown_option_ids = []
    duplicate_option_ids = []
    warnings = []
    seen = set()
    seen_duplicates = set()

    for option_id in option_ids:
        normalized = (option_id or "").strip()
        if not normalized:
            continue

        if normalized in seen:
            if normalized not in seen_duplicates:
                seen_duplicates.add(normalized)
                duplicate_option_ids.append(normalized)
            continue
        seen.add(normalized)

        is_known = normalized in known_ids
        if not is_known:
            unknown_option_ids.append(normalized)
            if not allow_unknown:
                continue

        selected_option_ids.append(normalized)

    if unknown_option_ids:
        joined_unknown = ", ".join(unknown_option_ids)
        if allow_unknown:
            warnings.append(f"Unknown capture options preserved: {joined_unknown}")
        else:
            warnings.append(f"Unknown capture options ignored: {joined_unknown}")
    if duplicate_option_ids:
        joined_duplicates = ", ".join(duplicate_option_ids)
        warnings.append(f"Duplicate capture options ignored: {joined_duplicates}")

    return CaptureOptionSelection(
        selected_option_ids=tuple(selected_option_ids),
        unknown_option_ids=tuple(unknown_option_ids),
        duplicate_option_ids=tuple(duplicate_option_ids),
        warnings=tuple(warnings),
    )


def default_total_export_capture_selection() -> CaptureOptionSelection:
    return normalize_capture_option_ids(default_total_export_capture_option_ids())
