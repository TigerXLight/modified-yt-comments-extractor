from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from total_export_local_media import (
    LOCAL_MEDIA_STATUS_HASH_MISMATCH,
    LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_STATUS_NEEDS_REVIEW,
    LocalMediaRecord,
)
from total_export_manual_archive import (
    ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED,
    ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
    ARCHIVE_STATUS_NOT_CHECKED,
    ManualArchiveRecord,
    normalize_source_url as normalize_archive_source_url,
)


ARCHIVE_FOLLOW_UP_STATUSES = (
    ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED,
    ARCHIVE_STATUS_NOT_CHECKED,
    ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
)

LOCAL_MEDIA_FOLLOW_UP_STATUSES = (
    LOCAL_MEDIA_STATUS_HASH_MISMATCH,
    LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_STATUS_NEEDS_REVIEW,
)


@dataclass(frozen=True)
class PreservationPlanItem:
    source_url: str
    normalized_url: str = ""
    package_id: str = ""
    archive_record_count: int = 0
    local_media_record_count: int = 0
    archive_statuses: tuple[str, ...] = ()
    local_media_statuses: tuple[str, ...] = ()
    needs_archive_follow_up: bool = False
    needs_local_media_follow_up: bool = False
    warnings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PreservationPlanResult:
    source_count: int = 0
    sources_with_archive_count: int = 0
    sources_missing_archive_count: int = 0
    sources_with_local_media_count: int = 0
    sources_missing_local_media_count: int = 0
    sources_needing_follow_up_count: int = 0
    items: tuple[PreservationPlanItem, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "errors": list(self.errors),
            "items": [preservation_plan_item_to_dict(item) for item in self.items],
            "source_count": self.source_count,
            "sources_missing_archive_count": self.sources_missing_archive_count,
            "sources_missing_local_media_count": self.sources_missing_local_media_count,
            "sources_needing_follow_up_count": self.sources_needing_follow_up_count,
            "sources_with_archive_count": self.sources_with_archive_count,
            "sources_with_local_media_count": self.sources_with_local_media_count,
            "warnings": list(self.warnings),
        }


def _clean_string(value: object) -> str:
    return str(value or "").strip()


def normalize_preservation_source_url(value: str) -> str:
    cleaned = _clean_string(value)
    if not cleaned:
        return ""
    return normalize_archive_source_url(cleaned)


def _source_key(value: str) -> str:
    return normalize_preservation_source_url(value) or _clean_string(value)


def _archive_record_key(record: ManualArchiveRecord) -> str:
    return _source_key(record.normalized_url or record.source_url)


def _local_media_record_key(record: LocalMediaRecord) -> str:
    return _source_key(record.normalized_url or record.source_url)


def _index_archive_records(
    records: Sequence[ManualArchiveRecord],
) -> dict[str, tuple[ManualArchiveRecord, ...]]:
    indexed: dict[str, list[ManualArchiveRecord]] = {}
    for record in records:
        key = _archive_record_key(record)
        if key:
            indexed.setdefault(key, []).append(record)
    return {key: tuple(value) for key, value in indexed.items()}


def _index_local_media_records(
    records: Sequence[LocalMediaRecord],
) -> dict[str, tuple[LocalMediaRecord, ...]]:
    indexed: dict[str, list[LocalMediaRecord]] = {}
    for record in records:
        key = _local_media_record_key(record)
        if key:
            indexed.setdefault(key, []).append(record)
    return {key: tuple(value) for key, value in indexed.items()}


