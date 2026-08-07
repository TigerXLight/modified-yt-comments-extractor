from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from source_archive_handoff_verifier import verify_source_archive_handoff

SCHEMA_VERSION = "source_archive_handoff_store_v1"
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _safe_id(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _write_json(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "filename": path.name,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_archive_handoff(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    package = outputs.get("archive_handoff_package") if isinstance(outputs, Mapping) else None
    if not isinstance(package, Mapping):
        raise ValueError("outputs must include archive_handoff_package object")
    archive_handoff_id = _safe_id(package.get("archive_handoff_id"), fallback="source.archive_handoff")

    file_specs = [
        ("source_archive_handoff_package", "source_archive_handoff_package", package),
        ("source_archive_provider_tasks", "source_archive_provider_tasks", outputs.get("provider_tasks")),
        ("source_archive_result_templates", "source_archive_result_templates", outputs.get("result_templates")),
        ("source_archive_result_intake_handoff", "source_archive_result_intake_handoff", outputs.get("result_intake_handoff")),
        ("source_archive_handoff_operator_summary", "source_archive_handoff_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{archive_handoff_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_archive_handoff(
        package,
        outputs.get("provider_tasks") if isinstance(outputs.get("provider_tasks"), Mapping) else None,
        outputs.get("result_templates") if isinstance(outputs.get("result_templates"), Mapping) else None,
        outputs.get("result_intake_handoff") if isinstance(outputs.get("result_intake_handoff"), Mapping) else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": str(package.get("release_audit_id") or ""),
        "release_index_id": str(package.get("release_index_id") or ""),
        "approved_release_id": str(package.get("approved_release_id") or ""),
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
