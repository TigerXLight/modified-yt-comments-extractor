from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from total_export_bundle_index import (
    BUNDLE_INDEX_STATUS_COMPLETE,
    BundleIndexItem,
    BundleIndexResult,
)


BUNDLE_RECONCILE_STATUS_PRESENT = "present"
BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP = "missing_expected_zip"
BUNDLE_RECONCILE_STATUS_PRESENT_NEEDS_REVIEW = "present_needs_review"
BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP = "unexpected_zip"


@dataclass(frozen=True)
class ExpectedBundleEntry:
    expected_zip_path: str
    package_id: str = ""
    source_url: str = ""
    notes: str = ""


@dataclass(frozen=True)
class BundleIndexReconciliationItem:
    expected_zip_path: str
    matched_zip_path: str = ""
    zip_filename: str = ""
    package_id: str = ""
    source_url: str = ""
    expected_present: bool = False
    index_status: str = ""
    sidecar_ok: bool = False
    needs_follow_up: bool = True
    status: str = BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP
    notes: str = ""
    warnings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class BundleIndexReconciliationResult:
    index_root_path: str
    expected_count: int = 0
    present_expected_count: int = 0
    missing_expected_count: int = 0
    unexpected_zip_count: int = 0
    needs_follow_up_count: int = 0
    items: tuple[BundleIndexReconciliationItem, ...] = ()
    unexpected_items: tuple[BundleIndexReconciliationItem, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def build_expected_bundle_entries(
    values: Sequence[str | ExpectedBundleEntry],
) -> tuple[ExpectedBundleEntry, ...]:
    entries: list[ExpectedBundleEntry] = []
    for value in values:
        if isinstance(value, ExpectedBundleEntry):
            entries.append(value)
        else:
            entries.append(ExpectedBundleEntry(expected_zip_path=str(value)))
    return tuple(entries)


def _path_key(value: str) -> str:
    if not value:
        return ""
    try:
        resolved = Path(value).expanduser().resolve(strict=False)
        return os.path.normcase(os.path.normpath(str(resolved)))
    except (OSError, RuntimeError):
        return os.path.normcase(os.path.normpath(value))


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _expected_item(
    expected: ExpectedBundleEntry,
    index_item: BundleIndexItem | None,
) -> BundleIndexReconciliationItem:
    if index_item is None:
        return BundleIndexReconciliationItem(
            expected_zip_path=expected.expected_zip_path,
            zip_filename=Path(expected.expected_zip_path).name,
            package_id=expected.package_id,
            source_url=expected.source_url,
            notes=expected.notes,
            warnings=(
                f"Expected ZIP is not present in the local bundle index: {expected.expected_zip_path}",
            ),
            recommended_actions=(
                "Locate or create the expected local bundle ZIP, then rebuild the local bundle index.",
                "Treat the missing local path as a follow-up signal, not proof of deletion or invalidity.",
            ),
        )

    sidecar_ok = index_item.status == BUNDLE_INDEX_STATUS_COMPLETE
    status = (
        BUNDLE_RECONCILE_STATUS_PRESENT
        if sidecar_ok
        else BUNDLE_RECONCILE_STATUS_PRESENT_NEEDS_REVIEW
    )
    actions = list(index_item.recommended_actions)
    if not sidecar_ok:
        actions.append("Review the indexed ZIP and its local sidecars before treating the bundle as complete.")
    return BundleIndexReconciliationItem(
        expected_zip_path=expected.expected_zip_path,
        matched_zip_path=index_item.zip_path,
        zip_filename=index_item.zip_filename,
        package_id=expected.package_id,
        source_url=expected.source_url,
        expected_present=True,
        index_status=index_item.status,
        sidecar_ok=sidecar_ok,
        needs_follow_up=not sidecar_ok,
        status=status,
        notes=expected.notes,
        warnings=tuple(index_item.warnings),
        recommended_actions=_unique(actions),
    )


def _unexpected_item(index_item: BundleIndexItem) -> BundleIndexReconciliationItem:
    return BundleIndexReconciliationItem(
        expected_zip_path="",
        matched_zip_path=index_item.zip_path,
        zip_filename=index_item.zip_filename,
        expected_present=False,
        index_status=index_item.status,
        sidecar_ok=index_item.status == BUNDLE_INDEX_STATUS_COMPLETE,
        needs_follow_up=True,
        status=BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP,
        warnings=_unique(
            (
                f"Indexed ZIP is not in the expected bundle list: {index_item.zip_path}",
                *index_item.warnings,
            )
        ),
        recommended_actions=_unique(
            (
                "Confirm whether this ZIP should be added to the expected bundle list or reviewed separately.",
                *index_item.recommended_actions,
            )
        ),
    )


def reconcile_bundle_index(
    expected_entries: Sequence[str | ExpectedBundleEntry],
    bundle_index_result: BundleIndexResult,
) -> BundleIndexReconciliationResult:
    expected = build_expected_bundle_entries(expected_entries)
    indexed_by_path = {
        _path_key(item.zip_path): item
        for item in bundle_index_result.items
    }
    expected_keys = {_path_key(entry.expected_zip_path) for entry in expected}

    items = tuple(
        _expected_item(entry, indexed_by_path.get(_path_key(entry.expected_zip_path)))
        for entry in expected
    )
    unexpected_items = tuple(
        _unexpected_item(item)
        for item in sorted(
            bundle_index_result.items,
            key=lambda value: _path_key(value.zip_path),
        )
        if _path_key(item.zip_path) not in expected_keys
    )
    present_count = sum(1 for item in items if item.expected_present)
    follow_up_count = sum(1 for item in items if item.needs_follow_up) + len(unexpected_items)

    return BundleIndexReconciliationResult(
        index_root_path=bundle_index_result.root_path,
        expected_count=len(items),
        present_expected_count=present_count,
        missing_expected_count=len(items) - present_count,
        unexpected_zip_count=len(unexpected_items),
        needs_follow_up_count=follow_up_count,
        items=items,
        unexpected_items=unexpected_items,
        warnings=tuple(bundle_index_result.warnings),
        errors=tuple(bundle_index_result.errors),
    )


def bundle_index_reconciliation_item_to_dict(
    item: BundleIndexReconciliationItem,
) -> dict[str, object]:
    return {
        "expected_present": item.expected_present,
        "expected_zip_path": item.expected_zip_path,
        "index_status": item.index_status,
        "matched_zip_path": item.matched_zip_path,
        "needs_follow_up": item.needs_follow_up,
        "notes": item.notes,
        "package_id": item.package_id,
        "recommended_actions": list(item.recommended_actions),
        "sidecar_ok": item.sidecar_ok,
        "source_url": item.source_url,
        "status": item.status,
        "warnings": list(item.warnings),
        "zip_filename": item.zip_filename,
    }


def bundle_index_reconciliation_to_dict(
    result: BundleIndexReconciliationResult,
) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "expected_count": result.expected_count,
        "index_root_path": result.index_root_path,
        "items": [bundle_index_reconciliation_item_to_dict(item) for item in result.items],
        "missing_expected_count": result.missing_expected_count,
        "needs_follow_up_count": result.needs_follow_up_count,
        "present_expected_count": result.present_expected_count,
        "unexpected_items": [
            bundle_index_reconciliation_item_to_dict(item)
            for item in result.unexpected_items
        ],
        "unexpected_zip_count": result.unexpected_zip_count,
        "warnings": list(result.warnings),
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: Sequence[str]) -> None:
    lines.append(label)
    lines.extend(f"- {value}" for value in values) if values else lines.append("- (none)")


