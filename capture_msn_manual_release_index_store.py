from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_release_index import MSNManualReleaseIndexReport, msn_manual_release_index_to_json

MSN_MANUAL_RELEASE_INDEX_STORE_SCHEMA_VERSION = "msn_manual_release_index_store_v1"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualReleaseIndexStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualReleaseIndexStoreReport:
    schema_version: str
    index_id: str
    release_id: str
    queue_item_id: str
    stored_files: list[MSNManualReleaseIndexStoredFile] = field(default_factory=list)
    output_file_count: int = 0
    store_status: str = "STORED"


def _safe_stem(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._")
    return safe or "msn_manual_release_index"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_bytes(path: Path, payload: dict[str, Any]) -> MSNManualReleaseIndexStoredFile:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return MSNManualReleaseIndexStoredFile(
        role=str(payload.get("file_role", path.stem)),
        filename=path.name,
        sha256=_hash_bytes(data),
        byte_count=len(data),
    )


def store_msn_manual_release_index(
    release_index: MSNManualReleaseIndexReport,
    output_dir: str | Path,
) -> MSNManualReleaseIndexStoreReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(release_index.index_id)

    index_payload = json.loads(msn_manual_release_index_to_json(release_index))
    index_payload["file_role"] = "msn_manual_release_index"
    index_file = _write_json_bytes(directory / f"{stem}.release_index.json", index_payload)

    inventory_payload = {
        "schema_version": MSN_MANUAL_RELEASE_INDEX_STORE_SCHEMA_VERSION,
        "file_role": "msn_manual_release_inventory",
        "index_id": release_index.index_id,
        "release_id": release_index.release_id,
        "queue_item_id": release_index.queue_item_id,
        "asset_count": len(release_index.assets),
        "assets": [asdict(asset) for asset in release_index.assets],
        "lineage": [asdict(entry) for entry in release_index.lineage],
        "index_hash": release_index.index_hash,
    }
    inventory_file = _write_json_bytes(directory / f"{stem}.release_inventory.json", inventory_payload)

    queue_payload = {
        "schema_version": MSN_MANUAL_RELEASE_INDEX_STORE_SCHEMA_VERSION,
        "file_role": "msn_manual_release_queue_update",
        "index_id": release_index.index_id,
        "release_id": release_index.release_id,
        "queue_item_id": release_index.queue_item_id,
        "evidence_queue_release_update": release_index.evidence_queue_release_update,
        "total_export_release_handoff": release_index.total_export_release_handoff,
        "index_hash": release_index.index_hash,
    }
    queue_file = _write_json_bytes(directory / f"{stem}.release_queue_update.json", queue_payload)

    files = [index_file, inventory_file, queue_file]
    return MSNManualReleaseIndexStoreReport(
        schema_version=MSN_MANUAL_RELEASE_INDEX_STORE_SCHEMA_VERSION,
        index_id=release_index.index_id,
        release_id=release_index.release_id,
        queue_item_id=release_index.queue_item_id,
        stored_files=files,
        output_file_count=len(files),
    )


def msn_manual_release_index_store_report_to_json(report: MSNManualReleaseIndexStoreReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
