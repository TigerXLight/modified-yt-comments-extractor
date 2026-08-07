from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_SCHEMA_VERSION = (
    "capture_manual_live_smoke_approval_packet_v1"
)
CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STATUS_PENDING = "APPROVAL_REQUIRED"
CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_MODE = "MANUAL_OPERATOR_ONLY"


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
_DEFAULT_REQUIRED_APPROVALS = (
    "named_site",
    "named_operator_action",
    "manual_browser_or_archive_step",
    "output_directory",
    "no_secret_or_credential_material",
    "no_automatic_external_access",
)
_DEFAULT_DISALLOWED_ACTIONS = (
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


def _normalise_id(value: Any, *, field_name: str) -> str:
    text = _safe_text(value)
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > 160:
        raise ValueError(f"{field_name} is too long for a safe metadata field")
    return text


def _reject_unsafe_secret_keys(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = _safe_text(key).casefold()
            if (
                key_text in _UNSAFE_FIELD_NAMES
                or key_text.endswith("_secret")
                or key_text.endswith("_token")
            ):
                raise ValueError(
                    f"Refusing {source}: secret-like field '{key}' must not be included in a manual smoke approval packet"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalTarget:
    site_id: str
    display_name: str
    requested_action: str
    operator_notes: str = ""
    status: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STATUS_PENDING
    execution_mode: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_MODE
    named_site_required: bool = True
    named_action_required: bool = True
    explicit_user_approval_required: bool = True
    runtime_execution_performed: bool = False
    live_network_request_performed: bool = False
    browser_automation_performed: bool = False
    screenshot_capture_performed: bool = False
    archive_submission_performed: bool = False
    media_download_performed: bool = False
    warc_or_wacz_capture_performed: bool = False
    archivebox_execution_performed: bool = False
    credential_value_read: bool = False
    full_local_path_serialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacket:
    packet_id: str
    target_count: int
    targets: tuple[CaptureManualLiveSmokeApprovalTarget, ...]
    required_approvals: tuple[str, ...]
    disallowed_automatic_actions: tuple[str, ...]
    next_actions: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_SCHEMA_VERSION
    review_status: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STATUS_PENDING
    execution_mode: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_MODE
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    explicit_user_approval_required: bool = True
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
    user_folder_scan_performed: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Manual live smoke approval packet",
                f"Packet id: {self.packet_id}",
                f"Targets: {self.target_count}",
                f"Review status: {self.review_status}",
                f"Execution mode: {self.execution_mode}",
                "Runtime execution performed: false",
                "Live network request performed: false",
                "Browser automation performed: false",
                "Archive submission performed: false",
                "Credential value read: false",
                "Completed capture claimed: false",
            )
        )


def build_capture_manual_live_smoke_approval_packet(
    targets: Sequence[Mapping[str, Any]],
    *,
    packet_id: str = "manual-live-smoke-approval-packet",
    required_approvals: Sequence[str] = _DEFAULT_REQUIRED_APPROVALS,
    disallowed_automatic_actions: Sequence[str] = _DEFAULT_DISALLOWED_ACTIONS,
) -> CaptureManualLiveSmokeApprovalPacket:
    """Build a local-only manual smoke approval packet.

    The packet is deliberately only metadata. It does not open a browser, call a
    website, submit to archives, capture screenshots, download media, execute
    ArchiveBox, read credentials, move files, or claim a completed smoke test.
    """
    if not targets:
        raise ValueError("at least one manual smoke target is required")
    _reject_unsafe_secret_keys(targets, source="manual smoke targets")
    safe_targets: list[CaptureManualLiveSmokeApprovalTarget] = []
    for index, target in enumerate(targets, start=1):
        site_id = _normalise_id(target.get("site_id") or target.get("site"), field_name=f"target {index} site_id")
        display_name = _normalise_id(
            target.get("display_name") or target.get("name") or site_id,
            field_name=f"target {index} display_name",
        )
        requested_action = _normalise_id(
            target.get("requested_action") or target.get("action"),
            field_name=f"target {index} requested_action",
        )
        operator_notes = _safe_text(target.get("operator_notes") or target.get("notes"))
        safe_targets.append(
            CaptureManualLiveSmokeApprovalTarget(
                site_id=site_id,
                display_name=display_name,
                requested_action=requested_action,
                operator_notes=operator_notes,
            )
        )
    next_actions = (
        "review_named_site_and_action_scope",
        "confirm_manual_operator_only_execution_window",
        "select_output_directory_before_any_manual_artifact_export",
        "do_not_run_live_network_or_browser_steps_until_separate_approval",
    )
    return CaptureManualLiveSmokeApprovalPacket(
        packet_id=_normalise_id(packet_id, field_name="packet_id"),
        target_count=len(safe_targets),
        targets=tuple(safe_targets),
        required_approvals=tuple(_normalise_id(item, field_name="required_approval") for item in required_approvals),
        disallowed_automatic_actions=tuple(
            _normalise_id(item, field_name="disallowed_automatic_action")
            for item in disallowed_automatic_actions
        ),
        next_actions=next_actions,
    )


def capture_manual_live_smoke_approval_packet_to_json(
    packet: CaptureManualLiveSmokeApprovalPacket,
) -> str:
    return json.dumps(packet.to_dict(), indent=2, sort_keys=True) + "\n"
