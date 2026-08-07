from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "msn_manual_archive_review_package_store_v1"
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
    return cleaned[:180] or "msn_manual_archive_review_package"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _json_bytes(payload)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": payload.get("file_role", "json_artifact"),
        "byte_count": len(data),
        "sha256": _sha256_bytes(data),
    }


def store_msn_manual_archive_review_package(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = _safe_base(str(package.get("archive_review_package_id") or package.get("release_id") or "msn_manual_archive_review_package"))

    package_payload = dict(package)
    package_payload["file_role"] = "msn_manual_archive_review_package"
    receipt_index_payload = dict(package.get("archive_receipt_index") or {})
    receipt_index_payload["file_role"] = "msn_manual_archive_receipt_index"
    queue_update_payload = dict(package.get("archive_review_queue_update") or {})
    queue_update_payload["file_role"] = "msn_manual_archive_review_queue_update"
    review_todo_payload = {
        "schema_version": "msn_manual_archive_review_todo_v1",
        "file_role": "msn_manual_archive_review_todo",
        "archive_review_package_id": package.get("archive_review_package_id"),
        "queue_item_id": package.get("queue_item_id"),
        "release_id": package.get("release_id"),
        "required_review_actions": list(package.get("required_review_actions", []) or []),
        "next_boundary": package.get("next_boundary"),
    }

    stored_files = [
        _write_json(out / f"{base}.archive_review_package.json", package_payload),
        _write_json(out / f"{base}.archive_receipt_index.json", receipt_index_payload),
        _write_json(out / f"{base}.archive_review_queue_update.json", queue_update_payload),
        _write_json(out / f"{base}.archive_review_todo.json", review_todo_payload),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS_STORED,
        "archive_review_package_id": package.get("archive_review_package_id"),
        "archive_result_intake_id": package.get("archive_result_intake_id"),
        "queue_item_id": package.get("queue_item_id"),
        "release_id": package.get("release_id"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


__all__ = ["SCHEMA_VERSION", "STORE_STATUS_STORED", "store_msn_manual_archive_review_package"]
