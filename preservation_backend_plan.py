# Evidence bundle integration: metadata-only preservation plan field.
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from capture_method_metadata import (
    available_capture_methods,
    capture_method_by_id,
    capture_method_metadata_to_dict,
)


REPORT_FORMATS = ("markdown", "text", "json")

PLAN_STATUS_READY = "ready"
PLAN_STATUS_NEEDS_SELECTION = "needs_selection"

BACKEND_STATUS_MANUAL = "manual_import"
BACKEND_STATUS_FUTURE = "future_backend"

MEDIA_PRESERVATION_CHOICE_NONE = "none"
MEDIA_PRESERVATION_CHOICE_SELECT = "select"
MEDIA_PRESERVATION_CHOICE_ALL = "all"
MEDIA_PRESERVATION_CHOICES = (
    MEDIA_PRESERVATION_CHOICE_NONE,
    MEDIA_PRESERVATION_CHOICE_SELECT,
    MEDIA_PRESERVATION_CHOICE_ALL,
)


@dataclass(frozen=True)
class PreservationBackendOption:
    backend_id: str
    display_name: str
    status: str
    execution_supported: bool
    local_only: bool
    notes: str
    recommended_next_step: str


@dataclass(frozen=True)
class PreservationFormatOption:
    format_id: str
    display_name: str
    file_extensions: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class MediaPreservationChoice:
    choice_id: str
    display_name: str
    explicit_opt_in: bool
    notes: str


@dataclass(frozen=True)
class PreservationBackendPlan:
    source_url: str
    selected_backend_ids: tuple[str, ...]
    selected_format_ids: tuple[str, ...]
    unknown_backend_ids: tuple[str, ...]
    unknown_format_ids: tuple[str, ...]
    duplicate_backend_ids: tuple[str, ...]
    duplicate_format_ids: tuple[str, ...]
    selected_capture_method_ids: tuple[str, ...]
    unknown_capture_method_ids: tuple[str, ...]
    duplicate_capture_method_ids: tuple[str, ...]
    media_preservation_choice: str
    status: str
    warnings: tuple[str, ...]
    notes: str = ""
    evidence_bundle: Any | None = None
    scope: str = (
        "local preservation backend planning only; no fetch, capture, network, archive, "
        "browser, scraping, credential, ArchiveBox execution, media download, or GUI behavior"
    )


BACKEND_OPTIONS: tuple[PreservationBackendOption, ...] = (
    PreservationBackendOption(
        backend_id="manual_local_files",
        display_name="Manual local files",
        status=BACKEND_STATUS_MANUAL,
        execution_supported=False,
        local_only=True,
        notes=(
            "User supplies already-created local files such as HTML, PDF, PNG, TXT, JSON, WARC, "
            "media files, or metadata exports for manifest registration later."
        ),
        recommended_next_step="Register only user-supplied local files; do not capture or fetch them here.",
    ),
    PreservationBackendOption(
        backend_id="archivebox_self_hosted",
        display_name="ArchiveBox-style self-hosted store",
        status=BACKEND_STATUS_FUTURE,
        execution_supported=False,
        local_only=True,
        notes=(
            "Future backend category for user-controlled ArchiveBox-style preservation outputs. "
            "This helper records intent only and does not run ArchiveBox."
        ),
        recommended_next_step=(
            "Start with manual import of already-created ArchiveBox outputs before considering any execution integration."
        ),
    ),
)


FORMAT_OPTIONS: tuple[PreservationFormatOption, ...] = (
    PreservationFormatOption(
        format_id="html",
        display_name="HTML snapshot",
        file_extensions=(".html", ".htm"),
        notes="Local HTML or rendered-page export supplied by the user or future approved backend.",
    ),
    PreservationFormatOption(
        format_id="pdf",
        display_name="PDF snapshot",
        file_extensions=(".pdf",),
        notes="Local PDF export supplied by the user or future approved backend.",
    ),
    PreservationFormatOption(
        format_id="png",
        display_name="PNG screenshot",
        file_extensions=(".png",),
        notes="Local image/screenshot file only; this helper does not capture screenshots.",
    ),
    PreservationFormatOption(
        format_id="txt",
        display_name="Text/article extraction",
        file_extensions=(".txt",),
        notes="Local text extraction or notes supplied by the user or future approved backend.",
    ),
    PreservationFormatOption(
        format_id="json",
        display_name="JSON metadata/export",
        file_extensions=(".json",),
        notes="Local structured metadata/export file.",
    ),
    PreservationFormatOption(
        format_id="warc",
        display_name="WARC archive",
        file_extensions=(".warc", ".warc.gz"),
        notes="Local WARC file supplied by the user or future approved backend.",
    ),
    PreservationFormatOption(
        format_id="media",
        display_name="Media file",
        file_extensions=(".mp4", ".webm", ".m4a", ".mp3", ".mov"),
        notes="Local media file only; this helper does not download media.",
    ),
    PreservationFormatOption(
        format_id="sqlite",
        display_name="SQLite metadata",
        file_extensions=(".sqlite", ".sqlite3", ".db"),
        notes="Local database/metadata store supplied by the user or future approved backend.",
    ),
)


