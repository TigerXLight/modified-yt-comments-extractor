from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from capture_manual_live_smoke_action_execution_kit import (
    ManualLiveSmokeActionExecutionKit,
)


MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_STORE_SCHEMA_VERSION = "manual_live_smoke_action_execution_kit_store_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


@dataclass(frozen=True)
class ManualLiveSmokeActionExecutionKitStoredFile:
    file_name: str
    role: str
    sha256: str
    byte_count: int

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ManualLiveSmokeActionExecutionKitStoreResult:
    artifacts: tuple[ManualLiveSmokeActionExecutionKitStoredFile, ...]
    schema_version: str = MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_STORE_SCHEMA_VERSION
    implementation_bundle: bool = True
    local_only: bool = True
    output_directory_selected_by_user: bool = True
    full_local_path_serialized: bool = False
    raw_media_payload_included: bool = False
    credential_value_read: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def store_manual_live_smoke_action_execution_kit(
    *,
    output_directory: str | Path,
    kit: ManualLiveSmokeActionExecutionKit,
    allow_overwrite: bool = True,
) -> ManualLiveSmokeActionExecutionKitStoreResult:
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    artifacts: list[ManualLiveSmokeActionExecutionKitStoredFile] = []
    for kit_file in kit.files:
        destination = output_path / kit_file.file_name
        if destination.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {kit_file.file_name}")
        payload = kit_file.text.encode("utf-8")
        destination.write_bytes(payload)
        artifacts.append(
            ManualLiveSmokeActionExecutionKitStoredFile(
                file_name=kit_file.file_name,
                role=kit_file.role,
                sha256=hashlib.sha256(payload).hexdigest(),
                byte_count=len(payload),
            )
        )
    return ManualLiveSmokeActionExecutionKitStoreResult(artifacts=tuple(artifacts))


def manual_live_smoke_action_execution_kit_store_result_to_json(
    result: ManualLiveSmokeActionExecutionKitStoreResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
