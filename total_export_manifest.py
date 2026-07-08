from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from evidence_schema import (
    ClaimEvidenceNote,
    EvidenceProvenance,
    MediaSourceChainNote,
    utc_now_iso,
)


def sha256_for_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return ""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
