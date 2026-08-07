from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from capture_manual_live_smoke_observation_packet import (
    CaptureManualLiveSmokeObservationPacket,
    capture_manual_live_smoke_observation_packet_to_json,
)


CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_STORE_SCHEMA_VERSION = (
    "capture_manual_live_smoke_observation_packet_store_v1"
)
CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME = (
    "capture_manual_live_smoke_observation_packet.json"
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


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservationPacketStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservationPacketStoreResult:
    files: tuple[CaptureManualLiveSmokeObservationPacketStoredFile, ...]
    output_directory_selected_by_user: bool = True
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_STORE_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    full_local_path_serialized: bool = False
    credential_value_read: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_capture_manual_live_smoke_observation_packet_store_payloads(
    packet: CaptureManualLiveSmokeObservationPacket,
) -> dict[str, str]:
    return {
        CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME: (
            capture_manual_live_smoke_observation_packet_to_json(packet)
        )
    }


def write_capture_manual_live_smoke_observation_packet(
    packet: CaptureManualLiveSmokeObservationPacket,
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> CaptureManualLiveSmokeObservationPacketStoreResult:
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    payloads = build_capture_manual_live_smoke_observation_packet_store_payloads(packet)
    stored_files: list[CaptureManualLiveSmokeObservationPacketStoredFile] = []
    for file_name, text in sorted(payloads.items()):
        destination = output_path / file_name
        if destination.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {file_name}")
        payload_bytes = text.encode("utf-8")
        destination.write_bytes(payload_bytes)
        stored_files.append(
            CaptureManualLiveSmokeObservationPacketStoredFile(
                file_name=file_name,
                role="manual_live_smoke_observation_packet",
                sha256=hashlib.sha256(payload_bytes).hexdigest(),
                byte_count=len(payload_bytes),
            )
        )
    return CaptureManualLiveSmokeObservationPacketStoreResult(files=tuple(stored_files))


def capture_manual_live_smoke_observation_packet_store_result_to_json(
    result: CaptureManualLiveSmokeObservationPacketStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
