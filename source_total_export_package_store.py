from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_total_export_package_verifier import verify_source_total_export_package

SCHEMA_VERSION = "source_total_export_package_store_v1"


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


def store_source_total_export_package(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    package = outputs.get("total_export_package") if isinstance(outputs, Mapping) else None
    if not isinstance(package, Mapping):
        raise ValueError("outputs must include total_export_package object")
    package_id = _safe_id(package.get("total_export_package_id"), fallback="source.total_export_package")

    file_specs = [
        ("source_total_export_package", "source_total_export_package", package),
        ("source_total_export_manifest", "source_total_export_manifest", outputs.get("total_export_manifest")),
        ("source_total_export_evidence_queue_handoff", "source_total_export_evidence_queue_handoff", outputs.get("evidence_queue_handoff")),
        ("source_total_export_operator_summary", "source_total_export_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{package_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_total_export_package(package)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "total_export_package_id": package_id,
        "capture_bundle_id": str(package.get("capture_bundle_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
