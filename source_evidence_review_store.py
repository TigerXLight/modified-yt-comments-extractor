from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_evidence_review_verifier import verify_source_evidence_review

SCHEMA_VERSION = "source_evidence_review_store_v1"


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


def store_source_evidence_review(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    package = outputs.get("evidence_review_package") if isinstance(outputs, Mapping) else None
    if not isinstance(package, Mapping):
        raise ValueError("outputs must include evidence_review_package object")
    review_package_id = _safe_id(package.get("evidence_review_package_id"), fallback="source.evidence_review")

    file_specs = [
        ("source_evidence_review_package", "source_evidence_review_package", package),
        ("source_evidence_review_checklist", "source_evidence_review_checklist", outputs.get("evidence_review_checklist")),
        ("source_evidence_review_decision", "source_evidence_review_decision", outputs.get("evidence_review_decision")),
        ("source_evidence_review_release_handoff", "source_evidence_review_release_handoff", outputs.get("release_handoff")),
        ("source_evidence_review_operator_summary", "source_evidence_review_operator_summary", outputs.get("operator_summary")),
    ]

    stored_files: list[dict[str, Any]] = []
    for suffix, role, data in file_specs:
        if not isinstance(data, Mapping):
            raise ValueError(f"outputs must include {suffix} object")
        path = output_path / f"{review_package_id}.{suffix}.json"
        receipt = _write_json(path, data)
        receipt["role"] = role
        stored_files.append(receipt)

    verification = verify_source_evidence_review(
        package,
        outputs.get("evidence_review_decision") if isinstance(outputs.get("evidence_review_decision"), Mapping) else None,
        outputs.get("release_handoff") if isinstance(outputs.get("release_handoff"), Mapping) else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "evidence_review_package_id": review_package_id,
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "total_export_package_id": str(package.get("total_export_package_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
