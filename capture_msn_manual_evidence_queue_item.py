from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

MSN_MANUAL_EVIDENCE_QUEUE_ITEM_SCHEMA_VERSION = "msn_manual_evidence_queue_item_v1"
MSN_MANUAL_EVIDENCE_QUEUE_ITEM_KIND = "msn_manual_capture_total_export_review"
MSN_MANUAL_EVIDENCE_QUEUE_READY_STATUS = "queued_for_evidence_review"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-/]{0,220}$")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_REQUIRED_ROLES = {"article_text", "capture_bundle_json", "total_export_manifest_json", "total_export_packet_json"}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_id(value: Any, *, field_name: str, default: str | None = None) -> str:
    text = str(value or default or "").strip()
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    if _SECRET_RE.search(text) or _FULL_PATH_RE.search(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    return text


def _safe_name(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if text.startswith("/") or ":/" in text or ":\\" in text or ".." in text.split("/"):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    if not _SAFE_NAME_RE.match(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    if _SECRET_RE.search(text) or _FULL_PATH_RE.search(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    return text


def _safe_sha(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.match(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    return text


def _positive_int(value: Any, *, field_name: str) -> int:
    try:
        number = int(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if number < 0:
        raise ValueError(f"{field_name} must not be negative")
    return number


def _assert_no_unsafe_strings(value: Any, *, context: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            _assert_no_unsafe_strings(child, context=f"{context}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_unsafe_strings(child, context=f"{context}[{index}]")
    elif isinstance(value, str):
        if _SECRET_RE.search(value) or _FULL_PATH_RE.search(value):
            raise ValueError(f"unsafe string in {context}")


def _unwrap_pipeline_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if "pipeline_result" in payload and isinstance(payload["pipeline_result"], Mapping):
        return payload["pipeline_result"]
    return payload


@dataclass(frozen=True)
class MSNManualEvidenceQueueAsset:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    relative_asset_name: bool = True
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualEvidenceQueueItem:
    schema_version: str
    queue_item_id: str
    queue_id: str
    item_kind: str
    source_type: str
    source_url_host_hint: str
    package_id: str
    review_status: str
    asset_count: int
    asset_roles: tuple[str, ...]
    assets: tuple[MSNManualEvidenceQueueAsset, ...]
    article_text_char_count: int
    comment_count: int
    total_export_manifest_file_name: str
    total_export_manifest_sha256: str
    pipeline_report_sha256: str
    source_pipeline_schema_version: str
    source_pipeline_package_id: str
    action_pipeline_implemented: bool
    generated_operator_action_kits: bool
    explicit_operator_artifact_files_read: bool
    total_export_package_written: bool
    ready_for_total_export_review: bool
    ready_for_evidence_queue_review: bool
    review_required: bool = True
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    credential_value_read: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_assets(pipeline: Mapping[str, Any]) -> tuple[MSNManualEvidenceQueueAsset, ...]:
    store = pipeline.get("total_export_store_result")
    if not isinstance(store, Mapping):
        raise ValueError("pipeline payload is missing total_export_store_result")
    files = store.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("total_export_store_result.files must be a non-empty list")
    assets: list[MSNManualEvidenceQueueAsset] = []
    for index, raw in enumerate(files):
        if not isinstance(raw, Mapping):
            raise ValueError(f"asset {index} must be an object")
        file_name = _safe_name(raw.get("file_name"), field_name=f"assets[{index}].file_name")
        role = _safe_id(raw.get("role"), field_name=f"assets[{index}].role")
        sha256 = _safe_sha(raw.get("sha256"), field_name=f"assets[{index}].sha256")
        byte_count = _positive_int(raw.get("byte_count"), field_name=f"assets[{index}].byte_count")
        assets.append(MSNManualEvidenceQueueAsset(file_name=file_name, role=role, sha256=sha256, byte_count=byte_count))
    roles = {asset.role for asset in assets}
    missing = sorted(_REQUIRED_ROLES - roles)
    if missing:
        raise ValueError(f"total export package is missing required asset roles: {', '.join(missing)}")
    return tuple(assets)


def build_msn_manual_evidence_queue_item(
    pipeline_payload: Mapping[str, Any],
    *,
    queue_id: str = "source_evidence_review_queue",
    item_id: str | None = None,
) -> MSNManualEvidenceQueueItem:
    """Build a Source Evidence queue item from an implemented MSN action Total Export pipeline report."""
    _assert_no_unsafe_strings(pipeline_payload)
    pipeline = _unwrap_pipeline_payload(pipeline_payload)
    schema_version = str(pipeline.get("schema_version") or "")
    if schema_version != "msn_manual_action_total_export_pipeline_v1":
        raise ValueError(f"unsupported pipeline schema_version: {schema_version!r}")
    package_id = _safe_id(pipeline.get("package_id"), field_name="package_id")
    source_url_host_hint = _safe_name(pipeline.get("source_url_host_hint"), field_name="source_url_host_hint")
    manifest_name = _safe_name(pipeline.get("total_export_manifest_file_name"), field_name="total_export_manifest_file_name")
    manifest_sha = _safe_sha(pipeline.get("total_export_manifest_sha256"), field_name="total_export_manifest_sha256")
    pipeline_sha = _safe_sha(pipeline.get("pipeline_report_sha256"), field_name="pipeline_report_sha256")
    if pipeline.get("pipeline_implemented") is not True:
        raise ValueError("pipeline_implemented must be true")
    if pipeline.get("generated_operator_action_kits") is not True:
        raise ValueError("generated_operator_action_kits must be true")
    if pipeline.get("explicit_operator_artifact_files_read") is not True:
        raise ValueError("explicit_operator_artifact_files_read must be true")
    if pipeline.get("total_export_package_written") is not True:
        raise ValueError("total_export_package_written must be true")
    if pipeline.get("ready_for_total_export_review") is not True:
        raise ValueError("pipeline must be ready_for_total_export_review")
    forbidden_true_flags = [
        "live_network_request_performed_by_tool",
        "browser_automation_performed_by_tool",
        "archive_submission_performed_by_tool",
        "media_download_performed_by_tool",
        "credential_value_read",
        "raw_media_payload_included",
        "full_local_path_serialized",
        "completed_capture_claimed",
        "verified_capture_claimed",
    ]
    unsafe_flags = [name for name in forbidden_true_flags if pipeline.get(name) is True]
    if unsafe_flags:
        raise ValueError(f"pipeline has unsafe true flags: {', '.join(unsafe_flags)}")
    safe_queue_id = _safe_id(queue_id, field_name="queue_id")
    assets = _extract_assets(pipeline)
    roles = tuple(sorted({asset.role for asset in assets}))
    deterministic_source = f"{safe_queue_id}|{package_id}|{manifest_sha}|{pipeline_sha}|{len(assets)}"
    queue_item_id = _safe_id(item_id or f"msn_manual_{_sha256_text(deterministic_source)[:16]}", field_name="queue_item_id")
    return MSNManualEvidenceQueueItem(
        schema_version=MSN_MANUAL_EVIDENCE_QUEUE_ITEM_SCHEMA_VERSION,
        queue_item_id=queue_item_id,
        queue_id=safe_queue_id,
        item_kind=MSN_MANUAL_EVIDENCE_QUEUE_ITEM_KIND,
        source_type="msn_manual_capture_total_export",
        source_url_host_hint=source_url_host_hint,
        package_id=package_id,
        review_status=MSN_MANUAL_EVIDENCE_QUEUE_READY_STATUS,
        asset_count=len(assets),
        asset_roles=roles,
        assets=assets,
        article_text_char_count=_positive_int(pipeline.get("article_text_char_count"), field_name="article_text_char_count"),
        comment_count=_positive_int(pipeline.get("comment_count"), field_name="comment_count"),
        total_export_manifest_file_name=manifest_name,
        total_export_manifest_sha256=manifest_sha,
        pipeline_report_sha256=pipeline_sha,
        source_pipeline_schema_version=schema_version,
        source_pipeline_package_id=package_id,
        action_pipeline_implemented=True,
        generated_operator_action_kits=True,
        explicit_operator_artifact_files_read=True,
        total_export_package_written=True,
        ready_for_total_export_review=True,
        ready_for_evidence_queue_review=True,
    )


def msn_manual_evidence_queue_item_to_json(item: MSNManualEvidenceQueueItem) -> str:
    return _json_bytes(item.to_dict()).decode("utf-8")
