from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_msn_manual_action_total_export_pipeline import (
    MSNManualActionTotalExportPipelineResult,
    msn_manual_action_total_export_pipeline_result_to_json,
)


MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_STORE_SCHEMA_VERSION = "msn_manual_action_total_export_pipeline_store_v1"
_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")


def _safe_prefix(value: str) -> str:
    text = str(value or "msn_manual_action_total_export_pipeline").strip()
    if not _SAFE_PREFIX_RE.match(text):
        raise ValueError(f"unsafe file_prefix: {value!r}")
    return text


@dataclass(frozen=True)
class MSNManualActionTotalExportPipelineStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualActionTotalExportPipelineStoreResult:
    schema_version: str
    files: tuple[MSNManualActionTotalExportPipelineStoredFile, ...]
    metadata_only_store_result: bool = True
    full_local_path_serialized: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _write(root: Path, file_name: str, text: str, role: str) -> MSNManualActionTotalExportPipelineStoredFile:
    data = text.encode("utf-8")
    root.mkdir(parents=True, exist_ok=True)
    (root / file_name).write_bytes(data)
    return MSNManualActionTotalExportPipelineStoredFile(
        file_name=file_name,
        role=role,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
    )


def store_msn_manual_action_total_export_pipeline_result(
    *,
    output_dir: str | Path,
    result: MSNManualActionTotalExportPipelineResult,
    file_prefix: str = "msn_manual_action_total_export_pipeline",
) -> MSNManualActionTotalExportPipelineStoreResult:
    prefix = _safe_prefix(file_prefix)
    root = Path(output_dir)
    report_text = msn_manual_action_total_export_pipeline_result_to_json(result) + "\n"
    manifest_payload = {
        "schema_version": MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_STORE_SCHEMA_VERSION,
        "report_file_name": f"{prefix}_report.json",
        "pipeline_report_sha256": result.pipeline_report_sha256,
        "package_id": result.package_id,
        "ready_for_total_export_review": result.ready_for_total_export_review,
        "review_required": True,
        "full_local_path_serialized": False,
    }
    files = (
        _write(root, f"{prefix}_report.json", report_text, "pipeline_report_json"),
        _write(root, f"{prefix}_manifest.json", json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n", "pipeline_store_manifest_json"),
    )
    return MSNManualActionTotalExportPipelineStoreResult(
        schema_version=MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_STORE_SCHEMA_VERSION,
        files=files,
    )


def msn_manual_action_total_export_pipeline_store_result_to_json(result: MSNManualActionTotalExportPipelineStoreResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
