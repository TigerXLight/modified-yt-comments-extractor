from __future__ import annotations

from typing import Iterable

from source_adapter_youtube_media_source_receipt_runtime import RUNTIME_STAGE, YoutubeMediaSourceReceiptRecord


def verify_record(record: YoutubeMediaSourceReceiptRecord) -> list[str]:
    issues: list[str] = []
    if not record.runtime_id.strip():
        issues.append("runtime_id is required")
    if record.stage != RUNTIME_STAGE:
        issues.append(f"unexpected stage: {record.stage}")
    if not record.status.strip():
        issues.append("status is required")
    if record.credential_policy != "redacted_reference_only":
        issues.append("credential policy must remain redacted_reference_only")
    if "secret" in " ".join(record.output_refs).lower():
        issues.append("output refs must not expose secret material")
    return issues


def verify_records(records: Iterable[YoutubeMediaSourceReceiptRecord]) -> list[str]:
    issues: list[str] = []
    for index, record in enumerate(records):
        for issue in verify_record(record):
            issues.append(f"record {index}: {issue}")
    return issues
