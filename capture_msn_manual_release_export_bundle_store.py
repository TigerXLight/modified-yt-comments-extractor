from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_release_export_bundle import (
    MSNManualReleaseExportBundleReport,
    msn_manual_release_export_bundle_to_json,
)

MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STORE_SCHEMA_VERSION = "msn_manual_release_export_bundle_store_v1"


@dataclass(frozen=True)
class MSNManualReleaseExportStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualReleaseExportBundleStoreReport:
    schema_version: str
    store_status: str
    export_bundle_id: str
    index_id: str
    release_id: str
    queue_item_id: str
    output_file_count: int
    stored_files: list[MSNManualReleaseExportStoredFile] = field(default_factory=list)


class MSNManualReleaseExportBundleStoreError(ValueError):
    pass


def _write_json(path: Path, payload: dict[str, Any]) -> MSNManualReleaseExportStoredFile:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(encoded)
    return MSNManualReleaseExportStoredFile(
        role=str(payload.get("_store_role", "release_export_payload")),
        filename=path.name,
        sha256=hashlib.sha256(encoded).hexdigest(),
        byte_count=len(encoded),
    )


def store_msn_manual_release_export_bundle(
    report: MSNManualReleaseExportBundleReport,
    output_dir: str | Path,
) -> MSNManualReleaseExportBundleStoreReport:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    base = report.export_bundle_id
    bundle_payload = msn_manual_release_export_bundle_to_json(report)
    manifest_payload = dict(report.total_export_handoff_manifest)
    queue_update_payload = dict(report.evidence_queue_final_update)
    bundle_payload["_store_role"] = "msn_manual_release_export_bundle"
    manifest_payload["_store_role"] = "msn_manual_release_export_manifest"
    queue_update_payload["_store_role"] = "msn_manual_release_export_queue_update"
    stored = [
        _write_json(target / f"{base}.release_export_bundle.json", bundle_payload),
        _write_json(target / f"{base}.release_export_manifest.json", manifest_payload),
        _write_json(target / f"{base}.release_export_queue_update.json", queue_update_payload),
    ]
    return MSNManualReleaseExportBundleStoreReport(
        schema_version=MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STORE_SCHEMA_VERSION,
        store_status="STORED",
        export_bundle_id=report.export_bundle_id,
        index_id=report.index_id,
        release_id=report.release_id,
        queue_item_id=report.queue_item_id,
        output_file_count=len(stored),
        stored_files=stored,
    )


def msn_manual_release_export_bundle_store_report_to_json(report: MSNManualReleaseExportBundleStoreReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "store_status": report.store_status,
        "export_bundle_id": report.export_bundle_id,
        "index_id": report.index_id,
        "release_id": report.release_id,
        "queue_item_id": report.queue_item_id,
        "output_file_count": report.output_file_count,
        "stored_files": [file.__dict__ for file in report.stored_files],
    }
