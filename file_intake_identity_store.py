"""Persistent FILES/media intake identity store.

V80R extends the side-effect-free V80P dedupe planner with a small JSON
identity store that can be read before planning and updated after a confirmed
FILES/media intake.  This gives browser-grid image intake a stronger memory
than the current process-only cache while keeping review/planning separate from
actual download/copy/delete work.

JDownloader/AppWork source pattern reviewed: download/controller identity and
watchdog layers keep explicit records for already-known linkable/downloaded
items and avoid repeating known work.  This Python/Tk implementation ports that
structure into YTCE terms: stable source URL/local path/hash records, bounded
identity history, stale-local-path filtering, and deterministic merge rules.

Substantial reference notes are recorded in THIRD_PARTY_NOTICES_JDOWNLOADER_APPWORK.md.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from file_intake_dedupe import (
    ExistingFileRecord,
    canonicalize_intake_source_url,
    existing_file_record_from_mapping,
    intake_identity_keys_for,
    normalize_intake_local_path,
    normalize_sha256,
)


FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION = "file-intake-identity-store-v80r"
DEFAULT_FILE_INTAKE_IDENTITY_MAX_RECORDS = 2048


@dataclass(frozen=True)
class FileIntakeIdentityStoreLoadResult:
    """Result from loading a persisted FILES/media identity store."""

    path: str
    records: tuple[ExistingFileRecord, ...]
    stale_records: tuple[ExistingFileRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def stale_count(self) -> int:
        return len(self.stale_records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "record_count": self.record_count,
            "records": [record.to_dict() for record in self.records],
            "schema_version": self.schema_version,
            "stale_count": self.stale_count,
            "stale_records": [record.to_dict() for record in self.stale_records],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FileIntakeIdentityStoreSaveResult:
    """Result from writing a persisted FILES/media identity store."""

    path: str
    saved_count: int
    warnings: tuple[str, ...] = ()
    schema_version: str = FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_file_intake_identity_record(
    *,
    record_id: str,
    display_name: str = "",
    source_url: str = "",
    local_path: str = "",
    sha256: str = "",
    size_bytes: int = 0,
    media_type: str = "",
    mime_type: str = "",
    provenance: str = "file_intake_identity_store",
) -> ExistingFileRecord:
    """Build a normalized existing-record object for persistence/reuse."""

    return ExistingFileRecord(
        record_id=str(record_id or "").strip(),
        display_name=str(display_name or "").strip(),
        source_url=str(source_url or "").strip(),
        local_path=str(local_path or "").strip(),
        sha256=normalize_sha256(sha256),
        size_bytes=_coerce_non_negative_int(size_bytes),
        media_type=str(media_type or "").strip(),
        mime_type=str(mime_type or "").strip(),
        provenance=str(provenance or "file_intake_identity_store").strip(),
    )


def load_file_intake_identity_store(
    path: str | Path,
    *,
    require_existing_local_path: bool = True,
) -> FileIntakeIdentityStoreLoadResult:
    """Load persisted identity records from JSON.

    When ``require_existing_local_path`` is true, records with local paths that
    no longer exist are returned as stale records instead of authoritative
    records.  This prevents old temp-download identities from suppressing a new
    FILES add after the backing file has been cleaned up.
    """

    store_path = Path(path)
    warnings: list[str] = []
    if not store_path.is_file():
        return FileIntakeIdentityStoreLoadResult(path=str(store_path), records=())
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except Exception:
        return FileIntakeIdentityStoreLoadResult(
            path=str(store_path),
            records=(),
            warnings=("identity_store_read_failed",),
        )
    raw_records = payload.get("records", []) if isinstance(payload, Mapping) else []
    records: list[ExistingFileRecord] = []
    stale: list[ExistingFileRecord] = []
    for index, raw in enumerate(raw_records or ()):  # tolerate partial legacy/corrupt rows
        if not isinstance(raw, Mapping):
            warnings.append(f"record_{index}_ignored")
            continue
        try:
            record = existing_file_record_from_mapping(raw)
        except Exception:
            warnings.append(f"record_{index}_coerce_failed")
            continue
        if not _record_has_identity(record):
            warnings.append(f"record_{index}_no_identity")
            continue
        if require_existing_local_path and record.local_path and not Path(record.local_path).is_file():
            stale.append(record)
            continue
        if require_existing_local_path and not record.local_path:
            stale.append(record)
            continue
        records.append(record)
    return FileIntakeIdentityStoreLoadResult(
        path=str(store_path),
        records=tuple(records),
        stale_records=tuple(stale),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def save_file_intake_identity_store(
    path: str | Path,
    records: Iterable[ExistingFileRecord | Mapping[str, Any]],
    *,
    max_records: int = DEFAULT_FILE_INTAKE_IDENTITY_MAX_RECORDS,
) -> FileIntakeIdentityStoreSaveResult:
    """Write a bounded JSON identity store.

    The function creates the parent directory and writes only the explicit
    records supplied by the caller.  It does not copy, move, delete, download,
    scan folders, or mutate FILES/session state.
    """

    store_path = Path(path)
    normalized = merge_file_intake_identity_records((), records, max_records=max_records)
    payload = {
        "schema_version": FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION,
        "saved_at_unix": time.time(),
        "record_count": len(normalized),
        "records": [_record_to_store_mapping(record) for record in normalized],
    }
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return FileIntakeIdentityStoreSaveResult(path=str(store_path), saved_count=len(normalized))
    except Exception:
        return FileIntakeIdentityStoreSaveResult(
            path=str(store_path),
            saved_count=0,
            warnings=("identity_store_write_failed",),
        )


def merge_file_intake_identity_records(
    existing: Iterable[ExistingFileRecord | Mapping[str, Any]],
    new_records: Iterable[ExistingFileRecord | Mapping[str, Any]],
    *,
    max_records: int = DEFAULT_FILE_INTAKE_IDENTITY_MAX_RECORDS,
) -> tuple[ExistingFileRecord, ...]:
    """Merge records by strongest known identity, newest record wins."""

    merged: dict[str, ExistingFileRecord] = {}
    order: list[str] = []
    for record_like in tuple(existing or ()) + tuple(new_records or ()):  # preserve order then replace
        record = _coerce_existing(record_like)
        if not _record_has_identity(record):
            continue
        key = _record_primary_key(record)
        if key not in merged:
            order.append(key)
        merged[key] = record
    bounded = [merged[key] for key in order if key in merged]
    if max_records > 0 and len(bounded) > max_records:
        bounded = bounded[-max_records:]
    return tuple(bounded)


def _record_to_store_mapping(record: ExistingFileRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "display_name": record.display_name,
        "source_url": canonicalize_intake_source_url(record.source_url) or record.source_url,
        "local_path": str(record.local_path or ""),
        "normalized_local_path": normalize_intake_local_path(record.local_path),
        "sha256": normalize_sha256(record.sha256),
        "size_bytes": _coerce_non_negative_int(record.size_bytes),
        "media_type": record.media_type,
        "mime_type": record.mime_type,
        "provenance": record.provenance,
        "schema_version": FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION,
    }


def _coerce_existing(value: ExistingFileRecord | Mapping[str, Any]) -> ExistingFileRecord:
    if isinstance(value, ExistingFileRecord):
        return value
    return existing_file_record_from_mapping(value)


def _record_has_identity(record: ExistingFileRecord) -> bool:
    return bool(
        intake_identity_keys_for(
            source_url=record.source_url,
            local_path=record.local_path,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
        )
    )


def _record_primary_key(record: ExistingFileRecord) -> str:
    keys = intake_identity_keys_for(
        source_url=record.source_url,
        local_path=record.local_path,
        sha256=record.sha256,
        size_bytes=record.size_bytes,
    )
    if keys:
        return keys[0]
    return f"record:{record.record_id}"


def _coerce_non_negative_int(value: object) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except Exception:
        return 0
    return max(0, number)
