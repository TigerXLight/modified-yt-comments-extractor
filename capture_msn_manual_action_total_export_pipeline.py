from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_manual_live_smoke_action_execution_kit import build_manual_live_smoke_action_execution_kit
from capture_manual_live_smoke_action_execution_kit_store import (
    manual_live_smoke_action_execution_kit_store_result_to_json,
    store_manual_live_smoke_action_execution_kit,
)
from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle
from capture_msn_manual_comments_extraction import extract_msn_manual_comments
from capture_msn_manual_total_export_manifest import build_msn_manual_total_export_packet, msn_manual_total_export_packet_to_json
from capture_msn_manual_total_export_package_store import (
    msn_manual_total_export_package_store_result_to_json,
    store_msn_manual_total_export_package,
)
MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_SCHEMA_VERSION = "msn_manual_action_total_export_pipeline_v1"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_ALLOWED_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _host_hint(url: str) -> str:
    host = re.sub(r"^https?://", "", str(url), flags=re.I).split("/", 1)[0].lower()
    return host[:80] or "unknown-host"


def _safe_text(value: Any, *, field_name: str, allow_empty: bool = False, max_length: int = 2000) -> str:
    text = str(value or "").strip()
    if not text and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > max_length:
        raise ValueError(f"{field_name} is too long")
    if _SECRET_RE.search(field_name) or _SECRET_RE.search(text):
        raise ValueError(f"secret-like value is not allowed for {field_name}")
    if _FULL_PATH_RE.search(text):
        raise ValueError(f"full local path is not allowed for {field_name}")
    return text


