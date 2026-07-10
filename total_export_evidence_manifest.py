from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from total_export_bundle_index import (
    BUNDLE_INDEX_STATUS_COMPLETE,
    BundleIndexResult,
)
from total_export_bundle_index_reconcile import BundleIndexReconciliationResult
from total_export_local_media import LocalMediaRecord
from total_export_local_media_verify import (
    LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
    LocalMediaVerificationResult,
)
from total_export_manual_archive import ManualArchiveRecord
from total_export_preservation_plan import (
    PreservationPlanItem,
    PreservationPlanResult,
    build_preservation_plan,
    normalize_preservation_source_url,
)


@dataclass(frozen=True)
class EvidenceManifestEntry:
    source_url: str = ""
    normalized_url: str = ""
    package_id: str = ""
    title: str = ""
    archive_record_count: int = 0
    archive_statuses: tuple[str, ...] = ()
    local_media_record_count: int = 0
    local_media_statuses: tuple[str, ...] = ()
    local_media_verification_statuses: tuple[str, ...] = ()
    bundle_statuses: tuple[str, ...] = ()
    local_reference_paths: tuple[str, ...] = ()
    needs_follow_up: bool = False
    warnings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceManifestResult:
    entry_count: int = 0
    sources_needing_follow_up_count: int = 0
    archive_record_count: int = 0
    local_media_record_count: int = 0
    local_media_verification_count: int = 0
    bundle_item_count: int = 0
    entries: tuple[EvidenceManifestEntry, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass
class _EntryBuilder:
    source_url: str = ""
    normalized_url: str = ""
    package_id: str = ""
    title: str = ""
    archive_record_count: int = 0
    archive_statuses: list[str] = field(default_factory=list)
    local_media_record_count: int = 0
    local_media_statuses: list[str] = field(default_factory=list)
    local_media_verification_statuses: list[str] = field(default_factory=list)
    bundle_statuses: list[str] = field(default_factory=list)
    local_reference_paths: list[str] = field(default_factory=list)
    needs_follow_up: bool = False
    warnings: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _source_key(value: str) -> str:
    cleaned = _clean(value)
    return normalize_preservation_source_url(cleaned) or cleaned


def _append_unique(values: list[str], *additions: str) -> None:
    for addition in additions:
        cleaned = _clean(addition)
        if cleaned and cleaned not in values:
            values.append(cleaned)


def _record_source(record) -> str:
    return _clean(record.normalized_url or record.source_url)


def _entry_from_builder(builder: _EntryBuilder) -> EvidenceManifestEntry:
    return EvidenceManifestEntry(
        source_url=builder.source_url,
        normalized_url=builder.normalized_url,
        package_id=builder.package_id,
        title=builder.title,
        archive_record_count=builder.archive_record_count,
        archive_statuses=tuple(builder.archive_statuses),
        local_media_record_count=builder.local_media_record_count,
        local_media_statuses=tuple(builder.local_media_statuses),
        local_media_verification_statuses=tuple(builder.local_media_verification_statuses),
        bundle_statuses=tuple(builder.bundle_statuses),
        local_reference_paths=tuple(builder.local_reference_paths),
        needs_follow_up=builder.needs_follow_up,
        warnings=tuple(builder.warnings),
        recommended_actions=tuple(builder.recommended_actions),
    )


def _apply_plan_item(builder: _EntryBuilder, item: PreservationPlanItem) -> None:
    builder.package_id = builder.package_id or item.package_id
    builder.needs_follow_up = builder.needs_follow_up or (
        item.needs_archive_follow_up or item.needs_local_media_follow_up
    )
    _append_unique(builder.warnings, *item.warnings)
    _append_unique(builder.recommended_actions, *item.recommended_actions)


def build_evidence_manifest(
    *,
    source_urls: Sequence[str] = (),
    manual_archive_records: Sequence[ManualArchiveRecord] = (),
    local_media_records: Sequence[LocalMediaRecord] = (),
    local_media_verification_result: LocalMediaVerificationResult | None = None,
    preservation_plan: PreservationPlanResult | None = None,
    bundle_index_result: BundleIndexResult | None = None,
    bundle_reconciliation_result: BundleIndexReconciliationResult | None = None,
) -> EvidenceManifestResult:
    builders: dict[str, _EntryBuilder] = {}
    order: list[str] = []
    package_to_source: dict[str, str] = {}

    def ensure_source(value: str) -> tuple[str, _EntryBuilder] | tuple[str, None]:
        source = _clean(value)
        key = _source_key(source)
        if not key:
            return "", None
        if key not in builders:
            builders[key] = _EntryBuilder(
                source_url=source,
                normalized_url=normalize_preservation_source_url(source),
            )
            order.append(key)
        elif not builders[key].source_url:
            builders[key].source_url = source
        return key, builders[key]

    for source_url in source_urls:
        ensure_source(source_url)
    for record in manual_archive_records:
        ensure_source(_record_source(record))
    for record in local_media_records:
        key, builder = ensure_source(_record_source(record))
        package_id = _clean(record.package_id)
        if key and package_id:
            package_to_source.setdefault(package_id, key)
            if builder is not None:
                builder.package_id = builder.package_id or package_id
    if preservation_plan is not None:
        for item in preservation_plan.items:
            key, builder = ensure_source(item.normalized_url or item.source_url)
            package_id = _clean(item.package_id)
            if key and package_id:
                package_to_source.setdefault(package_id, key)
                if builder is not None:
                    builder.package_id = builder.package_id or package_id
    if local_media_verification_result is not None:
        for item in local_media_verification_result.items:
            ensure_source(item.normalized_url or item.source_url)
    if bundle_reconciliation_result is not None:
        for item in (*bundle_reconciliation_result.items, *bundle_reconciliation_result.unexpected_items):
            ensure_source(item.source_url)

    derived_plan = build_preservation_plan(
        source_urls=tuple(builders[key].source_url for key in order),
        manual_archive_records=manual_archive_records,
        local_media_records=local_media_records,
    )
    plan_items = {_source_key(item.normalized_url or item.source_url): item for item in derived_plan.items}
    if preservation_plan is not None:
        plan_items.update(
            {
                _source_key(item.normalized_url or item.source_url): item
                for item in preservation_plan.items
            }
        )

    for record in manual_archive_records:
        key = _source_key(_record_source(record))
        builder = builders.get(key)
        if builder is None:
            continue
        builder.archive_record_count += 1
        _append_unique(builder.archive_statuses, record.archive_status)

    for record in local_media_records:
        key = _source_key(_record_source(record))
        builder = builders.get(key)
        if builder is None:
            continue
        builder.local_media_record_count += 1
        builder.package_id = builder.package_id or _clean(record.package_id)
        _append_unique(builder.local_media_statuses, record.status)
        _append_unique(builder.local_reference_paths, record.local_media_path)

    for key in order:
        plan_item = plan_items.get(key)
        if plan_item is not None:
            _apply_plan_item(builders[key], plan_item)

    standalone_count = 0

    def standalone_builder(prefix: str) -> _EntryBuilder:
        nonlocal standalone_count
        standalone_count += 1
        key = f"__{prefix}_{standalone_count}"
        builders[key] = _EntryBuilder()
        order.append(key)
        return builders[key]

    if local_media_verification_result is not None:
        for item in local_media_verification_result.items:
            key = _source_key(item.normalized_url or item.source_url)
            if not key and item.package_id:
                key = package_to_source.get(_clean(item.package_id), "")
            builder = builders.get(key) if key else None
            if builder is None:
                builder = standalone_builder("media_verification")
                builder.package_id = _clean(item.package_id)
                builder.title = _clean(item.local_media_path) or "Unassociated local media verification"
            _append_unique(builder.local_media_verification_statuses, item.status)
            _append_unique(builder.local_reference_paths, item.local_media_path)
            _append_unique(builder.warnings, *item.warnings)
            _append_unique(builder.recommended_actions, *item.recommended_actions)
            if item.status != LOCAL_MEDIA_VERIFY_STATUS_VERIFIED:
                builder.needs_follow_up = True

    if bundle_index_result is not None:
        for item in bundle_index_result.items:
            builder = standalone_builder("bundle_index")
            builder.title = item.zip_filename
            _append_unique(builder.bundle_statuses, item.status)
            _append_unique(
                builder.local_reference_paths,
                item.zip_path,
                item.sha256_sidecar_path,
                item.inspection_sidecar_path,
                item.review_folder_path,
            )
            _append_unique(builder.warnings, *item.warnings)
            _append_unique(builder.recommended_actions, *item.recommended_actions)
            builder.needs_follow_up = item.status != BUNDLE_INDEX_STATUS_COMPLETE

    reconciliation_items = ()
    if bundle_reconciliation_result is not None:
        reconciliation_items = (
            *bundle_reconciliation_result.items,
            *bundle_reconciliation_result.unexpected_items,
        )
        for item in reconciliation_items:
            key = _source_key(item.source_url)
            if not key and item.package_id:
                key = package_to_source.get(_clean(item.package_id), "")
            builder = builders.get(key) if key else None
            if builder is None:
                builder = standalone_builder("bundle_reconciliation")
                builder.package_id = _clean(item.package_id)
                builder.title = item.zip_filename or "Unassociated bundle reconciliation item"
            builder.package_id = builder.package_id or _clean(item.package_id)
            _append_unique(builder.bundle_statuses, item.status)
            _append_unique(builder.local_reference_paths, item.expected_zip_path, item.matched_zip_path)
            _append_unique(builder.warnings, *item.warnings)
            _append_unique(builder.recommended_actions, *item.recommended_actions)
            builder.needs_follow_up = builder.needs_follow_up or item.needs_follow_up

    entries = tuple(_entry_from_builder(builders[key]) for key in order)
    result_warnings: list[str] = []
    result_errors: list[str] = []
    for input_result in (
        local_media_verification_result,
        preservation_plan,
        bundle_index_result,
        bundle_reconciliation_result,
    ):
        if input_result is not None:
            _append_unique(result_warnings, *input_result.warnings)
            _append_unique(result_errors, *input_result.errors)
    if bundle_index_result is not None and bundle_index_result.items:
        _append_unique(
            result_warnings,
            "Bundle index items do not carry source/package identity and are represented as standalone local references.",
        )

    return EvidenceManifestResult(
        entry_count=len(entries),
        sources_needing_follow_up_count=sum(1 for entry in entries if entry.needs_follow_up),
        archive_record_count=len(manual_archive_records),
        local_media_record_count=len(local_media_records),
        local_media_verification_count=(
            len(local_media_verification_result.items)
            if local_media_verification_result is not None
            else 0
        ),
        bundle_item_count=(
            (len(bundle_index_result.items) if bundle_index_result is not None else 0)
            + len(reconciliation_items)
        ),
        entries=entries,
        warnings=tuple(result_warnings),
        errors=tuple(result_errors),
    )


def evidence_manifest_entry_to_dict(entry: EvidenceManifestEntry) -> dict[str, object]:
    return {
        "archive_record_count": entry.archive_record_count,
        "archive_statuses": list(entry.archive_statuses),
        "bundle_statuses": list(entry.bundle_statuses),
        "local_media_record_count": entry.local_media_record_count,
        "local_media_statuses": list(entry.local_media_statuses),
        "local_media_verification_statuses": list(entry.local_media_verification_statuses),
        "local_reference_paths": list(entry.local_reference_paths),
        "needs_follow_up": entry.needs_follow_up,
        "normalized_url": entry.normalized_url,
        "package_id": entry.package_id,
        "recommended_actions": list(entry.recommended_actions),
        "source_url": entry.source_url,
        "title": entry.title,
        "warnings": list(entry.warnings),
    }


def evidence_manifest_to_dict(result: EvidenceManifestResult) -> dict[str, object]:
    return {
        "archive_record_count": result.archive_record_count,
        "bundle_item_count": result.bundle_item_count,
        "entries": [evidence_manifest_entry_to_dict(entry) for entry in result.entries],
        "entry_count": result.entry_count,
        "errors": list(result.errors),
        "local_media_record_count": result.local_media_record_count,
        "local_media_verification_count": result.local_media_verification_count,
        "sources_needing_follow_up_count": result.sources_needing_follow_up_count,
        "warnings": list(result.warnings),
    }


def _display(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def build_evidence_manifest_text(result: EvidenceManifestResult) -> str:
    lines = [
        "Manual local evidence package manifest",
        "Scope: local metadata references only; no file copying, package building, ZIP creation/extraction, downloads, fetching, network/API/archive checks, scraping, screenshots, transcription, provider calls, or GUI behavior are performed.",
        f"Entry count: {result.entry_count}",
        f"Entries needing follow-up: {result.sources_needing_follow_up_count}",
        f"Archive record count: {result.archive_record_count}",
        f"Local media record count: {result.local_media_record_count}",
        f"Local media verification count: {result.local_media_verification_count}",
        f"Bundle item count: {result.bundle_item_count}",
        "Entries:",
    ]
    if not result.entries:
        lines.append("- (none)")
    for entry in result.entries:
        label = entry.normalized_url or entry.source_url or entry.package_id or entry.title or "(unassociated)"
        lines.append(
            f"- {label} [follow_up={_yes_no(entry.needs_follow_up)}; "
            f"archive_records={entry.archive_record_count}; media_records={entry.local_media_record_count}]"
        )
        lines.append(f"  Archive statuses: {_display(entry.archive_statuses)}")
        lines.append(f"  Local media statuses: {_display(entry.local_media_statuses)}")
        lines.append(
            f"  Verification statuses: {_display(entry.local_media_verification_statuses)}"
        )
        lines.append(f"  Bundle statuses: {_display(entry.bundle_statuses)}")
        lines.append(f"  Local references: {_display(entry.local_reference_paths)}")
        if entry.warnings:
            lines.append(f"  Warnings: {_display(entry.warnings)}")
        if entry.recommended_actions:
            lines.append(f"  Recommended actions: {_display(entry.recommended_actions)}")
    lines.append(f"Warnings: {_display(result.warnings)}")
    lines.append(f"Errors: {_display(result.errors)}")
    lines.append(
        "Missing local metadata/files are follow-up signals only, not proof of remote deletion or unavailability."
    )
    return "\n".join(lines)


def _markdown_cell(values: Sequence[str]) -> str:
    return (_display(values)).replace("|", "\\|").replace("\n", " ")


def build_evidence_manifest_markdown(result: EvidenceManifestResult) -> str:
    lines = [
        "# Manual Local Evidence Package Manifest",
        "",
        "Local metadata references only. This report does not copy files, build packages, create or extract ZIPs, download/fetch content, call network/API/archive services, scrape, capture screenshots, transcribe, call providers, or wire into the GUI.",
        "",
        "## Counts",
        "",
        f"- Entry count: {result.entry_count}",
        f"- Entries needing follow-up: {result.sources_needing_follow_up_count}",
        f"- Archive record count: {result.archive_record_count}",
        f"- Local media record count: {result.local_media_record_count}",
        f"- Local media verification count: {result.local_media_verification_count}",
        f"- Bundle item count: {result.bundle_item_count}",
        "",
        "## Entries",
        "",
        "| Source/package | Archive records/statuses | Local media records/statuses | Verification statuses | Bundle statuses | Local reference paths | Follow-up | Recommended actions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in result.entries:
        label = entry.normalized_url or entry.source_url or entry.package_id or entry.title or "(unassociated)"
        lines.append(
            "| "
            + " | ".join(
                [
                    label.replace("|", "\\|"),
                    f"{entry.archive_record_count}; {_markdown_cell(entry.archive_statuses)}",
                    f"{entry.local_media_record_count}; {_markdown_cell(entry.local_media_statuses)}",
                    _markdown_cell(entry.local_media_verification_statuses),
                    _markdown_cell(entry.bundle_statuses),
                    _markdown_cell(entry.local_reference_paths),
                    _yes_no(entry.needs_follow_up),
                    _markdown_cell(entry.recommended_actions),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Local reference paths are metadata references; this helper does not open, copy, package, or extract them.",
            "- Missing local metadata/files are follow-up signals only, not proof of remote deletion or unavailability.",
            "- No downloads, fetching, network/API/archive checks, scraping, screenshots, transcription, provider calls, ZIP extraction, or GUI behavior are performed.",
        ]
    )
    return "\n".join(lines)
