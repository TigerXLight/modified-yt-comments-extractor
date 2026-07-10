from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from total_export_zip_sidecar import (
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


BUNDLE_INDEX_STATUS_COMPLETE = "complete"
BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR = "missing_sha256_sidecar"
BUNDLE_INDEX_STATUS_SHA256_MISMATCH = "sha256_mismatch"
BUNDLE_INDEX_STATUS_MISSING_INSPECTION_SIDECAR = "missing_inspection_sidecar"
BUNDLE_INDEX_STATUS_INSPECTION_UNREADABLE = "inspection_unreadable"
BUNDLE_INDEX_STATUS_NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class BundleIndexItem:
    zip_path: str
    zip_filename: str
    zip_size_bytes: int = 0
    zip_sha256: str = ""
    sha256_sidecar_path: str = ""
    sha256_sidecar_present: bool = False
    sha256_sidecar_matches: bool = False
    inspection_sidecar_path: str = ""
    inspection_sidecar_present: bool = False
    inspection_sidecar_readable: bool = False
    inspection_summary: dict[str, object] | None = None
    review_folder_path: str = ""
    review_folder_present: bool = False
    status: str = BUNDLE_INDEX_STATUS_NEEDS_REVIEW
    warnings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BundleIndexResult:
    root_path: str
    recursive: bool = False
    zip_count: int = 0
    items: tuple[BundleIndexItem, ...] = ()
    status_counts: dict[str, int] | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "errors": list(self.errors),
            "items": [bundle_index_item_to_dict(item) for item in self.items],
            "recursive": self.recursive,
            "root_path": self.root_path,
            "status_counts": dict(sorted((self.status_counts or {}).items())),
            "warnings": list(self.warnings),
            "zip_count": self.zip_count,
        }


def sha256_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return ""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_sha256_sidecar(path: str) -> str:
    sidecar_path = Path(path)
    if not sidecar_path.is_file():
        return ""
    text = sidecar_path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    first = text.split(None, 1)[0].strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", first):
        return ""
    return first


