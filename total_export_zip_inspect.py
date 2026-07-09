from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from total_export_manifest import sha256_for_file


ZIP_INSPECTION_STATUS_OK = "ok"
ZIP_INSPECTION_STATUS_OK_WITH_WARNINGS = "ok_with_warnings"
ZIP_INSPECTION_STATUS_MISSING_ZIP = "missing_zip"
ZIP_INSPECTION_STATUS_INVALID_ZIP = "invalid_zip"
ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES = "unsafe_entries"
ZIP_INSPECTION_STATUS_MISSING_MANIFEST = "missing_manifest"
ZIP_INSPECTION_STATUS_MULTIPLE_MANIFESTS = "multiple_manifests"
ZIP_INSPECTION_STATUS_EMPTY_ZIP = "empty_zip"

STANDARD_REVIEW_ENTRY_PATHS = (
    ("summary", "metadata/TOTAL_EXPORT_SUMMARY.txt"),
    ("readme", "README_TOTAL_EXPORT.txt"),
    ("source_plan_report", "metadata/SOURCE_CAPTURE_PLAN.txt"),
    ("inventory_report", "metadata/TOTAL_EXPORT_INVENTORY.txt"),
)

CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
END_OF_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x05\x06"


@dataclass(frozen=True)
class TotalExportZipEntryInspection:
    name: str
    size_bytes: int
    compressed_size_bytes: int
    sha256: str = ""
    is_dir: bool = False


@dataclass(frozen=True)
class TotalExportZipStandardEntryInspection:
    label: str
    relative_path: str
    exists: bool


@dataclass(frozen=True)
class TotalExportZipInspectionResult:
    zip_path: str
    status: str = ZIP_INSPECTION_STATUS_MISSING_ZIP
    zip_found: bool = False
    zip_readable: bool = False
    zip_size_bytes: int = 0
    zip_sha256: str = ""
    entry_count: int = 0
    file_entry_count: int = 0
    directory_entry_count: int = 0
    top_level_name: str = ""
    single_top_level_folder: bool = False
    manifest_entries: tuple[str, ...] = ()
    standard_entries: tuple[TotalExportZipStandardEntryInspection, ...] = ()
    entries: tuple[TotalExportZipEntryInspection, ...] = ()
    unsafe_entries: tuple[str, ...] = ()
    duplicate_entries: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _normalized_name(name: str) -> str:
    return (name or "").replace("\\", "/")


def _is_directory_name(name: str) -> bool:
    return name.endswith("/") or name.endswith("\\")


def _is_unsafe_entry_name(name: str) -> bool:
    normalized = _normalized_name(name)
    if not name or "\\" in name:
        return True
    if normalized.startswith("/") or normalized.startswith("//"):
        return True
    if re.match(r"^[A-Za-z]:/", normalized):
        return True
    stripped = normalized.rstrip("/")
    if not stripped:
        return True
    parts = stripped.split("/")
    if any(part in {"", ".."} for part in parts):
        return True
    return False


def _read_uint16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _read_uint32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _raw_central_directory_names(path: Path) -> tuple[str, ...]:
    data = path.read_bytes()
    eocd_offset = data.rfind(END_OF_CENTRAL_DIRECTORY_SIGNATURE)
    if eocd_offset < 0 or eocd_offset + 22 > len(data):
        return ()

    central_directory_size = _read_uint32(data, eocd_offset + 12)
    central_directory_offset = _read_uint32(data, eocd_offset + 16)
    end_offset = min(central_directory_offset + central_directory_size, len(data))
    offset = central_directory_offset
    names = []

    while offset + 46 <= end_offset:
        if data[offset:offset + 4] != CENTRAL_DIRECTORY_SIGNATURE:
            break
        general_purpose_flag = _read_uint16(data, offset + 8)
        filename_length = _read_uint16(data, offset + 28)
        extra_length = _read_uint16(data, offset + 30)
        comment_length = _read_uint16(data, offset + 32)
        filename_start = offset + 46
        filename_end = filename_start + filename_length
        if filename_end > len(data):
            break
        filename_bytes = data[filename_start:filename_end]
        encoding = "utf-8" if general_purpose_flag & 0x800 else "cp437"
        names.append(filename_bytes.decode(encoding, errors="replace"))
        offset = filename_end + extra_length + comment_length
    return tuple(names)


def _top_level_names(names: tuple[str, ...]) -> tuple[str, ...]:
    top_levels = []
    seen = set()
    for name in names:
        if _is_directory_name(name):
            continue
        normalized = _normalized_name(name).strip("/")
        if not normalized:
            continue
        top_level = normalized.split("/", 1)[0]
        if top_level and top_level not in seen:
            seen.add(top_level)
            top_levels.append(top_level)
    return tuple(sorted(top_levels))


