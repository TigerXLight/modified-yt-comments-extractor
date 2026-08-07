from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_capture_bundle_verifier import verify_source_capture_bundle

SCHEMA_VERSION = "source_capture_bundle_store_v1"


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


def store_source_capture_bundle(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    bundle = outputs.get("capture_bundle") if isinstance(outputs, Mapping) else None
    if not isinstance(bundle, Mapping):
        raise ValueError("outputs must include capture_bundle object")
    capture_bundle_id = _safe_id(bundle.get("capture_bundle_id"), fallback="source.capture_bundle")

    file_specs = [
        ("source_capture_bundle", "source_capture_bundle", bundle),
        ("source_capture_manifest", "source_capture_manifest", outputs.get("capture_manifest")),
        ("source_capture_total_export_handoff", "source_capture_total_export_handoff", outputs.get("total_export_handoff")),
        ("source_capture_operator_summary", "source_capture_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{capture_bundle_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_capture_bundle(bundle)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": str(bundle.get("adapter_id") or ""),
        "source_url": str(bundle.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
