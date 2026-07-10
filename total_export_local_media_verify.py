from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from total_export_local_media import LocalMediaRecord, sha256_file


LOCAL_MEDIA_VERIFY_STATUS_VERIFIED = "verified"
LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE = "missing_local_file"
LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH = "size_mismatch"
LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH = "sha256_mismatch"
LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW = "needs_review"
LOCAL_MEDIA_VERIFY_STATUS_NOT_CHECKED = "not_checked"


@dataclass(frozen=True)
class LocalMediaVerificationItem:
    source_url: str = ""
    normalized_url: str = ""
    package_id: str = ""
    local_media_path: str = ""
    recorded_exists_at_registration: bool = False
    current_exists: bool = False
    recorded_size_bytes: int = 0
    current_size_bytes: int = 0
    recorded_sha256: str = ""
    current_sha256: str = ""
    size_matches: bool = False
    sha256_matches: bool = False
    media_type: str = ""
    status: str = LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW
    warnings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        data["recommended_actions"] = list(self.recommended_actions)
        return data


@dataclass(frozen=True)
class LocalMediaVerificationResult:
    record_count: int = 0
    checked_count: int = 0
    missing_count: int = 0
    size_mismatch_count: int = 0
    sha256_mismatch_count: int = 0
    items: tuple[LocalMediaVerificationItem, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_count": self.checked_count,
            "errors": list(self.errors),
            "items": [item.to_dict() for item in self.items],
            "missing_count": self.missing_count,
            "record_count": self.record_count,
            "sha256_mismatch_count": self.sha256_mismatch_count,
            "size_mismatch_count": self.size_mismatch_count,
            "warnings": list(self.warnings),
        }


def _clean_string(value: object) -> str:
    return str(value or "").strip()


def _clean_sha256(value: object) -> str:
    return _clean_string(value).casefold()