def _manifest_entries(names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in names
            if not _is_directory_name(name) and _normalized_name(name).endswith("_manifest.json")
        )
    )


def _standard_entries(
    *,
    names: tuple[str, ...],
    top_level_name: str,
) -> tuple[TotalExportZipStandardEntryInspection, ...]:
    name_set = {_normalized_name(name) for name in names}
    entries = []
    for label, relative_path in STANDARD_REVIEW_ENTRY_PATHS:
        expected_entry = f"{top_level_name}/{relative_path}" if top_level_name else relative_path
        entries.append(
            TotalExportZipStandardEntryInspection(
                label=label,
                relative_path=relative_path,
                exists=expected_entry in name_set,
            )
        )
    return tuple(entries)


def _status(
    *,
    entry_count: int,
    unsafe_entries: tuple[str, ...],
    manifest_entries: tuple[str, ...],
    warnings: tuple[str, ...],
) -> str:
    if entry_count == 0:
        return ZIP_INSPECTION_STATUS_EMPTY_ZIP
    if unsafe_entries:
        return ZIP_INSPECTION_STATUS_UNSAFE_ENTRIES
    if len(manifest_entries) > 1:
        return ZIP_INSPECTION_STATUS_MULTIPLE_MANIFESTS
    if not manifest_entries:
        return ZIP_INSPECTION_STATUS_MISSING_MANIFEST
    if warnings:
        return ZIP_INSPECTION_STATUS_OK_WITH_WARNINGS
    return ZIP_INSPECTION_STATUS_OK


def _zip_entry_inspections(
    *,
    zip_file: ZipFile,
    hash_entries: bool,
) -> tuple[TotalExportZipEntryInspection, ...]:
    entries = []
    for info in sorted(zip_file.infolist(), key=lambda item: item.filename):
        is_dir = info.is_dir()
        entry_hash = ""
        if hash_entries and not is_dir:
            digest = hashlib.sha256()
            with zip_file.open(info, "r") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            entry_hash = digest.hexdigest()
        entries.append(
            TotalExportZipEntryInspection(
                name=info.filename,
                size_bytes=info.file_size,
                compressed_size_bytes=info.compress_size,
                sha256=entry_hash,
                is_dir=is_dir,
            )
        )
    return tuple(entries)


def inspect_total_export_zip(
    zip_path: str,
    include_entries: bool = False,
    hash_entries: bool = False,
) -> TotalExportZipInspectionResult:
    path = Path(zip_path)
    if not path.is_file():
        return TotalExportZipInspectionResult(
            zip_path=zip_path,
            status=ZIP_INSPECTION_STATUS_MISSING_ZIP,
            errors=(f"ZIP file does not exist: {zip_path}",),
        )

    try:
        with ZipFile(path, "r") as zip_file:
            infos = zip_file.infolist()
            names = tuple(info.filename for info in infos)
            raw_names = _raw_central_directory_names(path) or names
            sorted_names = tuple(sorted(names))
            file_names = tuple(name for name in sorted_names if not _is_directory_name(name))
            directory_names = tuple(name for name in sorted_names if _is_directory_name(name))
            top_levels = _top_level_names(sorted_names)
            single_top_level_folder = len(top_levels) == 1
            top_level_name = top_levels[0] if single_top_level_folder else ""
            manifests = _manifest_entries(sorted_names)
            duplicate_entries = tuple(
                sorted(name for name, count in Counter(raw_names).items() if count > 1)
            )
            unsafe_entries = tuple(
                sorted(name for name in raw_names if _is_unsafe_entry_name(name))
            )
            standard_entries = _standard_entries(
                names=sorted_names,
                top_level_name=top_level_name,
            )

            warnings = []
            if duplicate_entries:
                warnings.append(f"Duplicate ZIP entries found: {', '.join(duplicate_entries)}")
            missing_standard = tuple(
                entry.relative_path for entry in standard_entries if not entry.exists
            )
            if missing_standard and len(manifests) == 1 and not unsafe_entries:
                warnings.append(
                    f"Optional standard review entries missing: {', '.join(missing_standard)}"
                )
            if len(top_levels) != 1 and file_names:
                warnings.append("ZIP does not contain a single top-level package folder.")

            entry_inspections = ()
            if include_entries:
                entry_inspections = _zip_entry_inspections(
                    zip_file=zip_file,
                    hash_entries=hash_entries,
                )

            return TotalExportZipInspectionResult(
                zip_path=zip_path,
                status=_status(
                    entry_count=len(infos),
                    unsafe_entries=unsafe_entries,
                    manifest_entries=manifests,
                    warnings=tuple(warnings),
                ),
                zip_found=True,
                zip_readable=True,
                zip_size_bytes=path.stat().st_size,
                zip_sha256=sha256_for_file(str(path)),
                entry_count=len(infos),
                file_entry_count=len(file_names),
                directory_entry_count=len(directory_names),
                top_level_name=top_level_name,
                single_top_level_folder=single_top_level_folder,
                manifest_entries=manifests,
                standard_entries=standard_entries,
                entries=entry_inspections,
                unsafe_entries=unsafe_entries,
                duplicate_entries=duplicate_entries,
                warnings=tuple(warnings),
            )
    except BadZipFile as exc:
        return TotalExportZipInspectionResult(
            zip_path=zip_path,
            status=ZIP_INSPECTION_STATUS_INVALID_ZIP,
            zip_found=True,
            zip_size_bytes=path.stat().st_size,
            zip_sha256=sha256_for_file(str(path)),
            errors=(f"ZIP file is not readable: {exc}",),
        )


