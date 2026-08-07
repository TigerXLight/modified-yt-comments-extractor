from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_evidence_queue_verifier import verify_source_evidence_queue

SCHEMA_VERSION = "source_evidence_queue_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _safe_id(value: object, *, fallback: str) -> str:
    text = str(value or "").strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "." for ch in text).strip("._-")
    return safe or fallback


def _write_json(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "filename": path.name,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_evidence_queue(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    item = outputs.get("evidence_queue_item") if isinstance(outputs, Mapping) else None
    if not isinstance(item, Mapping):
        raise ValueError("outputs must include evidence_queue_item object")
    queue_item_id = _safe_id(item.get("queue_item_id"), fallback="source.evidence_queue")

    file_specs = [
        ("source_evidence_queue_item", "source_evidence_queue_item", item),
        ("source_evidence_queue_index", "source_evidence_queue_index", outputs.get("evidence_queue_index")),
        ("source_evidence_review_handoff", "source_evidence_review_handoff", outputs.get("evidence_review_handoff")),
        ("source_evidence_queue_operator_summary", "source_evidence_queue_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{queue_item_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_evidence_queue(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "queue_item_id": queue_item_id,
        "total_export_package_id": str(item.get("total_export_package_id") or ""),
        "adapter_id": str(item.get("adapter_id") or ""),
        "source_url": str(item.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