MEDIA_PRESERVATION_CHOICE_OPTIONS: tuple[MediaPreservationChoice, ...] = (
    MediaPreservationChoice(
        choice_id=MEDIA_PRESERVATION_CHOICE_NONE,
        display_name="No media preservation",
        explicit_opt_in=False,
        notes="No media asset preservation is requested or planned.",
    ),
    MediaPreservationChoice(
        choice_id=MEDIA_PRESERVATION_CHOICE_SELECT,
        display_name="Select media assets",
        explicit_opt_in=True,
        notes=(
            "The user intends to choose specific discovered or supplied media assets. "
            "This metadata does not discover or download them."
        ),
    ),
    MediaPreservationChoice(
        choice_id=MEDIA_PRESERVATION_CHOICE_ALL,
        display_name="All media assets",
        explicit_opt_in=True,
        notes=(
            "The user explicitly intends to preserve all discovered or supplied media assets. "
            "This must never be inferred or used as the default."
        ),
    ),
)


def _known_backend_ids() -> set[str]:
    return {option.backend_id for option in BACKEND_OPTIONS}


def _known_format_ids() -> set[str]:
    return {option.format_id for option in FORMAT_OPTIONS}


def _known_capture_method_ids() -> set[str]:
    return {method.method_id for method in available_capture_methods()}


def normalize_media_preservation_choice(value: str = "") -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return MEDIA_PRESERVATION_CHOICE_NONE
    if normalized not in MEDIA_PRESERVATION_CHOICES:
        raise ValueError(
            "unknown media preservation choice: "
            f"{normalized}; expected one of {', '.join(MEDIA_PRESERVATION_CHOICES)}"
        )
    return normalized


