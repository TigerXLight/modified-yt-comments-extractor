from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_release_section_closeout import (
    MSNManualReleaseSectionCloseoutReport,
    msn_manual_release_section_closeout_to_json,
)

MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STORE_SCHEMA_VERSION = "msn_manual_release_section_closeout_store_v1"


@dataclass(frozen=True)
class MSNManualReleaseSectionCloseoutStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualReleaseSectionCloseoutStoreReport:
    schema_version: str
    store_status: str
    closeout_id: str
    export_bundle_id: str
    release_id: str
    queue_item_id: str
    output_file_count: int
    stored_files: list[MSNManualReleaseSectionCloseoutStoredFile] = field(default_factory=list)


class MSNManualReleaseSectionCloseoutStoreError(ValueError):
    pass


def _write_json(path: Path, role: str, payload: dict[str, Any]) -> MSNManualReleaseSectionCloseoutStoredFile:
    tagged = dict(payload)
    tagged["_store_role"] = role
    encoded = json.dumps(tagged, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(encoded)
    return MSNManualReleaseSectionCloseoutStoredFile(
        role=role,
        filename=path.name,
        sha256=hashlib.sha256(encoded).hexdigest(),
        byte_count=len(encoded),
    )


def store_msn_manual_release_section_closeout(
    report: MSNManualReleaseSectionCloseoutReport,
    output_dir: str | Path,
) -> MSNManualReleaseSectionCloseoutStoreReport:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    base = report.closeout_id
    closeout_payload = msn_manual_release_section_closeout_to_json(report)
    release_record_payload = dict(report.total_export_release_record)
    queue_update_payload = dict(report.evidence_queue_closeout_update)
    checklist_payload = dict(report.final_release_checklist)
    stored = [
        _write_json(target / f"{base}.release_section_closeout.json", "msn_manual_release_section_closeout", closeout_payload),
        _write_json(target / f"{base}.total_export_release_record.json", "msn_manual_total_export_release_record", release_record_payload),
        _write_json(target / f"{base}.release_closeout_queue_update.json", "msn_manual_release_closeout_queue_update", queue_update_payload),
        _write_json(target / f"{base}.release_closeout_checklist.json", "msn_manual_release_closeout_checklist", checklist_payload),
    ]
    return MSNManualReleaseSectionCloseoutStoreReport(
        schema_version=MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STORE_SCHEMA_VERSION,
        store_status="STORED",
        closeout_id=report.closeout_id,
        export_bundle_id=report.export_bundle_id,
        release_id=report.release_id,
        queue_item_id=report.queue_item_id,
        output_file_count=len(stored),
        stored_files=stored,
    )


def msn_manual_release_section_closeout_store_report_to_json(report: MSNManualReleaseSectionCloseoutStoreReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "store_status": report.store_status,
        "closeout_id": report.closeout_id,
        "export_bundle_id": report.export_bundle_id,
        "release_id": report.release_id,
        "queue_item_id": report.queue_item_id,
        "output_file_count": report.output_file_count,
        "stored_files": [file.__dict__ for file in report.stored_files],
    }
