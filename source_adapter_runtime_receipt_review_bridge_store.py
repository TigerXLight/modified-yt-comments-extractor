from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_receipt_review_bridge import output_documents
from source_adapter_runtime_receipt_review_bridge_verifier import verify_source_adapter_runtime_receipt_review_bridge

SCHEMA_VERSION = "source_adapter_runtime_receipt_review_bridge_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_runtime_receipt_review_bridge(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    docs = output_documents(package)
    bridge_id = str(package.get("source_adapter_runtime_receipt_review_bridge_id") or "source_adapter_runtime_receipt_review_bridge")
    stored_files = []
    for role, document in docs.items():
        receipt = _write_json(out / f"{bridge_id}.{role}.json", document)
        receipt["role"] = role
        stored_files.append(receipt)
    verification = verify_source_adapter_runtime_receipt_review_bridge(package)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_receipt_review_bridge_id": bridge_id,
        "source_adapter_runtime_wiring_bridge_id": str(package.get("source_adapter_runtime_wiring_bridge_id") or ""),
        "runtime_receipt_review_status": str(package.get("runtime_receipt_review_status") or ""),
        "runtime_receipt_review_count": int(package.get("runtime_receipt_review_count") or 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