def _normalize_selection(
    values: Iterable[str],
    *,
    known_ids: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    selected: list[str] = []
    unknown: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = str(value).strip().lower()
        if not normalized:
            continue
        if normalized in seen:
            if normalized not in duplicates:
                duplicates.append(normalized)
            continue
        seen.add(normalized)
        if normalized not in known_ids:
            unknown.append(normalized)
            continue
        selected.append(normalized)

    return tuple(selected), tuple(unknown), tuple(duplicates)


def build_preservation_backend_plan(
    *,
    source_url: str = "",
    selected_backend_ids: Sequence[str] = (),
    selected_format_ids: Sequence[str] = (),
    selected_capture_method_ids: Sequence[str] = (),
    media_preservation_choice: str = MEDIA_PRESERVATION_CHOICE_NONE,
    notes: str = "",
    evidence_bundle: Any | None = None,
) -> PreservationBackendPlan:
    selected_backends, unknown_backends, duplicate_backends = _normalize_selection(
        selected_backend_ids,
        known_ids=_known_backend_ids(),
    )
    selected_formats, unknown_formats, duplicate_formats = _normalize_selection(
        selected_format_ids,
        known_ids=_known_format_ids(),
    )
    selected_capture_methods, unknown_capture_methods, duplicate_capture_methods = (
        _normalize_selection(
            selected_capture_method_ids,
            known_ids=_known_capture_method_ids(),
        )
    )
    normalized_media_choice = normalize_media_preservation_choice(
        media_preservation_choice
    )

    warnings: list[str] = []
    if unknown_backends:
        warnings.append(
            f"Unknown preservation backends ignored: {', '.join(unknown_backends)}"
        )
    if unknown_formats:
        warnings.append(
            f"Unknown preservation formats ignored: {', '.join(unknown_formats)}"
        )
    if duplicate_backends:
        warnings.append(
            f"Duplicate preservation backends ignored: {', '.join(duplicate_backends)}"
        )
    if duplicate_formats:
        warnings.append(
            f"Duplicate preservation formats ignored: {', '.join(duplicate_formats)}"
        )
    if unknown_capture_methods:
        warnings.append(
            "Unknown capture methods ignored: "
            f"{', '.join(unknown_capture_methods)}"
        )
    if duplicate_capture_methods:
        warnings.append(
            "Duplicate capture methods ignored: "
            f"{', '.join(duplicate_capture_methods)}"
        )
    if not selected_backends:
        warnings.append("No preservation backend selected.")
    if not selected_formats:
        warnings.append("No preservation formats selected.")

    status = (
        PLAN_STATUS_READY
        if selected_backends and selected_formats
        else PLAN_STATUS_NEEDS_SELECTION
    )

    return PreservationBackendPlan(
        source_url=source_url.strip(),
        selected_backend_ids=selected_backends,
        selected_format_ids=selected_formats,
        unknown_backend_ids=unknown_backends,
        unknown_format_ids=unknown_formats,
        duplicate_backend_ids=duplicate_backends,
        duplicate_format_ids=duplicate_formats,
        selected_capture_method_ids=selected_capture_methods,
        unknown_capture_method_ids=unknown_capture_methods,
        duplicate_capture_method_ids=duplicate_capture_methods,
        media_preservation_choice=normalized_media_choice,
        status=status,
        warnings=tuple(warnings),
        notes=notes.strip(),
        evidence_bundle=evidence_bundle,
    )


def preservation_backend_plan_to_dict(
    plan: PreservationBackendPlan,
) -> dict[str, Any]:
    # Evidence bundle integration: metadata-only preservation plan field.
    from preservation_evidence_bundle import preservation_evidence_bundle_to_dict

    selected_capture_methods = [
        method
        for method_id in plan.selected_capture_method_ids
        if (method := capture_method_by_id(method_id)) is not None
    ]
    return {
        "available_backends": [
            {
                "backend_id": option.backend_id,
                "display_name": option.display_name,
                "execution_supported": option.execution_supported,
                "local_only": option.local_only,
                "notes": option.notes,
                "recommended_next_step": option.recommended_next_step,
                "status": option.status,
            }
            for option in BACKEND_OPTIONS
        ],
        "available_formats": [
            {
                "display_name": option.display_name,
                "file_extensions": list(option.file_extensions),
                "format_id": option.format_id,
                "notes": option.notes,
            }
            for option in FORMAT_OPTIONS
        ],
        "available_media_preservation_choices": [
            {
                "choice_id": option.choice_id,
                "display_name": option.display_name,
                "explicit_opt_in": option.explicit_opt_in,
                "notes": option.notes,
            }
            for option in MEDIA_PRESERVATION_CHOICE_OPTIONS
        ],
        "duplicate_backend_ids": list(plan.duplicate_backend_ids),
        "duplicate_capture_method_ids": list(
            plan.duplicate_capture_method_ids
        ),
        "duplicate_format_ids": list(plan.duplicate_format_ids),
        "evidence_bundle": (
            preservation_evidence_bundle_to_dict(plan.evidence_bundle)
            if plan.evidence_bundle is not None
            else None
        ),
        "capture_methods": [
            capture_method_metadata_to_dict(method)
            for method in selected_capture_methods
        ],
        "notes": plan.notes,
        "media_preservation_choice": plan.media_preservation_choice,
        "scope": plan.scope,
        "selected_backend_ids": list(plan.selected_backend_ids),
        "selected_capture_method_ids": list(plan.selected_capture_method_ids),
        "selected_format_ids": list(plan.selected_format_ids),
        "source_url": plan.source_url,
        "status": plan.status,
        "unknown_backend_ids": list(plan.unknown_backend_ids),
        "unknown_capture_method_ids": list(plan.unknown_capture_method_ids),
        "unknown_format_ids": list(plan.unknown_format_ids),
        "warnings": list(plan.warnings),
    }


def build_preservation_backend_plan_markdown(plan: PreservationBackendPlan) -> str:
    lines = [
        "# Preservation Backend Plan",
        "",
        "Local planning report only. This report does not fetch URLs, run ArchiveBox, submit/check archives, scrape pages, capture screenshots, download media, store credentials, call providers/network services, or wire into the GUI.",
        "",
        f"- Status: {plan.status}",
        f"- Source URL: {plan.source_url or '(not supplied)'}",
        f"- Selected backends: {', '.join(plan.selected_backend_ids) or 'none'}",
        f"- Selected formats: {', '.join(plan.selected_format_ids) or 'none'}",
        f"- Selected capture methods: {', '.join(plan.selected_capture_method_ids) or 'none specified'}",
        f"- Media preservation choice: {plan.media_preservation_choice}",
        "- Media preservation choices are `none`, `select`, or `all`; this is opt-in planning metadata only, this report does not discover or download media, and `all` must be explicit.",
    ]
    if plan.notes:
        lines.append(f"- Notes: {plan.notes}")
    if plan.warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {warning}" for warning in plan.warnings)

    lines.extend(["", "## Evidence Bundle", ""])
    if plan.evidence_bundle is None:
        lines.append("No evidence bundle is specified. No evidence files are opened, scanned, hashed, created, uploaded, captured, downloaded, scraped, or fetched.")
        lines.append("")
    else:
        from preservation_evidence_bundle import build_preservation_evidence_bundle_markdown

        lines.append(build_preservation_evidence_bundle_markdown(plan.evidence_bundle))
        lines.append("")

    lines.extend(["", "## Selected Capture Methods", ""])
    if not plan.selected_capture_method_ids:
        lines.append("No capture method is selected or specified. No capture is executed.")
        lines.append("")
    for method_id in plan.selected_capture_method_ids:
        method = capture_method_by_id(method_id)
        if method is None:
            continue
        lines.extend(
            [
                f"### {method.display_name}",
                "",
                f"- Method ID: {method.method_id}",
                f"- Limitations: {method.limitations}",
                "- Execution: metadata only; this plan does not run screenshots, DOM capture, scrolling, browsers, scraping, or downloads.",
                "",
            ]
        )

    lines.extend(["", "## Available Backends", ""])
    for option in BACKEND_OPTIONS:
        lines.extend(
            [
                f"### {option.display_name}",
                "",
                f"- Backend ID: {option.backend_id}",
                f"- Status: {option.status}",
                f"- Execution supported: {'yes' if option.execution_supported else 'no'}",
                f"- Local only: {'yes' if option.local_only else 'no'}",
                f"- Notes: {option.notes}",
                f"- Recommended next step: {option.recommended_next_step}",
                "",
            ]
        )

    lines.extend(["## Available Formats", ""])
    for option in FORMAT_OPTIONS:
        lines.extend(
            [
                f"### {option.display_name}",
                "",
                f"- Format ID: {option.format_id}",
                f"- File extensions: {', '.join(option.file_extensions)}",
                f"- Notes: {option.notes}",
                "",
            ]
        )

    return "\n".join(lines).rstrip()


def build_preservation_backend_plan_text(plan: PreservationBackendPlan) -> str:
    lines = [
        "Preservation backend plan",
        "Scope: local planning only; no fetch/capture/network/archive/browser/scraping/credential/ArchiveBox execution/media download/GUI behavior is performed.",
        f"status: {plan.status}",
        f"source_url: {plan.source_url or '(not supplied)'}",
        f"selected_backend_ids: {', '.join(plan.selected_backend_ids) or 'none'}",
        f"selected_format_ids: {', '.join(plan.selected_format_ids) or 'none'}",
        f"selected_capture_method_ids: {', '.join(plan.selected_capture_method_ids) or 'none specified'}",
        f"media_preservation_choice: {plan.media_preservation_choice}",
        "media_preservation_note: choices are none, select, or all; opt-in planning metadata only; no media discovery or download; all must be explicit",
    ]
    if plan.notes:
        lines.append(f"notes: {plan.notes}")
    if plan.warnings:
        lines.append(f"warnings: {'; '.join(plan.warnings)}")

    lines.append("")
    lines.append("evidence_bundle:")
    if plan.evidence_bundle is None:
        lines.append("- none specified; no evidence files are opened, scanned, hashed, created, uploaded, captured, downloaded, scraped, or fetched")
    else:
        from preservation_evidence_bundle import build_preservation_evidence_bundle_text

        lines.extend(build_preservation_evidence_bundle_text(plan.evidence_bundle).splitlines())

    lines.append("")
    lines.append("selected_capture_methods:")
    if not plan.selected_capture_method_ids:
        lines.append("- none specified; no capture is executed")
    for method_id in plan.selected_capture_method_ids:
        method = capture_method_by_id(method_id)
        if method is not None:
            lines.append(
                f"- {method.method_id}: {method.display_name}; limitations={method.limitations}; execution=metadata only"
            )

    lines.append("")
    lines.append("available_backends:")
    for option in BACKEND_OPTIONS:
        lines.append(
            f"- {option.backend_id}: {option.display_name}; status={option.status}; execution_supported={option.execution_supported}"
        )

    lines.append("")
    lines.append("available_formats:")
    for option in FORMAT_OPTIONS:
        lines.append(
            f"- {option.format_id}: {option.display_name}; extensions={', '.join(option.file_extensions)}"
        )

    return "\n".join(lines)


def render_preservation_backend_plan(
    plan: PreservationBackendPlan,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_preservation_backend_plan_markdown(plan)
    if output_format == "text":
        return build_preservation_backend_plan_text(plan)
    if output_format == "json":
        return json.dumps(
            preservation_backend_plan_to_dict(plan),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
