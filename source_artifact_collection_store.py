from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_artifact_collection_verifier import verify_source_artifact_collection

SCHEMA_VERSION = "source_artifact_collection_store_v1"


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _json_bytes(payload)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": str(payload.get("file_role") or payload.get("role") or path.stem),
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_artifact_collection(collection: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    collection_id = str(collection.get("collection_id") or "source_artifacts.unknown")
    safe_id = collection_id.replace("/", "_").replace("\\", "_")
    verification = verify_source_artifact_collection(collection)
    artifact_ledger = {
        "schema_version": "source_artifact_collection_ledger_v1",
        "file_role": "source_artifact_collection_ledger",
        "collection_id": collection_id,
        "adapter_id": collection.get("adapter_id", ""),
        "source_url": collection.get("source_url", ""),
        "artifacts": list(collection.get("artifacts") or []),
        "artifact_count": collection.get("artifact_count", 0),
    }
    extraction_handoff = {
        "schema_version": "source_artifact_extraction_handoff_v1",
        "file_role": "source_artifact_extraction_handoff",
        "collection_id": collection_id,
        "adapter_id": collection.get("adapter_id", ""),
        "source_url": collection.get("source_url", ""),
        "status": collection.get("collection_status", ""),
        "next_stage": "source_content_extraction",
        "eligible_for_extraction": verification["verified"] and collection.get("collection_status") == "READY_FOR_EXTRACTION",
    }
    stored_files = [
        _write_json(output_dir / f"{safe_id}.artifact_collection.json", {"file_role": "source_artifact_collection", **dict(collection)}),
        _write_json(output_dir / f"{safe_id}.artifact_ledger.json", artifact_ledger),
        _write_json(output_dir / f"{safe_id}.extraction_handoff.json", extraction_handoff),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "collection_id": collection_id,
        "adapter_id": collection.get("adapter_id", ""),
        "artifact_count": collection.get("artifact_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }


__all__ = ["store_source_artifact_collection"]
