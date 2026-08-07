from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from source_release_index_verifier import verify_source_release_index

SCHEMA_VERSION = "source_release_index_store_v1"
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


def store_source_release_index(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    record = outputs.get("release_index_record") if isinstance(outputs, Mapping) else None
    if not isinstance(record, Mapping):
        raise ValueError("outputs must include release_index_record object")
    release_index_id = _safe_id(record.get("release_index_id"), fallback="source.release_index")

    file_specs = [
        ("source_release_index_record", "source_release_index_record", record),
        ("source_release_inventory", "source_release_inventory", outputs.get("release_inventory")),
        ("source_release_export_bundle_handoff", "source_release_export_bundle_handoff", outputs.get("export_bundle_handoff")),
        ("source_release_index_operator_summary", "source_release_index_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{release_index_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_release_index(
        record,
        outputs.get("release_inventory") if isinstance(outputs.get("release_inventory"), Mapping) else None,
        outputs.get("export_bundle_handoff") if isinstance(outputs.get("export_bundle_handoff"), Mapping) else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "release_index_id": release_index_id,
        "approved_release_id": str(record.get("approved_release_id") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "adapter_id": str(record.get("adapter_id") or ""),
        "source_url": str(record.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