def _unique_preserving_order(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = _clean_string(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return tuple(output)


def verify_local_media_record(
    record: LocalMediaRecord,
    *,
    compute_hash: bool = True,
) -> LocalMediaVerificationItem:
    warnings: list[str] = []
    recommended_actions: list[str] = []
    local_path = _clean_string(record.local_media_path)
    recorded_size = int(record.local_file_size_bytes or 0)
    recorded_sha256 = _clean_sha256(record.local_file_sha256)
    current_exists = False
    current_size = 0
    current_sha256 = ""
    size_matches = False
    sha256_matches = False
    status = LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW

    if not local_path:
        warnings.append("Local media path is empty; no local file check was performed.")
        recommended_actions.append("Add a local media path before verifying this record.")
        status = LOCAL_MEDIA_VERIFY_STATUS_NOT_CHECKED
        return LocalMediaVerificationItem(
            source_url=record.source_url,
            normalized_url=record.normalized_url,
            package_id=record.package_id,
            local_media_path=local_path,
            recorded_exists_at_registration=record.exists_at_registration,
            current_exists=False,
            recorded_size_bytes=recorded_size,
            current_size_bytes=0,
            recorded_sha256=recorded_sha256,
            current_sha256="",
            size_matches=False,
            sha256_matches=False,
            media_type=record.media_type,
            status=status,
            warnings=_unique_preserving_order(warnings),
            recommended_actions=_unique_preserving_order(recommended_actions),
        )

    path = Path(local_path)
    current_exists = path.is_file()
    if not current_exists:
        warnings.append("Local media file was not found at verification time.")
        recommended_actions.append("Re-check the local media path or re-register the file location.")
        status = LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE
        return LocalMediaVerificationItem(
            source_url=record.source_url,
            normalized_url=record.normalized_url,
            package_id=record.package_id,
            local_media_path=local_path,
            recorded_exists_at_registration=record.exists_at_registration,
            current_exists=False,
            recorded_size_bytes=recorded_size,
            current_size_bytes=0,
            recorded_sha256=recorded_sha256,
            current_sha256="",
            size_matches=False,
            sha256_matches=False,
            media_type=record.media_type,
            status=status,
            warnings=_unique_preserving_order(warnings),
            recommended_actions=_unique_preserving_order(recommended_actions),
        )

    current_size = path.stat().st_size
    if recorded_size > 0:
        size_matches = current_size == recorded_size
        if not size_matches:
            warnings.append("Current file size does not match the recorded size.")
            recommended_actions.append("Review whether the local file was replaced or edited.")
    else:
        warnings.append("Recorded file size is blank or zero; size comparison was not checked.")
        recommended_actions.append("Record a known file size if this media should be verified later.")

    if compute_hash:
        current_sha256 = sha256_file(local_path)
        if recorded_sha256:
            sha256_matches = current_sha256 == recorded_sha256
            if not sha256_matches:
                warnings.append("Current SHA-256 does not match the recorded SHA-256.")
                recommended_actions.append("Review whether the local file was replaced or edited.")
        else:
            warnings.append("Recorded SHA-256 is blank; hash comparison was not checked.")
            recommended_actions.append("Record a SHA-256 if this media should be verified later.")
    else:
        warnings.append("SHA-256 was not computed for this verification run.")
        recommended_actions.append("Run verification with compute_hash=True for stronger local identity checking.")

    if recorded_size > 0 and not size_matches:
        status = LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH
    elif compute_hash and recorded_sha256 and not sha256_matches:
        status = LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH
    elif recorded_size > 0 and size_matches and compute_hash and recorded_sha256 and sha256_matches:
        status = LOCAL_MEDIA_VERIFY_STATUS_VERIFIED
    else:
        status = LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW

    return LocalMediaVerificationItem(
        source_url=record.source_url,
        normalized_url=record.normalized_url,
        package_id=record.package_id,
        local_media_path=local_path,
        recorded_exists_at_registration=record.exists_at_registration,
        current_exists=current_exists,
        recorded_size_bytes=recorded_size,
        current_size_bytes=current_size,
        recorded_sha256=recorded_sha256,
        current_sha256=current_sha256,
        size_matches=size_matches,
        sha256_matches=sha256_matches,
        media_type=record.media_type,
        status=status,
        warnings=_unique_preserving_order(warnings),
        recommended_actions=_unique_preserving_order(recommended_actions),
    )


def verify_local_media_records(
    records: Sequence[LocalMediaRecord],
    *,
    compute_hash: bool = True,
) -> LocalMediaVerificationResult:
    items = tuple(
        verify_local_media_record(record, compute_hash=compute_hash)
        for record in records
    )
    warnings: list[str] = [
        "Local media verification checks only user-supplied local file paths; it does not download, fetch, probe, transcribe, archive, scrape, or call network services."
    ]
    if not compute_hash:
        warnings.append("Hash computation was disabled; SHA-256 comparisons were not performed.")

    return LocalMediaVerificationResult(
        record_count=len(records),
        checked_count=sum(
            1 for item in items if item.status != LOCAL_MEDIA_VERIFY_STATUS_NOT_CHECKED
        ),
        missing_count=sum(
            1 for item in items if item.status == LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE
        ),
        size_mismatch_count=sum(
            1 for item in items if item.status == LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH
        ),
        sha256_mismatch_count=sum(
            1 for item in items if item.status == LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH
        ),
        items=items,
        warnings=tuple(warnings),
        errors=(),
    )


def local_media_verification_result_to_dict(
    result: LocalMediaVerificationResult,
) -> dict[str, object]:
    return result.to_dict()


def _display_value(value: object) -> str:
    if value is None or value == "":
        return "(none)"
    return str(value)


def build_local_media_verification_text(
    result: LocalMediaVerificationResult,
) -> str:
    lines = [
        "Local media verification report",
        "Scope: local filesystem verification only; no downloads, fetching, media probing, transcription, archive checks, scraping, browser automation, or network calls are performed.",
        f"Record count: {result.record_count}",
        f"Checked count: {result.checked_count}",
        f"Missing local files: {result.missing_count}",
        f"Size mismatches: {result.size_mismatch_count}",
        f"SHA-256 mismatches: {result.sha256_mismatch_count}",
    ]
    if not result.items:
        lines.append("- (none)")
    for item in result.items:
        lines.append(
            f"- File: {_display_value(item.local_media_path)} "
            f"[status={item.status}; current_exists={item.current_exists}; "
            f"recorded_size={item.recorded_size_bytes}; current_size={item.current_size_bytes}]"
        )
        if item.recorded_sha256 or item.current_sha256:
            lines.append(
                f"  SHA-256: recorded={_display_value(item.recorded_sha256)}; "
                f"current={_display_value(item.current_sha256)}"
            )
        for warning in item.warnings:
            lines.append(f"  Warning: {warning}")
        for action in item.recommended_actions:
            lines.append(f"  Recommended action: {action}")
    if result.warnings:
        lines.append("Safety notes:")
        for warning in result.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def _markdown_cell(value: object) -> str:
    return _display_value(value).replace("|", "\\|")


def build_local_media_verification_markdown(
    result: LocalMediaVerificationResult,
) -> str:
    lines = [
        "# Local Media Verification Report",
        "",
        "Local filesystem verification only. This report does not download, fetch, probe media, transcribe, archive-check, scrape, use browser automation, or call network services.",
        "",
        f"- Record count: {result.record_count}",
        f"- Checked count: {result.checked_count}",
        f"- Missing local files: {result.missing_count}",
        f"- Size mismatches: {result.size_mismatch_count}",
        f"- SHA-256 mismatches: {result.sha256_mismatch_count}",
        "",
        "| Local path | Status | Current exists | Recorded size | Current size | Size match | SHA-256 match | Warnings |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for item in result.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(item.local_media_path),
                    item.status,
                    "yes" if item.current_exists else "no",
                    str(item.recorded_size_bytes),
                    str(item.current_size_bytes),
                    "yes" if item.size_matches else "no",
                    "yes" if item.sha256_matches else "no",
                    _markdown_cell("; ".join(item.warnings)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Verification describes current local filesystem state only.",
            "- Missing local files are local notes, not proof that a remote source is unavailable.",
            "- Blank recorded size or SHA-256 values require review; they are not treated as mismatches.",
            "- No downloading, archive checking, scraping, transcription, media probing, browser automation, or network/API behavior is performed.",
        ]
    )
    return "\n".join(lines)
