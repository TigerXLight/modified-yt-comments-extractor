from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_msn_manual_capture_bundle import MSNManualCaptureBundle, msn_manual_capture_bundle_to_json
from capture_msn_manual_total_export_manifest import MSNManualTotalExportPacket, build_msn_manual_total_export_packet, msn_manual_total_export_packet_to_json


MSN_MANUAL_TOTAL_EXPORT_PACKAGE_STORE_SCHEMA_VERSION = "msn_manual_total_export_package_store_v1"
_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_prefix(value: str) -> str:
    text = str(value or "msn_manual_total_export").strip()
    if not _SAFE_PREFIX_RE.match(text):
        raise ValueError(f"unsafe file prefix: {value!r}")
    return text


@dataclass(frozen=True)
class MSNManualTotalExportStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualTotalExportPackageStoreResult:
    schema_version: str
    package_id: str
    files: tuple[MSNManualTotalExportStoredFile, ...]
    packet_sha256: str
    manifest_sha256: str
    wrote_total_export_package: bool = True
    ready_for_total_export_review: bool = True
    review_required: bool = True
    full_local_path_serialized: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    credential_value_read: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _write_bytes(root: Path, relative_name: str, payload: bytes, *, role: str) -> MSNManualTotalExportStoredFile:
    if ".." in Path(relative_name).parts or Path(relative_name).is_absolute():
        raise ValueError(f"unsafe relative output name: {relative_name}")
    target = root / relative_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return MSNManualTotalExportStoredFile(
        file_name=relative_name.replace("\\", "/"),
        role=role,
        sha256=_sha256_bytes(payload),
        byte_count=len(payload),
    )


def store_msn_manual_total_export_package(
    *,
    output_dir: Path,
    bundle: MSNManualCaptureBundle,
    package_id: str | None = None,
    file_prefix: str = "msn_manual_total_export",
) -> MSNManualTotalExportPackageStoreResult:
    prefix = _safe_prefix(file_prefix)
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = build_msn_manual_total_export_packet(bundle=bundle, package_id=package_id or prefix)

    article_payload = bundle.article_text.encode("utf-8")
    comments_payload = _json_bytes({"comments": list(bundle.comments), "comment_count": bundle.comment_count}) if bundle.comment_count else b""
    bundle_payload = msn_manual_capture_bundle_to_json(bundle).encode("utf-8")
    manifest_payload = _json_bytes(packet.manifest)
    packet_payload = msn_manual_total_export_packet_to_json(packet).encode("utf-8")

    files: list[MSNManualTotalExportStoredFile] = [
        _write_bytes(output_dir, packet.article_text_file_name, article_payload, role="article_text"),
        _write_bytes(output_dir, packet.bundle_json_file_name, bundle_payload, role="capture_bundle_json"),
        _write_bytes(output_dir, packet.manifest_file_name, manifest_payload, role="total_export_manifest_json"),
        _write_bytes(output_dir, f"metadata/{packet.package_id}_msn_manual_total_export_packet.json", packet_payload, role="total_export_packet_json"),
    ]
    if packet.comments_json_file_name and comments_payload:
        files.append(_write_bytes(output_dir, packet.comments_json_file_name, comments_payload, role="comments_json"))

    return MSNManualTotalExportPackageStoreResult(
        schema_version=MSN_MANUAL_TOTAL_EXPORT_PACKAGE_STORE_SCHEMA_VERSION,
        package_id=packet.package_id,
        files=tuple(files),
        packet_sha256=_sha256_bytes(packet_payload),
        manifest_sha256=_sha256_bytes(manifest_payload),
    )


def msn_manual_total_export_package_store_result_to_json(result: MSNManualTotalExportPackageStoreResult) -> str:
    return _json_bytes(result.to_dict()).decode("utf-8")
