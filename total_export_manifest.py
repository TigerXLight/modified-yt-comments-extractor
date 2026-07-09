from __future__ import annotations

import hashlib
import json
import re
from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from evidence_schema import (
    ClaimEvidenceNote,
    EvidenceProvenance,
    MediaSourceChainNote,
    utc_now_iso,
)


ASSET_TEXT_EXPORT = "text_export"
ASSET_CSV_EXPORT = "csv_export"
ASSET_EXCEL_EXPORT = "excel_export"
ASSET_JSON_EXPORT = "json_export"
ASSET_MANIFEST = "manifest"
ASSET_SCREENSHOT = "screenshot"
ASSET_HTML_SNAPSHOT = "html_snapshot"
ASSET_EXTRACTED_TEXT = "extracted_text"
ASSET_ARCHIVE_RESULT = "archive_result"
ASSET_MEDIA = "media"
ASSET_RAW_SIDECAR = "raw_sidecar"


def sha256_for_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return ""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_package_id(value: str) -> str:
    safe_value = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "").strip())
    safe_value = re.sub(r"_+", "_", safe_value).strip("_")
    return safe_value or "total_export"


def default_package_id(source_label: str = "") -> str:
    timestamp = utc_now_iso().replace("-", "").replace(":", "")
    if source_label:
        return safe_package_id(f"total_export_{safe_package_id(source_label)}_{timestamp}")
    return safe_package_id(f"total_export_{timestamp}")


def default_package_folder(base_folder: str, package_id: str) -> str:
    return str(Path(base_folder) / safe_package_id(package_id))


def asset_subfolder(asset_type: str) -> str:
    if asset_type in {
        ASSET_TEXT_EXPORT,
        ASSET_CSV_EXPORT,
        ASSET_EXCEL_EXPORT,
        ASSET_JSON_EXPORT,
        ASSET_MANIFEST,
        ASSET_ARCHIVE_RESULT,
        ASSET_RAW_SIDECAR,
    }:
        return "metadata"
    if asset_type in {ASSET_SCREENSHOT, ASSET_HTML_SNAPSHOT, ASSET_EXTRACTED_TEXT}:
        return "page_capture"
    if asset_type == ASSET_MEDIA:
        return "media"
    return "assets"


def manifest_filename(package_id: str) -> str:
    package_id = safe_package_id(package_id)
    if not package_id:
        return "manifest.json"
    return f"{package_id}_manifest.json"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_from_dict(dataclass_type: Any, data: Dict[str, Any]) -> Any:
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict for {dataclass_type.__name__}.")

    values = {}
    for dataclass_field in fields(dataclass_type):
        field_name = dataclass_field.name
        if field_name in data:
            values[field_name] = data[field_name]
        elif dataclass_field.default is MISSING and dataclass_field.default_factory is MISSING:
            raise ValueError(f"Missing required field {field_name!r} for {dataclass_type.__name__}.")
    return dataclass_type(**values)


@dataclass
class ExportAsset:
    asset_type: str = ""
    path: str = ""
    description: str = ""
    source_url: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    sha256: str = ""
    mime_type: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _value_for_dict(self)


@dataclass
class TotalExportManifest:
    package_id: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    source_urls: List[str] = field(default_factory=list)
    output_folder: str = ""
    capture_options: List[str] = field(default_factory=list)
    assets: List[ExportAsset] = field(default_factory=list)
    provenance_records: List[EvidenceProvenance] = field(default_factory=list)
    claim_notes: List[ClaimEvidenceNote] = field(default_factory=list)
    media_source_chain_notes: List[MediaSourceChainNote] = field(default_factory=list)
    archive_results: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    app_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _value_for_dict(self)


def export_asset_from_dict(data: Dict[str, Any]) -> ExportAsset:
    return _dataclass_from_dict(ExportAsset, data)


def total_export_manifest_from_dict(data: Dict[str, Any]) -> TotalExportManifest:
    values = dict(data)
    values["assets"] = [
        export_asset_from_dict(asset_data)
        for asset_data in values.get("assets", [])
    ]
    values["provenance_records"] = [
        _dataclass_from_dict(EvidenceProvenance, provenance_data)
        for provenance_data in values.get("provenance_records", [])
    ]
    values["claim_notes"] = [
        _dataclass_from_dict(ClaimEvidenceNote, claim_data)
        for claim_data in values.get("claim_notes", [])
    ]
    values["media_source_chain_notes"] = [
        _dataclass_from_dict(MediaSourceChainNote, media_data)
        for media_data in values.get("media_source_chain_notes", [])
    ]
    return _dataclass_from_dict(TotalExportManifest, values)


def read_manifest_json(path: str) -> TotalExportManifest:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return total_export_manifest_from_dict(data)


def write_manifest_json(manifest: TotalExportManifest, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)
