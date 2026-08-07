from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from capture_msn_manual_archive_result_intake import msn_manual_archive_result_intake_to_json

SCHEMA_VERSION = "msn_manual_archive_result_intake_store_v1"
STORE_STATUS_STORED = "STORED"
_SAFE_BASENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (_stable_json(value) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_base(value: str) -> str:
    cleaned = _SAFE_BASENAME_RE.sub("_", str(value or "").strip()).strip("._-")
    return cleaned[:180] or "msn_manual_archive_result_intake"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _json_bytes(payload)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": payload.get("file_role", "json_artifact"),
        "byte_count": len(data),
        "sha256": _sha256_bytes(data),
    }


def store_msn_manual_archive_result_intake(intake: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = _safe_base(str(intake.get("archive_result_intake_id") or intake.get("release_id") or "msn_manual_archive_result_intake"))

    intake_payload = dict(intake)
    intake_payload["file_role"] = "msn_manual_archive_result_intake"
    receipts_payload = {
        "schema_version": "msn_manual_archive_result_receipts_v1",
        "file_role": "msn_manual_archive_result_receipts",
        "archive_result_intake_id": intake.get("archive_result_intake_id"),
        "archive_handoff_id": intake.get("archive_handoff_id"),
        "queue_item_id": intake.get("queue_item_id"),
        "release_id": intake.get("release_id"),
        "receipts": list(intake.get("archive_result_receipts", []) or []),
    }
    queue_update_payload = dict(intake.get("archive_result_queue_update", {}) or {})
    queue_update_payload["file_role"] = "msn_manual_archive_result_queue_update"
    summary_payload = {
        "schema_version": "msn_manual_archive_result_operator_summary_v1",
        "file_role": "msn_manual_archive_result_operator_summary",
        "archive_result_intake_id": intake.get("archive_result_intake_id"),
        "queue_item_id": intake.get("queue_item_id"),
        "release_id": intake.get("release_id"),
        "archive_result_status": intake.get("archive_result_status"),
        "archive_result_summary": dict(intake.get("archive_result_summary", {}) or {}),
        "readiness_issues": list(intake.get("readiness_issues", []) or []),
    }

    stored_files = [
        _write_json(out / f"{base}.archive_result_intake.json", intake_payload),
        _write_json(out / f"{base}.archive_result_receipts.json", receipts_payload),
        _write_json(out / f"{base}.archive_result_queue_update.json", queue_update_payload),
        _write_json(out / f"{base}.archive_result_operator_summary.json", summary_payload),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS_STORED,
        "archive_result_intake_id": intake.get("archive_result_intake_id"),
        "archive_handoff_id": intake.get("archive_handoff_id"),
        "queue_item_id": intake.get("queue_item_id"),
        "release_id": intake.get("release_id"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


def store_msn_manual_archive_result_intake_json(intake: Mapping[str, Any], output_dir: str | Path) -> str:
    return msn_manual_archive_result_intake_to_json(store_msn_manual_archive_result_intake(intake, output_dir))


__all__ = ["SCHEMA_VERSION", "STORE_STATUS_STORED", "store_msn_manual_archive_result_intake", "store_msn_manual_archive_result_intake_json"]
