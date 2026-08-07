from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from capture_msn_manual_evidence_review_package import (
    MSNManualEvidenceReviewPackage,
    msn_manual_evidence_review_package_to_json,
)

MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STORE_SCHEMA_VERSION = "msn_manual_evidence_review_package_store_v1"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualEvidenceReviewStoredFile:
    role: str
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class MSNManualEvidenceReviewPackageStoreReport:
    schema_version: str
    queue_item_id: str
    stored_files: list[MSNManualEvidenceReviewStoredFile] = field(default_factory=list)
    output_file_count: int = 0
    store_status: str = "STORED"


def _safe_stem(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._")
    return safe or "msn_manual_evidence_review_package"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_bytes(path: Path, payload: dict[str, Any]) -> MSNManualEvidenceReviewStoredFile:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return MSNManualEvidenceReviewStoredFile(
        role=str(payload.get("file_role", path.stem)),
        filename=path.name,
        sha256=_hash_bytes(data),
        byte_count=len(data),
    )


def store_msn_manual_evidence_review_package(
    package: MSNManualEvidenceReviewPackage,
    output_dir: str | Path,
) -> MSNManualEvidenceReviewPackageStoreReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(package.queue_item_id)

    package_payload = json.loads(msn_manual_evidence_review_package_to_json(package))
    package_payload["file_role"] = "evidence_review_package"
    package_file = _write_json_bytes(directory / f"{stem}.evidence_review_package.json", package_payload)

    index_payload = {
        "schema_version": MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STORE_SCHEMA_VERSION,
        "file_role": "evidence_review_package_index",
        "queue_item_id": package.queue_item_id,
        "review_status": package.review_status,
        "package_hash": package.package_hash,
        "safe_asset_filenames": [asset.filename for asset in package.assets],
        "review_action_count": len(package.review_actions),
    }
    index_file = _write_json_bytes(directory / f"{stem}.evidence_review_index.json", index_payload)

    files = [package_file, index_file]
    return MSNManualEvidenceReviewPackageStoreReport(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STORE_SCHEMA_VERSION,
        queue_item_id=package.queue_item_id,
        stored_files=files,
        output_file_count=len(files),
    )


def msn_manual_evidence_review_package_store_report_to_json(report: MSNManualEvidenceReviewPackageStoreReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
