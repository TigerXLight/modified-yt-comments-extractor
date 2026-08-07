from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_approved_export_handoff import (
    MSNManualApprovedExportHandoffReport,
    msn_manual_approved_export_handoff_to_json,
)

MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STORE_SCHEMA_VERSION = "msn_manual_approved_export_handoff_store_v1"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualApprovedExportHandoffStoreReport:
    schema_version: str
    handoff_id: str
    queue_item_id: str
    decision_id: str
    stored_files: list[MSNManualApprovedExportHandoffStoredFile] = field(default_factory=list)
    output_file_count: int = 0
    store_status: str = "STORED"


def _safe_stem(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._")
    return safe or "msn_manual_approved_export_handoff"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_bytes(path: Path, payload: dict[str, Any]) -> MSNManualApprovedExportHandoffStoredFile:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return MSNManualApprovedExportHandoffStoredFile(
        role=str(payload.get("file_role", path.stem)),
        filename=path.name,
        sha256=_hash_bytes(data),
        byte_count=len(data),
    )


def store_msn_manual_approved_export_handoff(
    handoff: MSNManualApprovedExportHandoffReport,
    output_dir: str | Path,
) -> MSNManualApprovedExportHandoffStoreReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(handoff.handoff_id)

    handoff_payload = json.loads(msn_manual_approved_export_handoff_to_json(handoff))
    handoff_payload["file_role"] = "approved_export_handoff"
    handoff_file = _write_json_bytes(directory / f"{stem}.approved_export_handoff.json", handoff_payload)

    queue_payload = {
        "schema_version": MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STORE_SCHEMA_VERSION,
        "file_role": "approved_export_queue_update",
        "handoff_id": handoff.handoff_id,
        "queue_item_id": handoff.queue_item_id,
        "decision_id": handoff.decision_id,
        "handoff_status": handoff.handoff_status,
        "ready_for_total_export_release": handoff.ready_for_total_export_release,
        "evidence_queue_update": handoff.evidence_queue_update,
        "total_export_handoff": handoff.total_export_handoff,
        "handoff_hash": handoff.handoff_hash,
    }
    queue_file = _write_json_bytes(directory / f"{stem}.approved_export_queue_update.json", queue_payload)

    files = [handoff_file, queue_file]
    return MSNManualApprovedExportHandoffStoreReport(
        schema_version=MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STORE_SCHEMA_VERSION,
        handoff_id=handoff.handoff_id,
        queue_item_id=handoff.queue_item_id,
        decision_id=handoff.decision_id,
        stored_files=files,
        output_file_count=len(files),
    )


def msn_manual_approved_export_handoff_store_report_to_json(report: MSNManualApprovedExportHandoffStoreReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
