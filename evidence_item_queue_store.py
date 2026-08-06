from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from evidence_item_queue import (
    EvidenceItemQueue,
    build_evidence_item_queue_review_activity_flow_summary,
    build_evidence_item_queue_review_summary,
)


EVIDENCE_QUEUE_REVIEW_STORE_SCHEMA_VERSION = "evidence_item_queue_review_store_v1"


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
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _payload_sha256(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceItemQueueReviewStoreDocument:
    store_id: str
    created_at_utc: str
    queue_review_summary: Mapping[str, Any]
    activity_flow_summary: Mapping[str, Any]
    payload_sha256: str = ""
    schema_version: str = EVIDENCE_QUEUE_REVIEW_STORE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    explicit_records_only: bool = True
    persistence_scope: str = "explicit_user_selected_review_store_path"
    file_read_performed: bool = False
    file_check_performed: bool = False
    file_move_performed: bool = False
    file_existence_claimed: bool = False
    full_local_path_included: bool = False
    raw_payload_included: bool = False
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_fetch_or_api_call_performed: bool = False
    browser_automation_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True
    note: str = (
        "Atomic persistence of Evidence Item Queue review summaries only; raw queue "
        "payloads, full paths, file-state checks, runtime execution, and final-evidence "
        "claims are excluded."
    )

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        payload = dict(data)
        payload["payload_sha256"] = ""
        data["payload_sha256"] = self.payload_sha256 or _payload_sha256(payload)
        return data


def build_evidence_item_queue_review_store_document(
    queue: EvidenceItemQueue,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    actor_label: str = "",
    app_version: str = "",
) -> EvidenceItemQueueReviewStoreDocument:
    if not session_id:
        raise ValueError("session_id is required for queue review store documents")
    if not timestamp_utc:
        raise ValueError("timestamp_utc is required for deterministic queue review stores")
    queue_summary = build_evidence_item_queue_review_summary(queue).to_dict()
    activity_flow = build_evidence_item_queue_review_activity_flow_summary(
        queue,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        actor_label=actor_label,
        app_version=app_version,
    ).to_dict()
    payload = {
        "activity_flow_summary": activity_flow,
        "created_at_utc": timestamp_utc,
        "queue_review_summary": queue_summary,
        "schema_version": EVIDENCE_QUEUE_REVIEW_STORE_SCHEMA_VERSION,
    }
    store_id = "evidence_queue_review_store_" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()[:16]
    document = EvidenceItemQueueReviewStoreDocument(
        store_id=store_id,
        created_at_utc=timestamp_utc,
        queue_review_summary=queue_summary,
        activity_flow_summary=activity_flow,
    )
    return EvidenceItemQueueReviewStoreDocument(
        **{
            **document.__dict__,
            "payload_sha256": document.to_dict()["payload_sha256"],
        }
    )


def validate_evidence_item_queue_review_store_document(
    document: Mapping[str, Any],
) -> None:
    if document.get("schema_version") != EVIDENCE_QUEUE_REVIEW_STORE_SCHEMA_VERSION:
        raise ValueError("Unsupported Evidence Item Queue review store schema version")
    if document.get("metadata_only") is not True:
        raise ValueError("Evidence Item Queue review store must remain metadata-only")
    for forbidden in (
        "file_read_performed",
        "file_check_performed",
        "file_move_performed",
        "file_existence_claimed",
        "full_local_path_included",
        "raw_payload_included",
        "completed_evidence_claimed",
        "verified_evidence_claimed",
        "live_fetch_or_api_call_performed",
        "browser_automation_claimed",
        "automatic_classification",
    ):
        if document.get(forbidden) is not False:
            raise ValueError(f"Unsafe Evidence Item Queue review store flag: {forbidden}")
    payload = dict(document)
    expected_hash = str(payload.pop("payload_sha256", ""))
    payload["payload_sha256"] = ""
    actual_hash = _payload_sha256(payload)
    if expected_hash != actual_hash:
        raise ValueError("Evidence Item Queue review store hash mismatch")


def write_evidence_item_queue_review_store(
    document: EvidenceItemQueueReviewStoreDocument,
    output_path: str | os.PathLike[str],
) -> str:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = document.to_dict()
    validate_evidence_item_queue_review_store_document(payload)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_name = handle.name
        handle.write(encoded)
        handle.write("\n")
    try:
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return str(target)


def read_evidence_item_queue_review_store(
    input_path: str | os.PathLike[str],
) -> dict[str, Any]:
    with Path(input_path).open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError("Evidence Item Queue review store must be a JSON object")
    validate_evidence_item_queue_review_store_document(document)
    return document
