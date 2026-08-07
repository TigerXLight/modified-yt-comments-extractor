from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from capture_msn_manual_archive_handoff import msn_manual_archive_handoff_to_json

SCHEMA_VERSION = "msn_manual_archive_handoff_store_v1"
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
    return cleaned[:180] or "msn_manual_archive_handoff"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _json_bytes(payload)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": payload.get("file_role", "json_artifact"),
        "byte_count": len(data),
        "sha256": _sha256_bytes(data),
    }


def store_msn_manual_archive_handoff(handoff: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = _safe_base(str(handoff.get("archive_handoff_id") or handoff.get("release_id") or "msn_manual_archive_handoff"))

    handoff_payload = dict(handoff)
    handoff_payload["file_role"] = "msn_manual_archive_handoff"
    task_list_payload = {
        "schema_version": "msn_manual_archive_task_list_v1",
        "file_role": "msn_manual_archive_task_list",
        "archive_handoff_id": handoff.get("archive_handoff_id"),
        "queue_item_id": handoff.get("queue_item_id"),
        "release_id": handoff.get("release_id"),
        "tasks": list(handoff.get("archive_tasks", []) or []),
    }
    template_payload = {
        "schema_version": "msn_manual_archive_result_template_v1",
        "file_role": "msn_manual_archive_result_template",
        "archive_handoff_id": handoff.get("archive_handoff_id"),
        "queue_item_id": handoff.get("queue_item_id"),
        "release_id": handoff.get("release_id"),
        "result_template": list(handoff.get("archive_result_template", []) or []),
        "result_intake_status": "PENDING_OPERATOR_RESULTS",
    }

    stored_files = [
        _write_json(out / f"{base}.archive_handoff.json", handoff_payload),
        _write_json(out / f"{base}.archive_task_list.json", task_list_payload),
        _write_json(out / f"{base}.archive_result_template.json", template_payload),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS_STORED,
        "archive_handoff_id": handoff.get("archive_handoff_id"),
        "queue_item_id": handoff.get("queue_item_id"),
        "release_id": handoff.get("release_id"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


def store_msn_manual_archive_handoff_json(handoff: Mapping[str, Any], output_dir: str | Path) -> str:
    return msn_manual_archive_handoff_to_json(store_msn_manual_archive_handoff(handoff, output_dir))


__all__ = ["SCHEMA_VERSION", "STORE_STATUS_STORED", "store_msn_manual_archive_handoff", "store_msn_manual_archive_handoff_json"]
