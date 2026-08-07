from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from capture_manual_live_smoke_action_implementation import (
    get_manual_live_smoke_action_definition,
)


MANUAL_LIVE_SMOKE_ACTION_ARTIFACT_COLLECT_SCHEMA_VERSION = "manual_live_smoke_action_artifact_collect_v1"
MANUAL_LIVE_SMOKE_ACTION_OBSERVATION_DRAFT_SCHEMA_VERSION = "manual_live_smoke_action_observation_draft_v1"

_SECRET_KEY_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
_SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,180}$")


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
    return value


def _safe_text(value: Any, *, field_name: str, allow_empty: bool = False, max_length: int = 700) -> str:
    if _SECRET_KEY_RE.search(field_name):
        raise ValueError(f"secret-like field is not allowed: {field_name}")
    text = " ".join(str(value or "").replace("\x00", " ").split())
    if not text and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > max_length:
        raise ValueError(f"{field_name} is too long")
    if _SECRET_KEY_RE.search(text):
        raise ValueError(f"secret-like value is not allowed for {field_name}")
    if _FULL_PATH_RE.search(text):
        raise ValueError(f"full local path is not allowed for {field_name}")
    return text


def _safe_id(value: Any, *, field_name: str) -> str:
    text = _safe_text(value, field_name=field_name, max_length=140)
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"unsafe identifier for {field_name}: {value!r}")
    return text


def _safe_observation_display_name(value: Any) -> str:
    text = _safe_text(value, field_name="display_name")
    text = text.replace("/", " ").replace("\\", " ")
    return " ".join(text.split())


def _safe_file_name(path: Path) -> str:
    name = path.name
    if not _SAFE_FILE_RE.match(name) or name in {".", ".."}:
        raise ValueError(f"unsafe artifact file name: {name!r}")
    if any(separator in name for separator in ("/", "\\")) or ":" in name:
        raise ValueError(f"artifact file name must not include path separators: {name!r}")
    return name


@dataclass(frozen=True)
class ManualLiveSmokeActionArtifactInput:
    role: str
    source_path: Path


@dataclass(frozen=True)
class ManualLiveSmokeActionCollectedArtifact:
    file_name: str
    role: str
    sha256: str
    byte_count: int
    extension: str
    contract_required: bool
    full_local_path_serialized: bool = False
    raw_payload_included: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ManualLiveSmokeActionObservationDraft:
    site_id: str
    display_name: str
    requested_action: str
    operator_summary: str
    observed_artifacts: tuple[ManualLiveSmokeActionCollectedArtifact, ...]
    schema_version: str = MANUAL_LIVE_SMOKE_ACTION_OBSERVATION_DRAFT_SCHEMA_VERSION
    metadata_only: bool = True
    local_only: bool = True
    manual_operator_observation_supplied: bool = True
    user_review_required: bool = True
    operator_supplied_files_read: bool = True
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    credential_value_read: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_observation_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "display_name": self.display_name,
            "requested_action": self.requested_action,
            "operator_summary": self.operator_summary,
            "observed_artifacts": [artifact.to_dict() for artifact in self.observed_artifacts],
            "manual_operator_observation_supplied": True,
            "user_review_required": True,
            "completed_capture_claimed": False,
            "verified_capture_claimed": False,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = _value_for_dict(self)
        payload["observation_packet_input"] = self.to_observation_dict()
        return payload


def parse_manual_live_smoke_artifact_arg(value: str) -> ManualLiveSmokeActionArtifactInput:
    text = str(value or "")
    if "=" not in text:
        raise ValueError("artifact arguments must use role=file syntax")
    role_text, path_text = text.split("=", 1)
    role = _safe_id(role_text, field_name="artifact_role")
    if not path_text.strip():
        raise ValueError("artifact file path must not be empty")
    return ManualLiveSmokeActionArtifactInput(role=role, source_path=Path(path_text))


def _normalise_inputs(artifacts: Sequence[ManualLiveSmokeActionArtifactInput | str | Mapping[str, Any]]) -> tuple[ManualLiveSmokeActionArtifactInput, ...]:
    normalised: list[ManualLiveSmokeActionArtifactInput] = []
    for artifact in artifacts:
        if isinstance(artifact, ManualLiveSmokeActionArtifactInput):
            normalised.append(artifact)
        elif isinstance(artifact, str):
            normalised.append(parse_manual_live_smoke_artifact_arg(artifact))
        elif isinstance(artifact, Mapping):
            role = _safe_id(artifact.get("role") or artifact.get("artifact_role"), field_name="artifact_role")
            path_value = artifact.get("path") or artifact.get("source_path") or artifact.get("file")
            if not path_value:
                raise ValueError("artifact mapping must include path/source_path/file")
            normalised.append(ManualLiveSmokeActionArtifactInput(role=role, source_path=Path(str(path_value))))
        else:
            raise ValueError("artifact inputs must be role=file strings or artifact mappings")
    if not normalised:
        raise ValueError("at least one artifact must be supplied")
    return tuple(normalised)


def collect_manual_live_smoke_action_observation_draft(
    *,
    site_id: str,
    action_id: str,
    display_name: str | None = None,
    operator_summary: str,
    artifacts: Sequence[ManualLiveSmokeActionArtifactInput | str | Mapping[str, Any]],
) -> ManualLiveSmokeActionObservationDraft:
    definition = get_manual_live_smoke_action_definition(site_id, action_id)
    artifact_inputs = _normalise_inputs(artifacts)
    contracts = {contract.role: contract for contract in definition.artifact_contracts}
    collected: list[ManualLiveSmokeActionCollectedArtifact] = []
    for artifact in artifact_inputs:
        if artifact.role not in contracts:
            raise ValueError(f"artifact role is not accepted for {definition.action_id}: {artifact.role}")
        source_path = artifact.source_path
        if not source_path.is_file():
            raise ValueError(f"artifact path must name an existing file for role {artifact.role}")
        file_name = _safe_file_name(source_path)
        extension = source_path.suffix.lower().lstrip(".")
        contract = contracts[artifact.role]
        if contract.allowed_extensions and extension not in contract.allowed_extensions:
            allowed = ", ".join(contract.allowed_extensions)
            raise ValueError(f"artifact {file_name!r} extension {extension!r} is not allowed for {artifact.role}; allowed: {allowed}")
        data = source_path.read_bytes()
        collected.append(
            ManualLiveSmokeActionCollectedArtifact(
                file_name=file_name,
                role=artifact.role,
                sha256=hashlib.sha256(data).hexdigest(),
                byte_count=len(data),
                extension=extension,
                contract_required=bool(contract.required),
            )
        )
    return ManualLiveSmokeActionObservationDraft(
        site_id=definition.site_id,
        display_name=_safe_observation_display_name(display_name or definition.site_label),
        requested_action=definition.action_id,
        operator_summary=_safe_text(operator_summary, field_name="operator_summary"),
        observed_artifacts=tuple(collected),
    )


def manual_live_smoke_action_observation_draft_to_json(draft: ManualLiveSmokeActionObservationDraft) -> str:
    return json.dumps(draft.to_dict(), indent=2, sort_keys=True) + "\n"