def _append_item(lines: list[str], item: BundleIndexReconciliationItem) -> None:
    display_path = item.expected_zip_path or item.matched_zip_path
    lines.append(
        f"- {display_path} [status={item.status}; index_status={item.index_status or '(none)'}; "
        f"sidecar_ok={_yes_no(item.sidecar_ok)}; follow_up={_yes_no(item.needs_follow_up)}]"
    )
    if item.warnings:
        lines.append("  Warnings:")
        lines.extend(f"  - {warning}" for warning in item.warnings)
    if item.recommended_actions:
        lines.append("  Recommended actions:")
        lines.extend(f"  - {action}" for action in item.recommended_actions)


def build_bundle_index_reconciliation_text(
    result: BundleIndexReconciliationResult,
) -> str:
    lines = [
        "Total Export bundle index reconciliation",
        "Scope: local expected paths and bundle-index metadata only; no ZIP extraction, network, archive checks, downloads, scraping, screenshots, transcription, provider calls, or GUI behavior are performed.",
        f"Index root path: {result.index_root_path}",
        f"Expected count: {result.expected_count}",
        f"Present expected count: {result.present_expected_count}",
        f"Missing expected count: {result.missing_expected_count}",
        f"Unexpected ZIP count: {result.unexpected_zip_count}",
        f"Needs follow-up count: {result.needs_follow_up_count}",
        "Expected items:",
    ]
    if result.items:
        for item in result.items:
            _append_item(lines, item)
    else:
        lines.append("- (none)")
    lines.append("Unexpected items:")
    if result.unexpected_items:
        for item in result.unexpected_items:
            _append_item(lines, item)
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    lines.append("Missing and unexpected local files are follow-up signals only, not proof of deletion, invalidity, or external availability.")
    return "\n".join(lines)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build_bundle_index_reconciliation_markdown(
    result: BundleIndexReconciliationResult,
) -> str:
    lines = [
        "# Total Export Bundle Index Reconciliation",
        "",
        "Local expected paths and bundle-index metadata only. No ZIP extraction, source fetching, downloads, scraping, screenshots, archive checks/submission, transcription, provider calls, or GUI behavior are performed.",
        "",
        "## Counts",
        "",
        f"- Index root path: `{result.index_root_path}`",
        f"- Expected count: {result.expected_count}",
        f"- Present expected count: {result.present_expected_count}",
        f"- Missing expected count: {result.missing_expected_count}",
        f"- Unexpected ZIP count: {result.unexpected_zip_count}",
        f"- Needs follow-up count: {result.needs_follow_up_count}",
        "",
        "## Reconciliation Items",
        "",
        "| ZIP path | Status | Index status | Sidecars OK | Follow-up | Warnings | Recommended actions |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in (*result.items, *result.unexpected_items):
        path = item.expected_zip_path or item.matched_zip_path
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(path),
                    item.status,
                    item.index_status or "(none)",
                    _yes_no(item.sidecar_ok),
                    _yes_no(item.needs_follow_up),
                    _markdown_cell("; ".join(item.warnings) or "(none)"),
                    _markdown_cell("; ".join(item.recommended_actions) or "(none)"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Missing expected files and unexpected local files are manual follow-up signals only.",
            "- Sidecar warnings and actions come from the existing local bundle index helper.",
            "- No ZIP extraction is performed.",
            "- No downloads, source fetching, scraping, screenshots, archive checks/submission, transcription, provider calls, or GUI behavior are performed.",
        ]
    )
    return "\n".join(lines)
