from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from source_release_audit_verifier import verify_source_release_audit

SCHEMA_VERSION = "source_release_audit_store_v1"
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


def store_source_release_audit(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report = outputs.get("release_audit_report") if isinstance(outputs, Mapping) else None
    if not isinstance(report, Mapping):
        raise ValueError("outputs must include release_audit_report object")
    release_audit_id = _safe_id(report.get("release_audit_id"), fallback="source.release_audit")

    file_specs = [
        ("source_release_audit_report", "source_release_audit_report", report),
        ("source_release_traceability_map", "source_release_traceability_map", outputs.get("traceability_map")),
        ("source_release_archive_handoff", "source_release_archive_handoff", outputs.get("archive_handoff")),
        ("source_release_audit_operator_summary", "source_release_audit_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{release_audit_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_release_audit(
        report,
        outputs.get("traceability_map") if isinstance(outputs.get("traceability_map"), Mapping) else None,
        outputs.get("archive_handoff") if isinstance(outputs.get("archive_handoff"), Mapping) else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "release_audit_id": release_audit_id,
        "release_index_id": str(report.get("release_index_id") or ""),
        "approved_release_id": str(report.get("approved_release_id") or ""),
        "queue_item_id": str(report.get("queue_item_id") or ""),
        "adapter_id": str(report.get("adapter_id") or ""),
        "source_url": str(report.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
