from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_approved_release_bridge import output_documents
from source_adapter_approved_release_bridge_verifier import verify_source_adapter_approved_release_bridge

STORE_SCHEMA_VERSION = "source_adapter_approved_release_bridge_store_v1"
_ROLE_SUFFIXES = {
    "source_adapter_approved_release_bridge_package": "source_adapter_approved_release_bridge_package.json",
    "source_adapter_approved_release_output_batch": "source_adapter_approved_release_output_batch.json",
    "source_adapter_approved_release_batch": "source_adapter_approved_release_batch.json",
    "source_adapter_release_index_batch_handoff": "source_adapter_release_index_batch_handoff.json",
    "source_adapter_approved_release_bridge_operator_summary": "source_adapter_approved_release_bridge_operator_summary.json",
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_source_adapter_approved_release_bridge(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bridge_id = str(package.get("source_adapter_approved_release_bridge_id") or "source_adapter_approved_release_bridge")
    stored_files: list[dict[str, Any]] = []
    for role, document in output_documents(package).items():
        filename = f"{bridge_id}.{_ROLE_SUFFIXES[role]}"
        data = _json_bytes(document)
        (out / filename).write_bytes(data)
        stored_files.append({"role": role, "filename": filename, "byte_count": len(data), "sha256": _sha256(data)})
    verification = verify_source_adapter_approved_release_bridge(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_approved_release_bridge_id": bridge_id,
        "source_adapter_evidence_review_bridge_id": package.get("source_adapter_evidence_review_bridge_id", ""),
        "approved_release_count": package.get("approved_release_count", 0),
        "approved_release_bridge_status": package.get("approved_release_bridge_status", ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
