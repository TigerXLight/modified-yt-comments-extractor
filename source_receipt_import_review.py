from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


SOURCE_RECEIPT_IMPORT_REVIEW_SCHEMA_VERSION = "source_receipt_import_review_v1"

SUPPORTED_RECEIPT_TYPES = (
    "browser_capture",
    "screenshot",
    "article_page",
    "comments",
    "livechat",
    "media",
    "archive",
    "archivebox",
    "offline_bundle",
    "evidence_movement",
    "completed_evidence",
    "manual_source_note",
)

UNSAFE_KEYS = (
    "cookie",
    "credential",
    "authorization",
    "auth_header",
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "raw_payload",
    "raw_comments",
    "raw_tweet",
    "raw_transcript",
)

UNSAFE_CLAIM_KEYS = (
    "live_verification_claimed",
    "browser_automation_claimed",
    "archive_submission_claimed",
    "downloaded_files_claimed",
    "screenshot_ocr_claimed",
    "automatic_classification",
    "protected_attribute_inference",
)

LOCAL_PATH_PATTERN = re.compile(r"(^[A-Za-z]:\\|^\\\\|^/Users/|^/home/|^/var/|^/tmp/)")


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
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def _walk_items(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_walk_items(nested, next_prefix))
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            items.extend(_walk_items(nested, f"{prefix}[{index}]"))
    else:
        items.append((prefix, value))
    return items


def _validate_payload(data: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    receipt_type = str(data.get("receipt_type") or "")
    if receipt_type not in SUPPORTED_RECEIPT_TYPES:
        errors.append("unsupported_receipt_type")
    for required in ("receipt_type", "method_id", "operator_timestamp_utc", "status"):
        if not str(data.get(required) or ""):
            errors.append(f"missing_required_field:{required}")
    for path, value in _walk_items(data):
        key = path.rsplit(".", 1)[-1].lower()
        if any(marker in key for marker in UNSAFE_KEYS):
            errors.append(f"unsafe_key:{path}")
        if any(marker == key for marker in UNSAFE_CLAIM_KEYS) and bool(value):
            errors.append(f"unsafe_claim:{path}")
        if isinstance(value, str) and LOCAL_PATH_PATTERN.search(value):
            errors.append(f"full_local_path_rejected:{path}")
    if data.get("completed_evidence_claimed") is True:
        if receipt_type != "completed_evidence":
            errors.append("completed_evidence_claim_wrong_receipt_type")
        if not data.get("verified_sha256"):
            errors.append("completed_evidence_requires_verified_hash")
    return tuple(sorted(set(errors)))


@dataclass(frozen=True)
class SourceReceiptImportReview:
    receipt_id: str
    receipt_type: str
    method_id: str
    operator_timestamp_utc: str
    status: str
    validation_errors: tuple[str, ...]
    safe_metadata: Mapping[str, Any]
    schema_version: str = SOURCE_RECEIPT_IMPORT_REVIEW_SCHEMA_VERSION
    user_review_required: bool = True
    raw_credentials_rejected: bool = True
    raw_payload_rejected: bool = True
    full_local_path_rejected: bool = True
    completed_evidence_not_assumed: bool = True

    @property
    def accepted(self) -> bool:
        return not self.validation_errors

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["accepted"] = self.accepted
        return data


@dataclass(frozen=True)
class SourceReceiptImportReviewBundle:
    bundle_id: str
    receipts: tuple[SourceReceiptImportReview, ...]
    schema_version: str = SOURCE_RECEIPT_IMPORT_REVIEW_SCHEMA_VERSION
    user_review_required: bool = True
    live_execution_performed_by_importer: bool = False
    credentials_read_by_importer: bool = False

    @property
    def receipt_count(self) -> int:
        return len(self.receipts)

    @property
    def accepted_count(self) -> int:
        return sum(1 for receipt in self.receipts if receipt.accepted)

    @property
    def rejected_count(self) -> int:
        return self.receipt_count - self.accepted_count

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["receipt_count"] = self.receipt_count
        data["accepted_count"] = self.accepted_count
        data["rejected_count"] = self.rejected_count
        return data


def import_source_receipt_payload(payload: str | Mapping[str, Any]) -> SourceReceiptImportReview:
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    if not isinstance(data, dict):
        raise ValueError("Receipt payload must be a JSON object")
    errors = _validate_payload(data)
    safe_metadata = {
        "receipt_type": str(data.get("receipt_type") or ""),
        "method_id": str(data.get("method_id") or ""),
        "operator_timestamp_utc": str(data.get("operator_timestamp_utc") or ""),
        "status": str(data.get("status") or ""),
        "artifact_count": int(data.get("artifact_count") or 0),
        "hash_count": len(tuple(data.get("hashes") or ())) if isinstance(data.get("hashes"), Sequence) else 0,
    }
    return SourceReceiptImportReview(
        receipt_id="source_receipt_import_" + _sha16((safe_metadata, errors)),
        receipt_type=safe_metadata["receipt_type"],
        method_id=safe_metadata["method_id"],
        operator_timestamp_utc=safe_metadata["operator_timestamp_utc"],
        status=safe_metadata["status"],
        validation_errors=errors,
        safe_metadata=safe_metadata,
    )


def build_source_receipt_import_review_bundle(
    payloads: Sequence[str | Mapping[str, Any]],
) -> SourceReceiptImportReviewBundle:
    receipts = tuple(import_source_receipt_payload(payload) for payload in payloads)
    return SourceReceiptImportReviewBundle(
        bundle_id="source_receipt_import_review_" + _sha16([receipt.to_dict() for receipt in receipts]),
        receipts=receipts,
    )


def attach_receipt_reviews_to_workflow_summary(
    *,
    source_id: str,
    bundle: SourceReceiptImportReviewBundle,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "receipt_import_bundle_id": bundle.bundle_id,
        "receipt_count": bundle.receipt_count,
        "accepted_receipt_count": bundle.accepted_count,
        "rejected_receipt_count": bundle.rejected_count,
        "user_review_required": True,
        "live_execution_performed_by_importer": False,
        "credentials_read_by_importer": False,
    }


def source_receipt_import_review_bundle_to_json(bundle: SourceReceiptImportReviewBundle) -> str:
    return json.dumps(bundle.to_dict(), indent=2, sort_keys=True)
