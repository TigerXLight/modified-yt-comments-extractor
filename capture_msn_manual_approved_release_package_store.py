from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_approved_release_package import (
    MSNManualApprovedReleasePackageReport,
    msn_manual_approved_release_package_to_json,
)

MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STORE_SCHEMA_VERSION = "msn_manual_approved_release_package_store_v1"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualApprovedReleasePackageStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualApprovedReleasePackageStoreReport:
    schema_version: str
    release_id: str
    queue_item_id: str
    handoff_id: str
    decision_id: str
    stored_files: list[MSNManualApprovedReleasePackageStoredFile] = field(default_factory=list)
    output_file_count: int = 0
    store_status: str = "STORED"


def _safe_stem(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._")
    return safe or "msn_manual_approved_release_package"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_bytes(path: Path, payload: dict[str, Any]) -> MSNManualApprovedReleasePackageStoredFile:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return MSNManualApprovedReleasePackageStoredFile(
        role=str(payload.get("file_role", path.stem)),
        filename=path.name,
        sha256=_hash_bytes(data),
        byte_count=len(data),
    )


def store_msn_manual_approved_release_package(
    release_package: MSNManualApprovedReleasePackageReport,
    output_dir: str | Path,
) -> MSNManualApprovedReleasePackageStoreReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(release_package.release_id)

    release_payload = json.loads(msn_manual_approved_release_package_to_json(release_package))
    release_payload["file_role"] = "approved_release_package"
    release_file = _write_json_bytes(directory / f"{stem}.approved_release_package.json", release_payload)

    manifest_payload = dict(release_package.total_export_release_manifest)
    manifest_payload.update(
        {
            "schema_version": MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STORE_SCHEMA_VERSION,
            "file_role": "approved_release_manifest",
            "release_hash": release_package.release_hash,
        }
    )
    manifest_file = _write_json_bytes(directory / f"{stem}.approved_release_manifest.json", manifest_payload)

    queue_payload = {
        "schema_version": MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STORE_SCHEMA_VERSION,
        "file_role": "approved_release_queue_update",
        "release_id": release_package.release_id,
        "queue_item_id": release_package.queue_item_id,
        "handoff_id": release_package.handoff_id,
        "decision_id": release_package.decision_id,
        "release_status": release_package.release_status,
        "ready_for_total_export_release": release_package.ready_for_total_export_release,
        "evidence_queue_update": release_package.evidence_queue_update,
        "release_hash": release_package.release_hash,
    }
    queue_file = _write_json_bytes(directory / f"{stem}.approved_release_queue_update.json", queue_payload)

    files = [release_file, manifest_file, queue_file]
    return MSNManualApprovedReleasePackageStoreReport(
        schema_version=MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STORE_SCHEMA_VERSION,
        release_id=release_package.release_id,
        queue_item_id=release_package.queue_item_id,
        handoff_id=release_package.handoff_id,
        decision_id=release_package.decision_id,
        stored_files=files,
        output_file_count=len(files),
    )


def msn_manual_approved_release_package_store_report_to_json(report: MSNManualApprovedReleasePackageStoreReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
