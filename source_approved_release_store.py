from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from source_approved_release_verifier import verify_source_approved_release

SCHEMA_VERSION = "source_approved_release_store_v1"
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


def store_source_approved_release(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    package = outputs.get("approved_release_package") if isinstance(outputs, Mapping) else None
    if not isinstance(package, Mapping):
        raise ValueError("outputs must include approved_release_package object")
    approved_release_id = _safe_id(package.get("approved_release_id"), fallback="source.approved_release")

    file_specs = [
        ("source_approved_release_package", "source_approved_release_package", package),
        ("source_approved_release_manifest", "source_approved_release_manifest", outputs.get("approved_release_manifest")),
        ("source_approved_release_index_handoff", "source_approved_release_index_handoff", outputs.get("release_index_handoff")),
        ("source_approved_release_operator_summary", "source_approved_release_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{approved_release_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_approved_release(
        package,
        outputs.get("approved_release_manifest") if isinstance(outputs.get("approved_release_manifest"), Mapping) else None,
        outputs.get("release_index_handoff") if isinstance(outputs.get("release_index_handoff"), Mapping) else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": str(package.get("evidence_review_package_id") or ""),
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "total_export_package_id": str(package.get("total_export_package_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
