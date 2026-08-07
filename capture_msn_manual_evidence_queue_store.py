from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_msn_manual_evidence_queue_item import MSNManualEvidenceQueueItem, msn_manual_evidence_queue_item_to_json

MSN_MANUAL_EVIDENCE_QUEUE_STORE_SCHEMA_VERSION = "msn_manual_evidence_queue_store_v1"
_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")


def _safe_prefix(value: str) -> str:
    text = str(value or "msn_manual_evidence_queue").strip()
    if not _SAFE_PREFIX_RE.match(text):
        raise ValueError(f"unsafe file_prefix: {value!r}")
    return text


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class MSNManualEvidenceQueueStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualEvidenceQueueStoreResult:
    schema_version: str
    queue_item_id: str
    queue_id: str
    files: tuple[MSNManualEvidenceQueueStoredFile, ...]
    file_count: int
    ready_for_evidence_queue_review: bool
    metadata_only_store_result: bool = True
    full_local_path_serialized: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _write_bytes(root: Path, file_name: str, payload: bytes, *, role: str) -> MSNManualEvidenceQueueStoredFile:
    path = root / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return MSNManualEvidenceQueueStoredFile(file_name=file_name, role=role, sha256=_sha256_bytes(payload), byte_count=len(payload))


def store_msn_manual_evidence_queue_item(
    *,
    output_dir: str | Path,
    item: MSNManualEvidenceQueueItem,
    file_prefix: str = "msn_manual_evidence_queue",
) -> MSNManualEvidenceQueueStoreResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    prefix = _safe_prefix(file_prefix)
    item_payload = msn_manual_evidence_queue_item_to_json(item).encode("utf-8")
    index_payload = json.dumps(
        {
            "schema_version": "msn_manual_evidence_queue_index_v1",
            "queue_id": item.queue_id,
            "queue_item_ids": [item.queue_item_id],
            "queue_item_file_names": [f"queue/{prefix}_{item.queue_item_id}.json"],
            "ready_for_evidence_queue_review": item.ready_for_evidence_queue_review,
            "review_required": True,
            "full_local_path_serialized": False,
            "completed_capture_claimed": False,
            "verified_capture_claimed": False,
        },
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")
    files = (
        _write_bytes(root, f"queue/{prefix}_{item.queue_item_id}.json", item_payload, role="evidence_queue_item_json"),
        _write_bytes(root, f"queue/{prefix}_index.json", index_payload, role="evidence_queue_index_json"),
    )
    return MSNManualEvidenceQueueStoreResult(
        schema_version=MSN_MANUAL_EVIDENCE_QUEUE_STORE_SCHEMA_VERSION,
        queue_item_id=item.queue_item_id,
        queue_id=item.queue_id,
        files=files,
        file_count=len(files),
        ready_for_evidence_queue_review=item.ready_for_evidence_queue_review,
    )


def msn_manual_evidence_queue_store_result_to_json(result: MSNManualEvidenceQueueStoreResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