def _safe_id(value: Any, *, field_name: str, default: str | None = None) -> str:
    text = str(value or default or "").strip()
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    if _SECRET_RE.search(text) or _FULL_PATH_RE.search(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    return text


def _safe_url(value: str) -> str:
    text = _safe_text(value, field_name="source_url", max_length=3000)
    if not _ALLOWED_URL_RE.match(text):
        raise ValueError("source_url must be an http(s) URL")
    return text


def _read_explicit_artifact(path_value: str | Path, *, field_name: str) -> tuple[str, str, str, int]:
    path = Path(path_value)
    if not path.is_file():
        raise ValueError(f"explicit {field_name} file does not exist: {path.name}")
    data = path.read_bytes()
    text = data.decode("utf-8")
    return path.name, text, _sha256_bytes(data), len(data)


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return asdict(value)


@dataclass(frozen=True)
class MSNManualActionTotalExportPipelineResult:
    schema_version: str
    source_url_host_hint: str
    package_id: str
    action_kit_file_count: int
    total_export_file_count: int
    total_export_manifest_file_name: str
    article_artifact_file_name: str
    article_artifact_sha256: str
    article_artifact_byte_count: int
    comments_artifact_file_name: str | None
    comments_artifact_sha256: str | None
    comments_artifact_byte_count: int | None
    article_text_char_count: int
    comment_count: int
    total_export_packet_sha256: str
    total_export_manifest_sha256: str
    pipeline_report_sha256: str
    action_kit_store_result: dict[str, Any]
    total_export_packet: dict[str, Any]
    total_export_store_result: dict[str, Any]
    total_export_verification_report: dict[str, Any]
    pipeline_implemented: bool = True
    generated_operator_action_kits: bool = True
    explicit_operator_artifact_files_read: bool = True
    total_export_package_written: bool = True
    ready_for_total_export_review: bool = True
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


def build_msn_manual_action_total_export_pipeline(
    *,
    source_url: str,
    article_file: str | Path,
    output_dir: str | Path,
    comments_file: str | Path | None = None,
    package_id: str = "msn_manual_total_export",
    file_prefix: str = "msn_manual_action_total_export",
    operator_intent: str = "MSN manual capture for Total Export review",
) -> MSNManualActionTotalExportPipelineResult:
    """Run the local implemented bridge from explicit MSN artifacts to Total Export package output."""
    url = _safe_url(source_url)
    safe_package_id = _safe_id(package_id, field_name="package_id", default="msn_manual_total_export")
    safe_prefix = _safe_id(file_prefix, field_name="file_prefix", default="msn_manual_action_total_export")
    safe_intent = _safe_text(operator_intent, field_name="operator_intent", max_length=1000)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    article_name, article_text, article_sha256, article_bytes = _read_explicit_artifact(article_file, field_name="article")
    comments_name: str | None = None
    comments_text: str | None = None
    comments_sha256: str | None = None
    comments_bytes: int | None = None
    if comments_file is not None:
        comments_name, comments_text, comments_sha256, comments_bytes = _read_explicit_artifact(comments_file, field_name="comments")

    action_kit_files: list[dict[str, Any]] = []
    article_kit = build_manual_live_smoke_action_execution_kit(
        site_id="msn",
        action_id="msn_article_capture",
        source_url=url,
        operator_intent=safe_intent,
        file_prefix=f"{safe_prefix}_article",
    )
    article_kit_store = store_manual_live_smoke_action_execution_kit(
        output_directory=root / "operator_action_kits",
        kit=article_kit,
    )
    action_kit_files.extend(json.loads(manual_live_smoke_action_execution_kit_store_result_to_json(article_kit_store))["artifacts"])

    if comments_file is not None:
        comments_kit = build_manual_live_smoke_action_execution_kit(
            site_id="msn",
            action_id="msn_comments_shadow_root_capture",
            source_url=url,
            operator_intent=safe_intent,
            file_prefix=f"{safe_prefix}_comments",
        )
        comments_kit_store = store_manual_live_smoke_action_execution_kit(
            output_directory=root / "operator_action_kits",
            kit=comments_kit,
        )
        action_kit_files.extend(json.loads(manual_live_smoke_action_execution_kit_store_result_to_json(comments_kit_store))["artifacts"])

    article = extract_msn_manual_article(source_url=url, artifact_text=article_text, artifact_file_name=article_name)
    comments = None
    if comments_text is not None and comments_name is not None:
        comments = extract_msn_manual_comments(source_url=url, artifact_text=comments_text, artifact_file_name=comments_name)
    bundle = build_msn_manual_capture_bundle(article=article, comments=comments)
    total_export_packet = build_msn_manual_total_export_packet(bundle=bundle, package_id=safe_package_id)
    total_export_store = store_msn_manual_total_export_package(
        output_dir=root / "total_export_package",
        bundle=bundle,
        package_id=safe_package_id,
        file_prefix=safe_package_id,
    )
    total_export_payload = {
        "packet": json.loads(msn_manual_total_export_packet_to_json(total_export_packet)),
        "store_result": json.loads(msn_manual_total_export_package_store_result_to_json(total_export_store)),
    }
    verification_payload = {
        "schema_version": "msn_manual_action_total_export_nested_package_check_v1",
        "ready_for_total_export_review": total_export_packet.ready_for_total_export_review and total_export_store.ready_for_total_export_review,
        "package_id": total_export_packet.package_id,
        "file_count": len(total_export_store.files),
        "comment_count": bundle.comment_count,
        "total_export_manifest_present": bool(total_export_packet.manifest_file_name),
        "article_text_present": bool(total_export_packet.article_text_file_name),
        "bundle_json_present": bool(total_export_packet.bundle_json_file_name),
        "completed_capture_claimed": False,
        "verified_capture_claimed": False,
        "full_local_path_serialized": False,
    }

    action_kit_store_result = {
        "schema_version": "msn_manual_action_total_export_operator_kit_store_v1",
        "artifacts": action_kit_files,
        "file_count": len(action_kit_files),
        "full_local_path_serialized": False,
    }
    total_export_store_payload = json.loads(msn_manual_total_export_package_store_result_to_json(total_export_store))
    base_report = {
        "schema_version": MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_SCHEMA_VERSION,
        "source_url_host_hint": _host_hint(url),
        "package_id": total_export_packet.package_id,
        "action_kit_file_count": len(action_kit_files),
        "total_export_file_count": len(total_export_store.files),
        "article_artifact_sha256": article_sha256,
        "comments_artifact_sha256": comments_sha256,
        "total_export_packet_sha256": total_export_store.packet_sha256,
        "total_export_manifest_sha256": total_export_store.manifest_sha256,
    }
    return MSNManualActionTotalExportPipelineResult(
        schema_version=MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_SCHEMA_VERSION,
        source_url_host_hint=_host_hint(url),
        package_id=total_export_packet.package_id,
        action_kit_file_count=len(action_kit_files),
        total_export_file_count=len(total_export_store.files),
        total_export_manifest_file_name=total_export_packet.manifest_file_name,
        article_artifact_file_name=article_name,
        article_artifact_sha256=article_sha256,
        article_artifact_byte_count=article_bytes,
        comments_artifact_file_name=comments_name,
        comments_artifact_sha256=comments_sha256,
        comments_artifact_byte_count=comments_bytes,
        article_text_char_count=article.article_text_char_count,
        comment_count=bundle.comment_count,
        total_export_packet_sha256=total_export_store.packet_sha256,
        total_export_manifest_sha256=total_export_store.manifest_sha256,
        pipeline_report_sha256=_sha256_bytes(_json_bytes(base_report)),
        action_kit_store_result=action_kit_store_result,
        total_export_packet=total_export_payload["packet"],
        total_export_store_result=total_export_store_payload,
        total_export_verification_report=verification_payload,
        ready_for_total_export_review=verification_payload.get("ready_for_total_export_review") is True,
    )


def msn_manual_action_total_export_pipeline_result_to_json(result: MSNManualActionTotalExportPipelineResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
