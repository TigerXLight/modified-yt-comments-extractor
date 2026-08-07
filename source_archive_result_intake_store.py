from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_archive_result_intake_verifier import verify_source_archive_result_intake

STORE_SCHEMA_VERSION = "source_archive_result_intake_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "role": str(data.get("store_role") or data.get("role") or path.stem),
        "filename": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
    }


def store_source_archive_result_intake(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    record = dict(outputs.get("archive_result_intake_record") or {})
    receipt_index = dict(outputs.get("archive_receipt_index") or {})
    review_handoff = dict(outputs.get("archive_review_handoff") or {})
    summary = dict(outputs.get("operator_summary") or {})

    verification = verify_source_archive_result_intake(record, receipt_index, review_handoff)
    if not verification.get("verified"):
        raise ValueError("source archive result intake verification failed: " + "; ".join(verification.get("issues", [])))

    archive_result_intake_id = str(record.get("archive_result_intake_id") or "source.archive_result_intake")
    files = [
        ("source_archive_result_intake_record", f"{archive_result_intake_id}.source_archive_result_intake_record.json", record),
        ("source_archive_receipt_index", f"{archive_result_intake_id}.source_archive_receipt_index.json", receipt_index),
        ("source_archive_review_handoff", f"{archive_result_intake_id}.source_archive_review_handoff.json", review_handoff),
        ("source_archive_result_intake_operator_summary", f"{archive_result_intake_id}.source_archive_result_intake_operator_summary.json", summary),
    ]

    stored_files: list[dict[str, Any]] = []
    for role, filename, data in files:
        data = dict(data)
        data["store_role"] = role
        stored_files.append(_write_json(directory / filename, data))

    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "archive_result_intake_id": archive_result_intake_id,
        "archive_handoff_id": str(record.get("archive_handoff_id") or ""),
        "release_audit_id": str(record.get("release_audit_id") or ""),
        "release_index_id": str(record.get("release_index_id") or ""),
        "approved_release_id": str(record.get("approved_release_id") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "adapter_id": str(record.get("adapter_id") or ""),
        "source_url": str(record.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
