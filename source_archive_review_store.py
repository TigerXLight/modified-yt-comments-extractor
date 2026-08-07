from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_archive_review_verifier import verify_source_archive_review

SCHEMA_VERSION = "source_archive_review_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "filename": path.name,
        "role": str(data.get("artifact_role") or path.stem.split(".")[-1]),
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_archive_review(outputs: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package = dict(outputs["archive_review_package"])
    checklist = dict(outputs["archive_review_checklist"])
    decision = dict(outputs["archive_review_decision"])
    closeout = dict(outputs["archive_review_closeout"])
    summary = dict(outputs["operator_summary"])

    verification = verify_source_archive_review(package, checklist, decision, closeout)
    if not verification["verified"]:
        raise ValueError("source archive review verification failed: " + "; ".join(verification["issues"]))

    archive_review_package_id = str(package["archive_review_package_id"])
    artifacts = [
        ("source_archive_review_package", package),
        ("source_archive_review_checklist", checklist),
        ("source_archive_review_decision", decision),
        ("source_archive_review_closeout", closeout),
        ("source_archive_review_operator_summary", summary),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, document in artifacts:
        document["artifact_role"] = role
        stored_files.append(_write_json(output_dir / f"{archive_review_package_id}.{role}.json", document))

    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "approved_release_id": str(package.get("approved_release_id") or ""),
        "release_audit_id": str(package.get("release_audit_id") or ""),
        "archive_handoff_id": str(package.get("archive_handoff_id") or ""),
        "archive_result_intake_id": str(package.get("archive_result_intake_id") or ""),
        "archive_review_package_id": archive_review_package_id,
        "decision": str(package.get("decision") or ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