def total_export_zip_inspection_to_dict(
    result: TotalExportZipInspectionResult,
) -> dict[str, object]:
    return {
        "directory_entry_count": result.directory_entry_count,
        "duplicate_entries": list(result.duplicate_entries),
        "entries": [
            {
                "compressed_size_bytes": entry.compressed_size_bytes,
                "is_dir": entry.is_dir,
                "name": entry.name,
                "sha256": entry.sha256,
                "size_bytes": entry.size_bytes,
            }
            for entry in result.entries
        ],
        "entry_count": result.entry_count,
        "errors": list(result.errors),
        "file_entry_count": result.file_entry_count,
        "manifest_entries": list(result.manifest_entries),
        "single_top_level_folder": result.single_top_level_folder,
        "standard_entries": [
            {
                "exists": entry.exists,
                "label": entry.label,
                "relative_path": entry.relative_path,
            }
            for entry in result.standard_entries
        ],
        "status": result.status,
        "top_level_name": result.top_level_name,
        "unsafe_entries": list(result.unsafe_entries),
        "warnings": list(result.warnings),
        "zip_found": result.zip_found,
        "zip_path": result.zip_path,
        "zip_readable": result.zip_readable,
        "zip_sha256": result.zip_sha256,
        "zip_size_bytes": result.zip_size_bytes,
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _append_sequence(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    lines.append(label)
    if values:
        for value in values:
            lines.append(f"- {value}")
    else:
        lines.append("- (none)")


def build_total_export_zip_inspection_text(
    result: TotalExportZipInspectionResult,
) -> str:
    lines = [
        "Total Export ZIP inspection",
        f"ZIP path: {result.zip_path}",
        f"Status: {result.status}",
        f"ZIP found: {_yes_no(result.zip_found)}",
        f"ZIP readable: {_yes_no(result.zip_readable)}",
        f"ZIP size bytes: {result.zip_size_bytes}",
        f"ZIP SHA-256: {result.zip_sha256 or '(none)'}",
        f"Entry count: {result.entry_count}",
        f"File entry count: {result.file_entry_count}",
        f"Directory entry count: {result.directory_entry_count}",
        f"Top-level name: {result.top_level_name or '(none)'}",
        f"Single top-level folder: {_yes_no(result.single_top_level_folder)}",
    ]
    _append_sequence(lines, "Manifest entries:", result.manifest_entries)
    lines.append("Standard entries:")
    if result.standard_entries:
        for entry in result.standard_entries:
            lines.append(
                f"- {entry.label}: {entry.relative_path} [exists={_yes_no(entry.exists)}]"
            )
    else:
        lines.append("- (none)")
    _append_sequence(lines, "Unsafe entries:", result.unsafe_entries)
    _append_sequence(lines, "Duplicate entries:", result.duplicate_entries)
    _append_sequence(lines, "Errors:", result.errors)
    _append_sequence(lines, "Warnings:", result.warnings)
    if result.entries:
        lines.append("Entries:")
        for entry in result.entries:
            suffix = f"; sha256={entry.sha256}" if entry.sha256 else ""
            kind = "dir" if entry.is_dir else "file"
            lines.append(
                f"- {entry.name} [{kind}; size={entry.size_bytes}; "
                f"compressed={entry.compressed_size_bytes}{suffix}]"
            )
    return "\n".join(lines)
