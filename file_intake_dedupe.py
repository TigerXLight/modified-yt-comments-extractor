"""Deterministic FILES/media intake duplicate guard.

V80P adds a small, side-effect-free intake classifier that can be used before
adding browser-discovered media, downloaded media, or Profile/Media Database
materialized files into FILES/evidence stores.

JDownloader/AppWork source pattern reviewed: file/download-controller identity
and queue/watchdog layers keep explicit records for downloaded/linkable items,
avoid repeating already-known work, and separate decision/planning from actual
I/O.  This Python/Tk project implementation does not paste Java source; it
implements the same method-of-operation in YTCE terminology:

- canonical source URL identity
- normalized local path identity
- sha256/size identity where available
- batch-local duplicate detection
- existing-record reuse detection
- explicit added/reused/duplicate/failed counts
- no filesystem mutation during review

Substantial reference notes are recorded in THIRD_PARTY_NOTICES_JDOWNLOADER_APPWORK.md.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit


FILE_INTAKE_DEDUPE_SCHEMA_VERSION = "file-intake-dedupe-v80p"
FILE_INTAKE_STATUS_ADDED = "added"
FILE_INTAKE_STATUS_REUSED = "reused"
FILE_INTAKE_STATUS_DUPLICATE = "duplicate"
FILE_INTAKE_STATUS_FAILED = "failed"
FILE_INTAKE_STATUS_SKIPPED = "skipped"

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ocid",
    "spm",
    "vero_id",
}

_FILE_INTAKE_SCOPE = (
    "side-effect-free FILES/media intake dedupe planning only; no copy, move, "
    "delete, download, browser action, external provider call, or filesystem "
    "mutation is performed"
)


@dataclass(frozen=True)
class FileIntakeCandidate:
    """One candidate the UI or backend wants to add to FILES/evidence storage."""

    candidate_id: str
    display_name: str = ""
    source_url: str = ""
    local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    media_type: str = ""
    mime_type: str = ""
    destination_name: str = ""
    provenance: str = "operator_selected"
    schema_version: str = FILE_INTAKE_DEDUPE_SCHEMA_VERSION

    def canonical_source_url(self) -> str:
        return canonicalize_intake_source_url(self.source_url)

    def normalized_local_path(self) -> str:
        return normalize_intake_local_path(self.local_path)

    def normalized_sha256(self) -> str:
        return normalize_sha256(self.sha256)

    def identity_key(self) -> str:
        return build_intake_identity_key(
            source_url=self.source_url,
            local_path=self.local_path,
            sha256=self.sha256,
            size_bytes=self.size_bytes,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["canonical_source_url"] = self.canonical_source_url()
        data["normalized_local_path"] = self.normalized_local_path()
        data["normalized_sha256"] = self.normalized_sha256()
        data["identity_key"] = self.identity_key()
        return data


@dataclass(frozen=True)
class ExistingFileRecord:
    """Already-known FILES/evidence/media record used as dedupe input."""

    record_id: str
    display_name: str = ""
    source_url: str = ""
    local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    media_type: str = ""
    mime_type: str = ""
    provenance: str = "existing_record"
    schema_version: str = FILE_INTAKE_DEDUPE_SCHEMA_VERSION

    def canonical_source_url(self) -> str:
        return canonicalize_intake_source_url(self.source_url)

    def normalized_local_path(self) -> str:
        return normalize_intake_local_path(self.local_path)

    def normalized_sha256(self) -> str:
        return normalize_sha256(self.sha256)

    def identity_key(self) -> str:
        return build_intake_identity_key(
            source_url=self.source_url,
            local_path=self.local_path,
            sha256=self.sha256,
            size_bytes=self.size_bytes,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["canonical_source_url"] = self.canonical_source_url()
        data["normalized_local_path"] = self.normalized_local_path()
        data["normalized_sha256"] = self.normalized_sha256()
        data["identity_key"] = self.identity_key()
        return data


@dataclass(frozen=True)
class FileIntakeDecision:
    """Review result for one candidate before FILES/evidence mutation."""

    candidate_id: str
    status: str
    reason: str
    canonical_source_url: str = ""
    normalized_local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    existing_record_id: str = ""
    duplicate_of_candidate_id: str = ""
    planned_action: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = FILE_INTAKE_DEDUPE_SCHEMA_VERSION
    file_copy_performed: bool = False
    file_move_performed: bool = False
    file_delete_performed: bool = False
    media_download_performed: bool = False
    browser_action_performed: bool = False
    provider_call_performed: bool = False
    automatic_classification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["warning_count"] = len(self.warnings)
        return data


@dataclass(frozen=True)
class FileIntakeDedupePlan:
    """Batch review plan for FILES/media intake candidates."""

    candidates: tuple[FileIntakeCandidate, ...]
    existing_records: tuple[ExistingFileRecord, ...]
    decisions: tuple[FileIntakeDecision, ...]
    schema_version: str = FILE_INTAKE_DEDUPE_SCHEMA_VERSION
    scope: str = _FILE_INTAKE_SCOPE
    file_copy_performed: bool = False
    file_move_performed: bool = False
    file_delete_performed: bool = False
    media_download_performed: bool = False
    browser_action_performed: bool = False
    provider_call_performed: bool = False
    automatic_classification_performed: bool = False

    @property
    def added_count(self) -> int:
        return _count_status(self.decisions, FILE_INTAKE_STATUS_ADDED)

    @property
    def reused_count(self) -> int:
        return _count_status(self.decisions, FILE_INTAKE_STATUS_REUSED)

    @property
    def duplicate_count(self) -> int:
        return _count_status(self.decisions, FILE_INTAKE_STATUS_DUPLICATE)

    @property
    def failed_count(self) -> int:
        return _count_status(self.decisions, FILE_INTAKE_STATUS_FAILED)

    @property
    def skipped_count(self) -> int:
        return _count_status(self.decisions, FILE_INTAKE_STATUS_SKIPPED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_count": self.added_count,
            "browser_action_performed": self.browser_action_performed,
            "candidate_count": len(self.candidates),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "decisions": [decision.to_dict() for decision in self.decisions],
            "duplicate_count": self.duplicate_count,
            "existing_record_count": len(self.existing_records),
            "existing_records": [record.to_dict() for record in self.existing_records],
            "failed_count": self.failed_count,
            "file_copy_performed": self.file_copy_performed,
            "file_delete_performed": self.file_delete_performed,
            "file_move_performed": self.file_move_performed,
            "media_download_performed": self.media_download_performed,
            "provider_call_performed": self.provider_call_performed,
            "reused_count": self.reused_count,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "skipped_count": self.skipped_count,
            "status_counts": build_intake_status_counts(self.decisions),
            "automatic_classification_performed": self.automatic_classification_performed,
        }


@dataclass(frozen=True)
class FileHashResult:
    """Hash/size outcome for an explicit local path."""

    path: str
    status: str
    sha256: str = ""
    size_bytes: int = 0
    warnings: tuple[str, ...] = ()
    schema_version: str = FILE_INTAKE_DEDUPE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_sha256(value: object) -> str:
    text = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", text):
        return text
    return ""


def normalize_intake_local_path(value: object) -> str:
    """Normalize local paths for comparison without touching the filesystem."""

    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    text = text.replace("\\", "/")
    text = re.sub(r"/+", "/", text)
    text = text.rstrip("/")
    if re.match(r"^[A-Za-z]:/", text):
        text = text[0].lower() + text[1:]
    return text.lower()


def _normalize_url_path(path: str) -> str:
    # Keep URL path semantics but remove common copy/paste and percent-escape noise.
    text = unquote(path or "/") or "/"
    pieces = [quote(piece, safe="-._~!$&'()*+,;=:@") for piece in text.split("/")]
    normalized = "/".join(pieces)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized


def canonicalize_intake_source_url(value: object) -> str:
    """Canonicalize source URL identity for duplicate comparison.

    The result keeps meaningful query parameters but removes common tracking
    parameters and fragments.  It lowercases the scheme/host and removes default
    ports, while avoiding a network request.
    """

    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    parsed = urlsplit(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ""
    port = parsed.port
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    query_pairs = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        key_l = key.lower()
        if key_l in TRACKING_QUERY_KEYS or any(key_l.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, val))
    query_pairs.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(query_pairs, doseq=True)
    path = _normalize_url_path(parsed.path)
    return urlunsplit((scheme, netloc, path, query, ""))


def build_intake_identity_key(
    *,
    source_url: object = "",
    local_path: object = "",
    sha256: object = "",
    size_bytes: object = 0,
) -> str:
    """Build a stable strongest-available identity key for one intake item."""

    digest = normalize_sha256(sha256)
    size = _coerce_non_negative_int(size_bytes)
    if digest:
        if size:
            return f"sha256-size:{digest}:{size}"
        return f"sha256:{digest}"
    canonical_url = canonicalize_intake_source_url(source_url)
    if canonical_url:
        return f"source-url:{canonical_url}"
    normalized_path = normalize_intake_local_path(local_path)
    if normalized_path:
        return f"local-path:{normalized_path}"
    return ""


def hash_local_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> FileHashResult:
    """Hash a caller-specified local file and report sha256/size.

    This reads only the explicit path supplied by the caller.  It does not copy,
    move, delete, download, scan folders, or create files.
    """

    text = str(path or "").strip()
    if not text:
        return FileHashResult(path="", status=FILE_INTAKE_STATUS_FAILED, warnings=("path_required",))
    candidate = Path(text)
    if not candidate.is_file():
        return FileHashResult(path=text, status=FILE_INTAKE_STATUS_FAILED, warnings=("file_not_found",))
    digest = hashlib.sha256()
    size = 0
    with candidate.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return FileHashResult(
        path=text,
        status=FILE_INTAKE_STATUS_ADDED,
        sha256=digest.hexdigest(),
        size_bytes=size,
    )


def candidate_with_file_hash(candidate: FileIntakeCandidate) -> FileIntakeCandidate:
    """Return candidate enriched with sha256/size when local_path is readable."""

    if candidate.normalized_sha256() or not candidate.local_path:
        return candidate
    result = hash_local_file(candidate.local_path)
    if result.status != FILE_INTAKE_STATUS_ADDED:
        return candidate
    return replace(candidate, sha256=result.sha256, size_bytes=result.size_bytes)


def file_intake_candidate_from_mapping(payload: Mapping[str, Any]) -> FileIntakeCandidate:
    return FileIntakeCandidate(
        candidate_id=str(payload.get("candidate_id") or payload.get("resource_id") or payload.get("item_id") or "").strip(),
        display_name=str(payload.get("display_name") or payload.get("name") or "").strip(),
        source_url=str(payload.get("source_url") or payload.get("reference_url") or payload.get("url") or "").strip(),
        local_path=str(payload.get("local_path") or payload.get("output_path") or payload.get("path") or "").strip(),
        sha256=str(payload.get("sha256") or payload.get("hash") or "").strip(),
        size_bytes=_coerce_non_negative_int(payload.get("size_bytes") or payload.get("size") or 0),
        media_type=str(payload.get("media_type") or "").strip(),
        mime_type=str(payload.get("mime_type") or "").strip(),
        destination_name=str(payload.get("destination_name") or payload.get("filename") or "").strip(),
        provenance=str(payload.get("provenance") or "operator_selected").strip(),
    )


def existing_file_record_from_mapping(payload: Mapping[str, Any]) -> ExistingFileRecord:
    return ExistingFileRecord(
        record_id=str(payload.get("record_id") or payload.get("item_id") or payload.get("resource_id") or "").strip(),
        display_name=str(payload.get("display_name") or payload.get("name") or "").strip(),
        source_url=str(payload.get("source_url") or payload.get("reference_url") or payload.get("url") or "").strip(),
        local_path=str(payload.get("local_path") or payload.get("output_path") or payload.get("path") or "").strip(),
        sha256=str(payload.get("sha256") or payload.get("hash") or "").strip(),
        size_bytes=_coerce_non_negative_int(payload.get("size_bytes") or payload.get("size") or 0),
        media_type=str(payload.get("media_type") or "").strip(),
        mime_type=str(payload.get("mime_type") or "").strip(),
        provenance=str(payload.get("provenance") or "existing_record").strip(),
    )


def build_file_intake_dedupe_plan(
    *,
    candidates: Iterable[FileIntakeCandidate | Mapping[str, Any]],
    existing_records: Iterable[ExistingFileRecord | Mapping[str, Any]] = (),
    enrich_hashes: bool = False,
) -> FileIntakeDedupePlan:
    """Classify a batch as added/reused/duplicate/failed without mutation."""

    normalized_candidates = tuple(
        _coerce_candidate(candidate, enrich_hashes=enrich_hashes)
        for candidate in candidates
    )
    normalized_existing = tuple(_coerce_existing(record) for record in existing_records)
    existing_index = _build_existing_identity_index(normalized_existing)
    seen_candidate_index: dict[str, FileIntakeCandidate] = {}
    decisions: list[FileIntakeDecision] = []

    for index, candidate in enumerate(normalized_candidates):
        candidate_id = candidate.candidate_id or f"candidate-{index + 1}"
        source_url = candidate.canonical_source_url()
        local_path = candidate.normalized_local_path()
        sha256 = candidate.normalized_sha256()
        size = _coerce_non_negative_int(candidate.size_bytes)
        identity_keys = intake_identity_keys_for(
            source_url=source_url,
            local_path=local_path,
            sha256=sha256,
            size_bytes=size,
        )
        if not identity_keys:
            decisions.append(
                FileIntakeDecision(
                    candidate_id=candidate_id,
                    status=FILE_INTAKE_STATUS_FAILED,
                    reason="no_identity",
                    canonical_source_url=source_url,
                    normalized_local_path=local_path,
                    sha256=sha256,
                    size_bytes=size,
                    planned_action="review_required",
                    warnings=("candidate_requires_source_url_local_path_or_sha256",),
                )
            )
            continue

        existing_match = _first_existing_match(identity_keys, existing_index)
        if existing_match is not None:
            decisions.append(
                FileIntakeDecision(
                    candidate_id=candidate_id,
                    status=FILE_INTAKE_STATUS_REUSED,
                    reason="matches_existing_record",
                    canonical_source_url=source_url,
                    normalized_local_path=local_path,
                    sha256=sha256,
                    size_bytes=size,
                    existing_record_id=existing_match.record_id,
                    planned_action="reuse_existing_record",
                )
            )
            continue

        duplicate = _first_seen_candidate_match(identity_keys, seen_candidate_index)
        if duplicate is not None:
            decisions.append(
                FileIntakeDecision(
                    candidate_id=candidate_id,
                    status=FILE_INTAKE_STATUS_DUPLICATE,
                    reason="duplicates_candidate_in_current_batch",
                    canonical_source_url=source_url,
                    normalized_local_path=local_path,
                    sha256=sha256,
                    size_bytes=size,
                    duplicate_of_candidate_id=duplicate.candidate_id,
                    planned_action="skip_duplicate",
                )
            )
            continue

        for key in identity_keys:
            seen_candidate_index.setdefault(key, candidate)
        decisions.append(
            FileIntakeDecision(
                candidate_id=candidate_id,
                status=FILE_INTAKE_STATUS_ADDED,
                reason="new_identity",
                canonical_source_url=source_url,
                normalized_local_path=local_path,
                sha256=sha256,
                size_bytes=size,
                planned_action="add_new_record",
            )
        )

    return FileIntakeDedupePlan(
        candidates=normalized_candidates,
        existing_records=normalized_existing,
        decisions=tuple(decisions),
    )


def intake_identity_keys_for(
    *,
    source_url: object = "",
    local_path: object = "",
    sha256: object = "",
    size_bytes: object = 0,
) -> tuple[str, ...]:
    """Return all comparable identity keys, strongest first."""

    keys: list[str] = []
    digest = normalize_sha256(sha256)
    size = _coerce_non_negative_int(size_bytes)
    if digest:
        if size:
            keys.append(f"sha256-size:{digest}:{size}")
        keys.append(f"sha256:{digest}")
    canonical_url = canonicalize_intake_source_url(source_url)
    if canonical_url:
        keys.append(f"source-url:{canonical_url}")
    path = normalize_intake_local_path(local_path)
    if path:
        keys.append(f"local-path:{path}")
    return tuple(dict.fromkeys(keys))


def build_intake_status_counts(decisions: Iterable[FileIntakeDecision]) -> dict[str, int]:
    counts = {
        FILE_INTAKE_STATUS_ADDED: 0,
        FILE_INTAKE_STATUS_REUSED: 0,
        FILE_INTAKE_STATUS_DUPLICATE: 0,
        FILE_INTAKE_STATUS_FAILED: 0,
        FILE_INTAKE_STATUS_SKIPPED: 0,
    }
    for decision in decisions:
        counts[decision.status] = counts.get(decision.status, 0) + 1
    return counts


def render_file_intake_dedupe_summary(plan: FileIntakeDedupePlan) -> str:
    """Return a compact operator-facing summary line."""

    return (
        f"FILES/media intake review: {plan.added_count} added, "
        f"{plan.reused_count} reused, {plan.duplicate_count} duplicate, "
        f"{plan.failed_count} failed"
    )


def _coerce_candidate(
    value: FileIntakeCandidate | Mapping[str, Any],
    *,
    enrich_hashes: bool,
) -> FileIntakeCandidate:
    if isinstance(value, FileIntakeCandidate):
        candidate = value
    elif isinstance(value, Mapping):
        candidate = file_intake_candidate_from_mapping(value)
    else:
        raise TypeError("candidate must be FileIntakeCandidate or mapping")
    if enrich_hashes:
        return candidate_with_file_hash(candidate)
    return candidate


def _coerce_existing(value: ExistingFileRecord | Mapping[str, Any]) -> ExistingFileRecord:
    if isinstance(value, ExistingFileRecord):
        return value
    if isinstance(value, Mapping):
        return existing_file_record_from_mapping(value)
    raise TypeError("existing record must be ExistingFileRecord or mapping")


def _coerce_non_negative_int(value: object) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _build_existing_identity_index(records: Iterable[ExistingFileRecord]) -> dict[str, ExistingFileRecord]:
    index: dict[str, ExistingFileRecord] = {}
    for record in records:
        for key in intake_identity_keys_for(
            source_url=record.source_url,
            local_path=record.local_path,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
        ):
            index.setdefault(key, record)
    return index


def _first_existing_match(
    identity_keys: Iterable[str],
    existing_index: Mapping[str, ExistingFileRecord],
) -> ExistingFileRecord | None:
    for key in identity_keys:
        record = existing_index.get(key)
        if record is not None:
            return record
    return None


def _first_seen_candidate_match(
    identity_keys: Iterable[str],
    seen_index: Mapping[str, FileIntakeCandidate],
) -> FileIntakeCandidate | None:
    for key in identity_keys:
        candidate = seen_index.get(key)
        if candidate is not None:
            return candidate
    return None


def _count_status(decisions: Iterable[FileIntakeDecision], status: str) -> int:
    return sum(1 for decision in decisions if decision.status == status)
