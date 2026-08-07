from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_evidence_review_decision import (
    MSNManualEvidenceReviewDecisionReport,
    msn_manual_evidence_review_decision_to_json,
)

MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STORE_SCHEMA_VERSION = "msn_manual_evidence_review_decision_store_v1"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualEvidenceReviewDecisionStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualEvidenceReviewDecisionStoreReport:
    schema_version: str
    decision_id: str
    queue_item_id: str
    stored_files: list[MSNManualEvidenceReviewDecisionStoredFile] = field(default_factory=list)
    output_file_count: int = 0
    store_status: str = "STORED"


def _safe_stem(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._")
    return safe or "msn_manual_evidence_review_decision"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_bytes(path: Path, payload: dict[str, Any]) -> MSNManualEvidenceReviewDecisionStoredFile:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return MSNManualEvidenceReviewDecisionStoredFile(
        role=str(payload.get("file_role", path.stem)),
        filename=path.name,
        sha256=_hash_bytes(data),
        byte_count=len(data),
    )


def store_msn_manual_evidence_review_decision(
    decision: MSNManualEvidenceReviewDecisionReport,
    output_dir: str | Path,
) -> MSNManualEvidenceReviewDecisionStoreReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(decision.decision_id)

    decision_payload = json.loads(msn_manual_evidence_review_decision_to_json(decision))
    decision_payload["file_role"] = "evidence_review_decision"
    decision_file = _write_json_bytes(directory / f"{stem}.evidence_review_decision.json", decision_payload)

    queue_update_payload = {
        "schema_version": MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STORE_SCHEMA_VERSION,
        "file_role": "evidence_queue_review_update",
        "decision_id": decision.decision_id,
        "queue_item_id": decision.queue_item_id,
        "review_decision": decision.review_decision,
        "decision_status": decision.decision_status,
        "approved_for_total_export": decision.approved_for_total_export,
        "queue_update": decision.evidence_queue_update,
        "total_export_handoff": decision.total_export_handoff,
        "decision_hash": decision.decision_hash,
    }
    queue_update_file = _write_json_bytes(directory / f"{stem}.evidence_queue_update.json", queue_update_payload)

    files = [decision_file, queue_update_file]
    return MSNManualEvidenceReviewDecisionStoreReport(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STORE_SCHEMA_VERSION,
        decision_id=decision.decision_id,
        queue_item_id=decision.queue_item_id,
        stored_files=files,
        output_file_count=len(files),
    )


def msn_manual_evidence_review_decision_store_report_to_json(report: MSNManualEvidenceReviewDecisionStoreReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
