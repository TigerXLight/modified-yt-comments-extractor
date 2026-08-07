from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_release_audit_bridge import output_documents
from source_adapter_release_audit_bridge_verifier import verify_source_adapter_release_audit_bridge

SCHEMA_VERSION = "source_adapter_release_audit_bridge_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, data: Any) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "filename": path.name,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_adapter_release_audit_bridge(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    bridge_id = str(package.get("source_adapter_release_audit_bridge_id") or "").strip()
    if not bridge_id:
        raise ValueError("source_adapter_release_audit_bridge_id is required")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    documents = output_documents(package)
    stored_files: list[dict[str, Any]] = []
    for role, data in documents.items():
        receipt = _write_json(output_path / f"{bridge_id}.{role}.json", data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_adapter_release_audit_bridge(package)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_release_audit_bridge_id": bridge_id,
        "source_adapter_release_index_bridge_id": str(package.get("source_adapter_release_index_bridge_id") or ""),
        "release_audit_bridge_status": package.get("release_audit_bridge_status"),
        "release_audit_count": package.get("release_audit_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