def _unique_preserving_order(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = _clean_string(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique.append(cleaned)
    return tuple(unique)


def _first_package_id(records: Sequence[LocalMediaRecord]) -> str:
    for record in records:
        if _clean_string(record.package_id):
            return _clean_string(record.package_id)
    return ""


def build_preservation_plan_item(
    *,
    source_url: str,
    manual_archive_records: Sequence[ManualArchiveRecord] = (),
    local_media_records: Sequence[LocalMediaRecord] = (),
) -> PreservationPlanItem:
    cleaned_source = _clean_string(source_url)
    normalized_url = normalize_preservation_source_url(cleaned_source)
    archive_statuses = _unique_preserving_order(
        tuple(record.archive_status for record in manual_archive_records)
    )
    local_media_statuses = _unique_preserving_order(
        tuple(record.status for record in local_media_records)
    )

    needs_archive_follow_up = (
        not manual_archive_records
        or any(status in ARCHIVE_FOLLOW_UP_STATUSES for status in archive_statuses)
    )
    needs_local_media_follow_up = (
        not local_media_records
        or any(status in LOCAL_MEDIA_FOLLOW_UP_STATUSES for status in local_media_statuses)
    )

    warnings: list[str] = []
    actions: list[str] = []

    if not cleaned_source:
        warnings.append("Source URL is empty; preservation status cannot be matched.")
    if not manual_archive_records:
        warnings.append("No manually supplied archive metadata record is present.")
        actions.append("Add a manually supplied archive URL if one exists.")
    elif ARCHIVE_STATUS_NOT_CHECKED in archive_statuses:
        actions.append("Review not_checked archive status; no archive service was checked by this helper.")
    if ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED in archive_statuses:
        actions.append("Review manual_follow_up_needed archive status.")
    if ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND in archive_statuses:
        actions.append("Review manually_checked_not_found archive status; absence is not proof.")

    if not local_media_records:
        warnings.append("No registered local media metadata record is present.")
        actions.append("Register a local media file already saved on disk if available.")
    if LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE in local_media_statuses:
        actions.append("Re-check local media path/hash.")
    if LOCAL_MEDIA_STATUS_HASH_MISMATCH in local_media_statuses:
        actions.append("Review local media hash_mismatch status.")
    if LOCAL_MEDIA_STATUS_NEEDS_REVIEW in local_media_statuses:
        actions.append("Review needs_review local media status.")

    if needs_archive_follow_up or needs_local_media_follow_up:
        actions.append("No automatic archive checks or downloads are performed.")

    return PreservationPlanItem(
        source_url=cleaned_source,
        normalized_url=normalized_url,
        package_id=_first_package_id(local_media_records),
        archive_record_count=len(manual_archive_records),
        local_media_record_count=len(local_media_records),
        archive_statuses=archive_statuses,
        local_media_statuses=local_media_statuses,
        needs_archive_follow_up=needs_archive_follow_up,
        needs_local_media_follow_up=needs_local_media_follow_up,
        warnings=_unique_preserving_order(tuple(warnings)),
        recommended_actions=_unique_preserving_order(tuple(actions)),
    )


def _source_urls_from_records(
    manual_archive_records: Sequence[ManualArchiveRecord],
    local_media_records: Sequence[LocalMediaRecord],
) -> tuple[str, ...]:
    values: list[str] = []
    for record in manual_archive_records:
        values.append(record.normalized_url or record.source_url)
    for record in local_media_records:
        values.append(record.normalized_url or record.source_url)
    return _unique_preserving_order(tuple(values))


def build_preservation_plan(
    *,
    source_urls: Sequence[str] = (),
    manual_archive_records: Sequence[ManualArchiveRecord] = (),
    local_media_records: Sequence[LocalMediaRecord] = (),
) -> PreservationPlanResult:
    archive_index = _index_archive_records(manual_archive_records)
    local_media_index = _index_local_media_records(local_media_records)
    selected_sources = _unique_preserving_order(
        tuple(source_urls) or _source_urls_from_records(manual_archive_records, local_media_records)
    )

    items: list[PreservationPlanItem] = []
    errors: list[str] = []
    for source_url in selected_sources:
        key = _source_key(source_url)
        if not key:
            errors.append("Empty source URL skipped.")
            continue
        items.append(
            build_preservation_plan_item(
                source_url=source_url,
                manual_archive_records=archive_index.get(key, ()),
                local_media_records=local_media_index.get(key, ()),
            )
        )

    warnings = (
        "Local preservation plan uses user-supplied metadata only; missing records are unknown, not proof.",
        "No archive checks, downloads, fetching, scraping, screenshots, transcription, or provider calls are performed.",
    )

    return PreservationPlanResult(
        source_count=len(items),
        sources_with_archive_count=sum(1 for item in items if item.archive_record_count > 0),
        sources_missing_archive_count=sum(1 for item in items if item.archive_record_count == 0),
        sources_with_local_media_count=sum(1 for item in items if item.local_media_record_count > 0),
        sources_missing_local_media_count=sum(1 for item in items if item.local_media_record_count == 0),
        sources_needing_follow_up_count=sum(
            1
            for item in items
            if item.needs_archive_follow_up or item.needs_local_media_follow_up
        ),
        items=tuple(items),
        warnings=warnings,
        errors=tuple(errors),
    )


def preservation_plan_item_to_dict(item: PreservationPlanItem) -> dict[str, object]:
    return item.to_dict()


def preservation_plan_to_dict(plan: PreservationPlanResult) -> dict[str, object]:
    return plan.to_dict()


def _format_tuple(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def build_preservation_plan_text(plan: PreservationPlanResult) -> str:
    lines = [
        "Local preservation plan report",
        "Scope: local/user-supplied metadata only; no archive checks, downloads, fetching, scraping, screenshots, transcription, or provider calls are performed.",
        f"Source count: {plan.source_count}",
        f"Sources with archive metadata: {plan.sources_with_archive_count}",
        f"Sources missing archive metadata: {plan.sources_missing_archive_count}",
        f"Sources with local media metadata: {plan.sources_with_local_media_count}",
        f"Sources missing local media metadata: {plan.sources_missing_local_media_count}",
        f"Sources needing follow-up: {plan.sources_needing_follow_up_count}",
        "Items:",
    ]
    if not plan.items:
        lines.append("- (none)")
    for item in plan.items:
        lines.append(f"- Source: {item.normalized_url or item.source_url}")
        if item.package_id:
            lines.append(f"  Package ID: {item.package_id}")
        lines.append(
            "  Archive records: "
            f"{item.archive_record_count} [statuses={_format_tuple(item.archive_statuses)}; "
            f"follow_up={_format_bool(item.needs_archive_follow_up)}]"
        )
        lines.append(
            "  Local media records: "
            f"{item.local_media_record_count} [statuses={_format_tuple(item.local_media_statuses)}; "
            f"follow_up={_format_bool(item.needs_local_media_follow_up)}]"
        )
        if item.warnings:
            lines.append(f"  Warnings: {_format_tuple(item.warnings)}")
        if item.recommended_actions:
            lines.append("  Recommended actions:")
            for action in item.recommended_actions:
                lines.append(f"  - {action}")
    if plan.warnings:
        lines.append("Plan warnings:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    if plan.errors:
        lines.append("Plan errors:")
        for error in plan.errors:
            lines.append(f"- {error}")
    return "\n".join(lines)


def build_preservation_plan_markdown(plan: PreservationPlanResult) -> str:
    lines = [
        "# Local Preservation Plan Report",
        "",
        "Local/user-supplied metadata only. This report does not check archive services, submit URLs, download media, fetch sources, scrape pages, capture screenshots, transcribe, call providers, or wire into the GUI.",
        "",
        "## Counts",
        "",
        f"- Source count: {plan.source_count}",
        f"- Sources with archive metadata: {plan.sources_with_archive_count}",
        f"- Sources missing archive metadata: {plan.sources_missing_archive_count}",
        f"- Sources with local media metadata: {plan.sources_with_local_media_count}",
        f"- Sources missing local media metadata: {plan.sources_missing_local_media_count}",
        f"- Sources needing follow-up: {plan.sources_needing_follow_up_count}",
        "",
        "## Sources",
        "",
        "| Source URL | Archive records | Archive statuses | Archive follow-up | Local media records | Local media statuses | Local media follow-up | Recommended actions |",
        "| --- | ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in plan.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.normalized_url or item.source_url or "(none)",
                    str(item.archive_record_count),
                    _format_tuple(item.archive_statuses),
                    _format_bool(item.needs_archive_follow_up),
                    str(item.local_media_record_count),
                    _format_tuple(item.local_media_statuses),
                    _format_bool(item.needs_local_media_follow_up),
                    "<br>".join(item.recommended_actions) if item.recommended_actions else "(none)",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Missing metadata means unknown, not proof that no archive or local media exists.",
            "- Archive statuses are user-entered local notes.",
            "- Local media statuses are local filesystem/user-entered notes.",
            "- No automatic archive checks, downloads, source fetching, scraping, screenshots, transcription, provider calls, or GUI behavior are performed.",
        ]
    )
    return "\n".join(lines)
