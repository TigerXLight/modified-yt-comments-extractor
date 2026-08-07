from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from capture_manual_live_smoke_approval_packet import (
    CaptureManualLiveSmokeApprovalPacket,
    capture_manual_live_smoke_approval_packet_to_json,
)


CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STORE_SCHEMA_VERSION = (
    "capture_manual_live_smoke_approval_packet_store_v1"
)
CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME = (
    "capture_manual_live_smoke_approval_packet.json"
)


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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacketStoredFile:
    filename: str
    file_role: str
    sha256: str
    byte_count: int
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STORE_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    full_local_path_serialized: bool = False
    live_network_request_performed: bool = False
    browser_automation_performed: bool = False
    screenshot_capture_performed: bool = False
    archive_submission_performed: bool = False
    media_download_performed: bool = False
    credential_value_read: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacketStoreResult:
    packet_id: str
    target_count: int
    source_schema_version: str
    files: tuple[CaptureManualLiveSmokeApprovalPacketStoredFile, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STORE_SCHEMA_VERSION
    output_directory_role: str = "user_selected_manual_smoke_approval_directory"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    runtime_execution_performed: bool = False
    live_network_request_performed: bool = False
    browser_automation_performed: bool = False
    screenshot_capture_performed: bool = False
    archive_submission_performed: bool = False
    media_download_performed: bool = False
    warc_or_wacz_capture_performed: bool = False
    archivebox_execution_performed: bool = False
    credential_value_read: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    file_movement_performed: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        payload = _value_for_dict(self)
        payload["file_count"] = self.file_count
        return payload


def build_capture_manual_live_smoke_approval_packet_store_payloads(
    packet: CaptureManualLiveSmokeApprovalPacket,
) -> dict[str, str]:
    return {
        CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME: (
            capture_manual_live_smoke_approval_packet_to_json(packet)
        )
    }


def write_capture_manual_live_smoke_approval_packet(
    packet: CaptureManualLiveSmokeApprovalPacket,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> CaptureManualLiveSmokeApprovalPacketStoreResult:
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    stored_files: list[CaptureManualLiveSmokeApprovalPacketStoredFile] = []
    for filename, payload_text in build_capture_manual_live_smoke_approval_packet_store_payloads(packet).items():
        file_path = output_path / filename
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing manual smoke approval file: {filename}")
        payload_bytes = payload_text.encode("utf-8")
        file_path.write_bytes(payload_bytes)
        stored_files.append(
            CaptureManualLiveSmokeApprovalPacketStoredFile(
                filename=filename,
                file_role=filename.removesuffix(".json"),
                sha256=_sha256_bytes(payload_bytes),
                byte_count=len(payload_bytes),
            )
        )
    return CaptureManualLiveSmokeApprovalPacketStoreResult(
        packet_id=packet.packet_id,
        target_count=packet.target_count,
        source_schema_version=packet.schema_version,
        files=tuple(stored_files),
    )


def capture_manual_live_smoke_approval_packet_store_result_to_json(
    result: CaptureManualLiveSmokeApprovalPacketStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
