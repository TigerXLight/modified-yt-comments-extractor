from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_SCHEMA_VERSION = (
    "capture_manual_live_smoke_observation_packet_v1"
)
CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_MODE = "MANUAL_OPERATOR_OBSERVATION_ONLY"
CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_STATUS = "OPERATOR_OBSERVATION_REVIEW_REQUIRED"

_UNSAFE_FIELD_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "client_secret",
        "credential",
        "credential_value",
        "key",
        "key_value",
        "password",
        "secret",
        "secret_value",
        "token",
    }
)
_DEFAULT_REQUIRED_REVIEW_STEPS = (
    "named_site_and_action_match_approval_packet",
    "operator_supplied_metadata_review",
    "safe_artifact_name_and_hash_review",
    "no_secret_or_credential_material",
    "no_raw_media_or_full_local_paths",
    "no_completed_or_verified_capture_claims",
)
_DEFAULT_DISALLOWED_AUTOMATION = (
    "automatic_live_http_fetch",
    "automatic_browser_automation",
    "automatic_screenshot_capture",
    "automatic_archive_submission",
    "automatic_media_download",
    "automatic_warc_or_wacz_capture",
    "automatic_archivebox_execution",
    "credential_read_or_provider_call",
    "file_movement_or_user_folder_scan",
)
_HEX_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


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


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())


def _normalise_id(value: Any, *, field_name: str, max_length: int = 180) -> str:
    text = _safe_text(value)
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > max_length:
        raise ValueError(f"{field_name} is too long for a safe metadata field")
    _reject_full_local_path_text(text, field_name=field_name)
    return text


def _reject_full_local_path_text(text: str, *, field_name: str) -> None:
    if _WINDOWS_DRIVE_RE.match(text) or text.startswith("/mnt/") or text.startswith("/home/"):
        raise ValueError(f"{field_name} must not include a full local path")
    if "\\" in text or "/" in text:
        raise ValueError(f"{field_name} must not include path separators")


def _normalise_free_note(value: Any, *, field_name: str, max_length: int = 600) -> str:
    text = _safe_text(value)
    if len(text) > max_length:
        raise ValueError(f"{field_name} is too long for a safe note field")
    if _WINDOWS_DRIVE_RE.search(text) or "/mnt/" in text or "/home/" in text:
        raise ValueError(f"{field_name} must not include full local paths")
    return text


def _normalise_filename(value: Any, *, field_name: str) -> str:
    text = _normalise_id(value, field_name=field_name, max_length=180)
    if text in {".", ".."}:
        raise ValueError(f"{field_name} must be a safe file name")
    if ":" in text:
        raise ValueError(f"{field_name} must not include drive or URI separators")
    return text


def _normalise_sha256(value: Any, *, field_name: str) -> str:
    text = _safe_text(value).lower()
    if not _HEX_SHA256_RE.match(text):
        raise ValueError(f"{field_name} must be a 64-character SHA-256 hex digest")
    return text


def _normalise_non_negative_int(value: Any, *, field_name: str) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a non-negative integer") from exc
    if integer < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return integer


def _reject_unsafe_secret_keys(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = _safe_text(key).casefold()
            if (
                key_text in _UNSAFE_FIELD_NAMES
                or key_text.endswith("_secret")
                or key_text.endswith("_token")
                or key_text.endswith("_key")
            ):
                raise ValueError(
                    f"Refusing {source}: secret-like field '{key}' must not be included in a manual smoke observation packet"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservedArtifact:
    file_name: str
    sha256: str
    byte_count: int
    role: str
    full_local_path_serialized: bool = False
    raw_payload_included: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservation:
    site_id: str
    display_name: str
    requested_action: str
    observation_status: str
    operator_summary: str
    observed_artifacts: tuple[CaptureManualLiveSmokeObservedArtifact, ...]
    manual_operator_observation_supplied: bool = True
    user_review_required: bool = True
    automation_execution_performed_by_tool: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    screenshot_capture_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    warc_or_wacz_capture_performed_by_tool: bool = False
    archivebox_execution_performed_by_tool: bool = False
    credential_value_read_by_tool: bool = False
    full_local_path_serialized: bool = False
    raw_media_payload_included: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservationPacket:
    packet_id: str
    observation_count: int
    observations: tuple[CaptureManualLiveSmokeObservation, ...]
    required_review_steps: tuple[str, ...]
    disallowed_automation: tuple[str, ...]
    next_actions: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_SCHEMA_VERSION
    review_status: str = CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_STATUS
    execution_mode: str = CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_MODE
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    user_review_required: bool = True
    manual_operator_observation_supplied: bool = True
    automation_execution_performed_by_tool: bool = False
    runtime_execution_performed_by_tool: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    screenshot_capture_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    warc_or_wacz_capture_performed_by_tool: bool = False
    archivebox_execution_performed_by_tool: bool = False
    credential_value_read_by_tool: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    file_movement_performed_by_tool: bool = False
    user_folder_scan_performed_by_tool: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Manual live smoke observation packet",
                f"Packet id: {self.packet_id}",
                f"Observations: {self.observation_count}",
                f"Review status: {self.review_status}",
                f"Execution mode: {self.execution_mode}",
                "Tool live network request performed: false",
                "Tool browser automation performed: false",
                "Tool credential value read: false",
                "Completed capture claimed: false",
            )
        )


