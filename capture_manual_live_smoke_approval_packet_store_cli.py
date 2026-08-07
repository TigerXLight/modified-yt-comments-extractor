from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from capture_manual_live_smoke_approval_packet import (
    build_capture_manual_live_smoke_approval_packet,
)
from capture_manual_live_smoke_approval_packet_store import (
    write_capture_manual_live_smoke_approval_packet,
)


CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STORE_CLI_SCHEMA_VERSION = (
    "capture_manual_live_smoke_approval_packet_store_cli_v1"
)
_UNSAFE_INPUT_KEYS = frozenset(
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


class CaptureManualLiveSmokeApprovalPacketStoreCLIError(ValueError):
    pass


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


def _reject_unsafe_secret_keys(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = _safe_text(key).casefold()
            if (
                key_text in _UNSAFE_INPUT_KEYS
                or key_text.endswith("_secret")
                or key_text.endswith("_token")
            ):
                raise CaptureManualLiveSmokeApprovalPacketStoreCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _load_targets_json(path: str | Path) -> tuple[dict[str, Any], ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_unsafe_secret_keys(data, source="targets JSON")
    if isinstance(data, Mapping):
        targets = data.get("targets")
    else:
        targets = data
    if not isinstance(targets, list):
        raise CaptureManualLiveSmokeApprovalPacketStoreCLIError(
            "targets JSON must be either a list or an object with a targets list"
        )
    if not all(isinstance(target, Mapping) for target in targets):
        raise CaptureManualLiveSmokeApprovalPacketStoreCLIError("each target must be a JSON object")
    return tuple(dict(target) for target in targets)


def _target_from_arg(text: str) -> dict[str, str]:
    parts = text.split("|", 2)
    if len(parts) < 2:
        raise CaptureManualLiveSmokeApprovalPacketStoreCLIError(
            "--target must be formatted as site_id|requested_action or site_id|requested_action|display_name"
        )
    site_id, requested_action = parts[0], parts[1]
    display_name = parts[2] if len(parts) == 3 else parts[0]
    return {
        "site_id": site_id,
        "display_name": display_name,
        "requested_action": requested_action,
    }


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacketStoreCLIResult:
    packet_id: str
    target_count: int
    packet_schema_version: str
    store_schema_version: str
    stored_file_count: int
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    required_approvals: tuple[str, ...]
    disallowed_automatic_actions: tuple[str, ...]
    next_actions: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_STORE_CLI_SCHEMA_VERSION
    review_status: str = "APPROVAL_REQUIRED"
    execution_mode: str = "MANUAL_OPERATOR_ONLY"
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
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Manual live smoke approval packet store CLI",
                f"Packet id: {self.packet_id}",
                f"Targets: {self.target_count}",
                f"Stored files: {self.stored_file_count}",
                "Review status: APPROVAL_REQUIRED",
                "Execution mode: MANUAL_OPERATOR_ONLY",
                "Live network request performed: false",
                "Browser automation performed: false",
                "Credential value read: false",
                "Completed capture claimed: false",
            )
        )


def build_capture_manual_live_smoke_approval_packet_store_cli_result(
    targets: Sequence[Mapping[str, Any]],
    output_directory: str | Path,
    *,
    packet_id: str = "manual-live-smoke-approval-packet",
    allow_overwrite: bool = True,
) -> CaptureManualLiveSmokeApprovalPacketStoreCLIResult:
    if not targets:
        raise CaptureManualLiveSmokeApprovalPacketStoreCLIError("at least one target is required")
    normalised = tuple(dict(target) for target in targets)
    _reject_unsafe_secret_keys(normalised, source="target metadata")
    packet = build_capture_manual_live_smoke_approval_packet(normalised, packet_id=packet_id)
    store_result = write_capture_manual_live_smoke_approval_packet(
        packet,
        output_directory,
        allow_overwrite=allow_overwrite,
    )
    files = tuple(store_result.files)
    return CaptureManualLiveSmokeApprovalPacketStoreCLIResult(
        packet_id=packet.packet_id,
        target_count=packet.target_count,
        packet_schema_version=packet.schema_version,
        store_schema_version=store_result.schema_version,
        stored_file_count=store_result.file_count,
        stored_file_names=tuple(file.filename for file in files),
        stored_file_hashes=tuple(file.sha256 for file in files),
        required_approvals=packet.required_approvals,
        disallowed_automatic_actions=packet.disallowed_automatic_actions,
        next_actions=packet.next_actions,
    )


def capture_manual_live_smoke_approval_packet_store_cli_result_to_json(
    result: CaptureManualLiveSmokeApprovalPacketStoreCLIResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"


def run_capture_manual_live_smoke_approval_packet_store_cli(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only manual live smoke approval packet without executing live actions."
    )
    parser.add_argument("--packet-id", default="manual-live-smoke-approval-packet")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--targets-json")
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    try:
        targets: list[dict[str, Any]] = []
        targets.extend(_target_from_arg(item) for item in args.target)
        if args.targets_json:
            targets.extend(_load_targets_json(args.targets_json))
        result = build_capture_manual_live_smoke_approval_packet_store_cli_result(
            targets,
            args.output_directory,
            packet_id=args.packet_id,
            allow_overwrite=not args.no_overwrite,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2
    print(result.to_summary_text() if args.summary else capture_manual_live_smoke_approval_packet_store_cli_result_to_json(result), file=stdout, end="\n" if args.summary else "")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_capture_manual_live_smoke_approval_packet_store_cli())