def _relative_sort_key(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def find_bundle_zip_files(root_path: str, recursive: bool = False) -> tuple[Path, ...]:
    root = Path(root_path)
    if not root.is_dir():
        return ()
    pattern = "**/*.zip" if recursive else "*.zip"
    return tuple(
        sorted(
            (path for path in root.glob(pattern) if path.is_file()),
            key=lambda path: _relative_sort_key(path, root),
        )
    )


def _inspection_summary_from_json(path: str) -> tuple[bool, dict[str, object] | None, str]:
    sidecar_path = Path(path)
    if not sidecar_path.is_file():
        return False, None, ""
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, None, f"Inspection sidecar is not readable JSON: {exc}"

    inspection = data.get("zip_inspection") if isinstance(data, dict) else None
    if not isinstance(inspection, dict):
        return False, None, "Inspection sidecar is missing zip_inspection object."

    try:
        summary = {
            "entry_count": int(inspection.get("entry_count") or 0),
            "file_entry_count": int(inspection.get("file_entry_count") or 0),
            "status": str(inspection.get("status", "")),
            "zip_sha256": str(inspection.get("zip_sha256", "")),
            "zip_size_bytes": int(inspection.get("zip_size_bytes") or 0),
        }
    except (TypeError, ValueError) as exc:
        return False, None, f"Inspection sidecar has invalid summary fields: {exc}"
    return True, summary, ""


def _review_folder_path(zip_path: Path) -> str:
    return str(zip_path.with_suffix(""))


def _status_for_item(
    *,
    sha256_sidecar_present: bool,
    sha256_sidecar_matches: bool,
    sha256_match_checked: bool,
    inspection_sidecar_present: bool,
    inspection_sidecar_readable: bool,
) -> str:
    if sha256_sidecar_present and sha256_match_checked and not sha256_sidecar_matches:
        return BUNDLE_INDEX_STATUS_SHA256_MISMATCH
    if inspection_sidecar_present and not inspection_sidecar_readable:
        return BUNDLE_INDEX_STATUS_INSPECTION_UNREADABLE
    if not sha256_sidecar_present:
        return BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR
    if not inspection_sidecar_present:
        return BUNDLE_INDEX_STATUS_MISSING_INSPECTION_SIDECAR
    if not sha256_match_checked:
        return BUNDLE_INDEX_STATUS_NEEDS_REVIEW
    return BUNDLE_INDEX_STATUS_COMPLETE


def build_bundle_index_item(
    zip_path: str,
    *,
    compute_hash: bool = True,
) -> BundleIndexItem:
    zip_file = Path(zip_path)
    zip_hash = sha256_file(str(zip_file)) if compute_hash else ""
    zip_size = zip_file.stat().st_size if zip_file.is_file() else 0
    sha_path = default_zip_sha256_sidecar_path(str(zip_file))
    json_path = default_zip_json_sidecar_path(str(zip_file))
    sidecar_hash = read_sha256_sidecar(sha_path)
    sha_present = Path(sha_path).is_file()
    sha_matches = bool(zip_hash and sidecar_hash and zip_hash == sidecar_hash)
    sha_match_checked = bool(compute_hash and zip_hash and sidecar_hash)
    json_present = Path(json_path).is_file()
    json_readable, inspection_summary, json_warning = _inspection_summary_from_json(json_path)
    review_folder = _review_folder_path(zip_file)
    status = _status_for_item(
        sha256_sidecar_present=sha_present,
        sha256_sidecar_matches=sha_matches,
        sha256_match_checked=sha_match_checked,
        inspection_sidecar_present=json_present,
        inspection_sidecar_readable=json_readable,
    )

    warnings: list[str] = []
    actions: list[str] = []
    if not sha_present:
        warnings.append(f"SHA256 sidecar missing: {sha_path}")
        actions.append("Create or locate the matching .sha256 sidecar.")
    elif sha_match_checked and not sha_matches:
        warnings.append("SHA256 sidecar hash does not match the local ZIP hash.")
        actions.append("Review the ZIP and .sha256 sidecar before trusting this bundle.")
    elif sha_present and not sha_match_checked:
        warnings.append("SHA256 sidecar hash was not compared to the local ZIP hash.")
        actions.append("Compute the local ZIP hash before treating the sidecar as verified.")
    if not json_present:
        warnings.append(f"Inspection JSON sidecar missing: {json_path}")
        actions.append("Create or locate the matching .inspection.json sidecar.")
    elif not json_readable:
        warnings.append(json_warning or "Inspection JSON sidecar could not be read.")
        actions.append("Review or regenerate the inspection JSON sidecar.")
    if status != BUNDLE_INDEX_STATUS_COMPLETE:
        actions.append("No ZIP extraction, network, archive checks, or downloads are performed.")

    return BundleIndexItem(
        zip_path=str(zip_file),
        zip_filename=zip_file.name,
        zip_size_bytes=zip_size,
        zip_sha256=zip_hash,
        sha256_sidecar_path=sha_path,
        sha256_sidecar_present=sha_present,
        sha256_sidecar_matches=sha_matches,
        inspection_sidecar_path=json_path,
        inspection_sidecar_present=json_present,
        inspection_sidecar_readable=json_readable,
        inspection_summary=inspection_summary,
        review_folder_path=review_folder,
        review_folder_present=Path(review_folder).is_dir(),
        status=status,
        warnings=tuple(warnings),
        recommended_actions=tuple(dict.fromkeys(actions)),
    )


def _status_counts(items: Sequence[BundleIndexItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return dict(sorted(counts.items()))


def build_bundle_index(
    root_path: str,
    *,
    recursive: bool = False,
    compute_hash: bool = True,
) -> BundleIndexResult:
    root = Path(root_path)
    if not root.is_dir():
        return BundleIndexResult(
            root_path=root_path,
            recursive=recursive,
            errors=(f"Bundle index root does not exist: {root_path}",),
            warnings=(
                "Local bundle index uses existing files only; no ZIP extraction, network, archive checks, or downloads are performed.",
            ),
        )

    items = tuple(
        build_bundle_index_item(str(path), compute_hash=compute_hash)
        for path in find_bundle_zip_files(root_path, recursive=recursive)
    )
    return BundleIndexResult(
        root_path=root_path,
        recursive=recursive,
        zip_count=len(items),
        items=items,
        status_counts=_status_counts(items),
        warnings=(
            "Local bundle index uses existing files only; no ZIP extraction, network, archive checks, or downloads are performed.",
        ),
    )


def bundle_index_item_to_dict(item: BundleIndexItem) -> dict[str, object]:
    return item.to_dict()


def bundle_index_to_dict(result: BundleIndexResult) -> dict[str, object]:
    return result.to_dict()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- (none)")


def build_bundle_index_text(result: BundleIndexResult) -> str:
    lines = [
        "Total Export bundle index",
        "Scope: local files and sidecars only; no ZIP extraction, network, archive checks, downloads, scraping, screenshots, transcription, provider calls, or GUI behavior are performed.",
        f"Root path: {result.root_path}",
        f"Recursive: {_yes_no(result.recursive)}",
        f"ZIP count: {result.zip_count}",
        f"Status counts: {result.status_counts or {}}",
        "Items:",
    ]
    if result.items:
        for item in result.items:
            lines.append(
                f"- {item.zip_path} [status={item.status}; size={item.zip_size_bytes}; sha256={item.zip_sha256 or '(none)'}]"
            )
            lines.append(
                "  Sidecars: "
                f"sha256={_yes_no(item.sha256_sidecar_present)} "
                f"match={_yes_no(item.sha256_sidecar_matches)}; "
                f"inspection={_yes_no(item.inspection_sidecar_present)} "
                f"readable={_yes_no(item.inspection_sidecar_readable)}"
            )
            if item.warnings:
                lines.append("  Warnings:")
                lines.extend(f"  - {warning}" for warning in item.warnings)
            if item.recommended_actions:
                lines.append("  Recommended actions:")
                lines.extend(f"  - {action}" for action in item.recommended_actions)
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    return "\n".join(lines)


def build_bundle_index_markdown(result: BundleIndexResult) -> str:
    lines = [
        "# Total Export Bundle Index",
        "",
        "Local files and sidecars only. This report does not extract ZIP files, fetch sources, check archives, submit archive URLs, download media, scrape pages, capture screenshots, transcribe, call providers, or wire into the GUI.",
        "",
        "## Counts",
        "",
        f"- Root path: `{result.root_path}`",
        f"- Recursive: {_yes_no(result.recursive)}",
        f"- ZIP count: {result.zip_count}",
        f"- Status counts: `{result.status_counts or {}}`",
        "",
        "## ZIPs",
        "",
        "| ZIP path | Status | Size bytes | SHA-256 sidecar | SHA-256 matches | Inspection sidecar | Inspection readable | Recommended actions |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for item in result.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.zip_path,
                    item.status,
                    str(item.zip_size_bytes),
                    _yes_no(item.sha256_sidecar_present),
                    _yes_no(item.sha256_sidecar_matches),
                    _yes_no(item.inspection_sidecar_present),
                    _yes_no(item.inspection_sidecar_readable),
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
            "- Missing or mismatched sidecars are local follow-up signals only.",
            "- No ZIP extraction is performed.",
            "- No downloads, source fetching, scraping, screenshots, archive checks/submission, transcription, provider calls, or GUI behavior are performed.",
        ]
    )
    return "\n".join(lines)
