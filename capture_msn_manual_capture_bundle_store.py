from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_msn_manual_capture_bundle import MSNManualCaptureBundle, msn_manual_capture_bundle_to_json


MSN_MANUAL_CAPTURE_BUNDLE_STORE_SCHEMA_VERSION = "msn_manual_capture_bundle_store_v1"
_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class MSNManualCaptureBundleStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualCaptureBundleStoreResult:
    schema_version: str
    files: tuple[MSNManualCaptureBundleStoredFile, ...]
    metadata_only_store_result: bool = True
    full_local_path_serialized: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "files": [file.to_dict() for file in self.files], "metadata_only_store_result": True, "full_local_path_serialized": False, "file_movement_performed_by_tool": False, "user_folder_scan_performed_by_tool": False}


def _safe_prefix(value: str) -> str:
    text = str(value or "msn_manual_capture_bundle").strip()
    if not _SAFE_PREFIX_RE.match(text):
        raise ValueError("file_prefix must be a safe identifier")
    return text


def _write(output_dir: Path, file_name: str, text: str) -> MSNManualCaptureBundleStoredFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / file_name
    data = text.encode("utf-8")
    path.write_bytes(data)
    return MSNManualCaptureBundleStoredFile(
        file_name=file_name,
        role="msn_manual_capture_bundle_json",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
    )


def store_msn_manual_capture_bundle(
    *,
    output_dir: str | Path,
    bundle: MSNManualCaptureBundle,
    file_prefix: str = "msn_manual_capture_bundle",
) -> MSNManualCaptureBundleStoreResult:
    prefix = _safe_prefix(file_prefix)
    file = _write(Path(output_dir), f"{prefix}.json", msn_manual_capture_bundle_to_json(bundle))
    manifest_payload = {
        "schema_version": MSN_MANUAL_CAPTURE_BUNDLE_STORE_SCHEMA_VERSION,
        "bundle_file_name": file.file_name,
        "bundle_sha256": bundle.bundle_sha256,
        "stored_file_sha256": file.sha256,
        "ready_for_total_export_review": bundle.ready_for_total_export_review,
        "review_required": True,
        "full_local_path_serialized": False,
    }
    manifest = _write(Path(output_dir), f"{prefix}_manifest.json", json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n")
    return MSNManualCaptureBundleStoreResult(
        schema_version=MSN_MANUAL_CAPTURE_BUNDLE_STORE_SCHEMA_VERSION,
        files=(file, manifest),
    )


def msn_manual_capture_bundle_store_result_to_json(result: MSNManualCaptureBundleStoreResult) -> str:
    return _json_bytes(result.to_dict()).decode("utf-8")