def _build_observed_artifacts(
    artifacts: Sequence[Mapping[str, Any]], *, observation_index: int
) -> tuple[CaptureManualLiveSmokeObservedArtifact, ...]:
    safe_artifacts: list[CaptureManualLiveSmokeObservedArtifact] = []
    for artifact_index, artifact in enumerate(artifacts, start=1):
        safe_artifacts.append(
            CaptureManualLiveSmokeObservedArtifact(
                file_name=_normalise_filename(
                    artifact.get("file_name") or artifact.get("name"),
                    field_name=f"observation {observation_index} artifact {artifact_index} file_name",
                ),
                sha256=_normalise_sha256(
                    artifact.get("sha256") or artifact.get("hash"),
                    field_name=f"observation {observation_index} artifact {artifact_index} sha256",
                ),
                byte_count=_normalise_non_negative_int(
                    artifact.get("byte_count", 0),
                    field_name=f"observation {observation_index} artifact {artifact_index} byte_count",
                ),
                role=_normalise_id(
                    artifact.get("role") or artifact.get("artifact_role") or "manual_observation_support",
                    field_name=f"observation {observation_index} artifact {artifact_index} role",
                ),
            )
        )
    return tuple(safe_artifacts)


def build_capture_manual_live_smoke_observation_packet(
    observations: Sequence[Mapping[str, Any]],
    *,
    packet_id: str = "manual-live-smoke-observation-packet",
    required_review_steps: Sequence[str] = _DEFAULT_REQUIRED_REVIEW_STEPS,
    disallowed_automation: Sequence[str] = _DEFAULT_DISALLOWED_AUTOMATION,
) -> CaptureManualLiveSmokeObservationPacket:
    """Build a local-only manual smoke observation packet.

    The builder only records operator-supplied metadata and safe artifact names,
    hashes, byte counts, and roles. It does not fetch URLs, drive a browser,
    take screenshots, submit archives, download media, read credentials, move
    files, scan folders, or claim a completed/verified capture.
    """
    if not observations:
        raise ValueError("at least one manual smoke observation is required")
    _reject_unsafe_secret_keys(observations, source="manual smoke observations")
    safe_observations: list[CaptureManualLiveSmokeObservation] = []
    for index, observation in enumerate(observations, start=1):
        observed_artifacts = observation.get("observed_artifacts") or observation.get("artifacts") or ()
        if not isinstance(observed_artifacts, Sequence) or isinstance(observed_artifacts, (str, bytes)):
            raise ValueError(f"observation {index} observed_artifacts must be a list of metadata objects")
        safe_observations.append(
            CaptureManualLiveSmokeObservation(
                site_id=_normalise_id(
                    observation.get("site_id") or observation.get("site"),
                    field_name=f"observation {index} site_id",
                ),
                display_name=_normalise_id(
                    observation.get("display_name") or observation.get("name") or observation.get("site_id"),
                    field_name=f"observation {index} display_name",
                ),
                requested_action=_normalise_id(
                    observation.get("requested_action") or observation.get("action"),
                    field_name=f"observation {index} requested_action",
                ),
                observation_status=_normalise_id(
                    observation.get("observation_status") or CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_STATUS,
                    field_name=f"observation {index} observation_status",
                ),
                operator_summary=_normalise_free_note(
                    observation.get("operator_summary") or observation.get("summary"),
                    field_name=f"observation {index} operator_summary",
                ),
                observed_artifacts=_build_observed_artifacts(
                    tuple(item for item in observed_artifacts if isinstance(item, Mapping)),
                    observation_index=index,
                ),
            )
        )
    next_actions = (
        "review_operator_observation_metadata_against_approval_packet",
        "review_safe_artifact_names_hashes_and_roles",
        "do_not_mark_capture_complete_until_separate_manual_review_accepts_results",
        "keep live execution outside automatic tests and default app startup",
    )
    return CaptureManualLiveSmokeObservationPacket(
        packet_id=_normalise_id(packet_id, field_name="packet_id"),
        observation_count=len(safe_observations),
        observations=tuple(safe_observations),
        required_review_steps=tuple(_normalise_id(item, field_name="required_review_step") for item in required_review_steps),
        disallowed_automation=tuple(_normalise_id(item, field_name="disallowed_automation") for item in disallowed_automation),
        next_actions=next_actions,
    )


def capture_manual_live_smoke_observation_packet_to_json(
    packet: CaptureManualLiveSmokeObservationPacket,
) -> str:
    return json.dumps(packet.to_dict(), indent=2, sort_keys=True) + "\n"
