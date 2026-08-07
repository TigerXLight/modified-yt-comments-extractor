from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_VERIFIER_SCHEMA_VERSION = (
    "capture_manual_live_smoke_observation_packet_verifier_v1"
)
REQUIRED_OBSERVATION_PACKET_SCHEMAS = (
    "capture_manual_live_smoke_observation_packet_v1",
    "capture_manual_live_smoke_observation_packet_store_cli_v1",
)


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservationPacketVerifierIssue:
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


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


def _iter_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            return (mapped,)
    if isinstance(value, Mapping):
        items: list[Mapping[str, Any]] = [value]
        for key in ("packet", "store_result", "verifier_report", "closeout_report"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                items.extend(_iter_mappings(nested))
        for key in ("artifacts", "source_artifacts"):
            nested_list = value.get(key)
            if isinstance(nested_list, Sequence) and not isinstance(nested_list, (str, bytes)):
                for item in nested_list:
                    if isinstance(item, Mapping):
                        items.extend(_iter_mappings(item))
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items: list[Mapping[str, Any]] = []
        for item in value:
            items.extend(_iter_mappings(item))
        return tuple(items)
    return ()


def _collect_schema_versions(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    versions = {str(item.get("schema_version")) for item in items if item.get("schema_version")}
    return tuple(sorted(versions))


def _flag_value(items: Sequence[Mapping[str, Any]], flag: str) -> bool:
    for item in items:
        if item.get(flag) is True:
            return True
    return False


def _collect_stored_names(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    names: set[str] = set()
    for item in items:
        for file_item in item.get("files", ()) or ():
            if isinstance(file_item, Mapping) and file_item.get("file_name"):
                names.add(str(file_item["file_name"]))
        for file_name in item.get("stored_file_names", ()) or ():
            if file_name:
                names.add(str(file_name))
    return tuple(sorted(names))


def _collect_hashes(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    hashes: set[str] = set()
    for item in items:
        for digest in item.get("stored_file_hashes", ()) or ():
            if digest:
                hashes.add(str(digest))
        for file_item in item.get("files", ()) or ():
            if isinstance(file_item, Mapping) and file_item.get("sha256"):
                hashes.add(str(file_item["sha256"]))
    return tuple(sorted(hashes))


def _collect_observation_names(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    names: set[str] = set()
    for item in items:
        observations = item.get("observations", ()) or ()
        if isinstance(observations, Sequence) and not isinstance(observations, (str, bytes)):
            for observation in observations:
                if isinstance(observation, Mapping):
                    site_id = observation.get("site_id")
                    action = observation.get("requested_action")
                    if site_id and action:
                        names.add(f"{site_id}:{action}")
    return tuple(sorted(names))


@dataclass(frozen=True)
class CaptureManualLiveSmokeObservationPacketVerifierReport:
    source_artifact_count: int
    observation_packet_ready_for_review: bool
    issue_count: int
    issues: tuple[CaptureManualLiveSmokeObservationPacketVerifierIssue, ...]
    required_schema_versions: tuple[str, ...]
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    observed_site_actions: tuple[str, ...]
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_VERIFIER_SCHEMA_VERSION
    review_status: str = "OPERATOR_OBSERVATION_REVIEW_REQUIRED"
    execution_mode: str = "MANUAL_OPERATOR_OBSERVATION_ONLY"
    metadata_only: bool = True
    local_only: bool = True
    user_review_required: bool = True
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
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Manual live smoke observation packet verifier",
                f"Ready for review: {str(self.observation_packet_ready_for_review).lower()}",
                f"Issue count: {self.issue_count}",
                f"Observed site actions: {', '.join(self.observed_site_actions) or 'none'}",
                "Tool live network request performed: false",
                "Completed capture claimed: false",
            )
        )


def verify_capture_manual_live_smoke_observation_packet(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    required_schema_versions: Sequence[str] = REQUIRED_OBSERVATION_PACKET_SCHEMAS,
) -> CaptureManualLiveSmokeObservationPacketVerifierReport:
    items = _iter_mappings(artifacts)
    if not items:
        raise ValueError("at least one observation artifact is required")
    observed = _collect_schema_versions(items)
    required = tuple(required_schema_versions)
    missing = tuple(schema for schema in required if schema not in observed)
    issues: list[CaptureManualLiveSmokeObservationPacketVerifierIssue] = []
    for schema in missing:
        issues.append(
            CaptureManualLiveSmokeObservationPacketVerifierIssue(
                code="missing_schema_version",
                message=f"Required schema version is missing: {schema}",
            )
        )
    unsafe_flags = (
        "automation_execution_performed_by_tool",
        "runtime_execution_performed_by_tool",
        "live_network_request_performed_by_tool",
        "browser_automation_performed_by_tool",
        "screenshot_capture_performed_by_tool",
        "archive_submission_performed_by_tool",
        "media_download_performed_by_tool",
        "warc_or_wacz_capture_performed_by_tool",
        "archivebox_execution_performed_by_tool",
        "credential_value_read_by_tool",
        "credential_value_read",
        "secret_value_recorded",
        "raw_media_payload_included",
        "full_local_path_serialized",
        "completed_capture_claimed",
        "verified_capture_claimed",
    )
    for flag in unsafe_flags:
        if _flag_value(items, flag):
            issues.append(
                CaptureManualLiveSmokeObservationPacketVerifierIssue(
                    code=f"unsafe_{flag}",
                    message=f"Unsafe flag must remain false: {flag}",
                )
            )
    observed_site_actions = _collect_observation_names(items)
    if not observed_site_actions:
        issues.append(
            CaptureManualLiveSmokeObservationPacketVerifierIssue(
                code="missing_observation_site_action",
                message="At least one named site/action observation is required.",
            )
        )
    return CaptureManualLiveSmokeObservationPacketVerifierReport(
        source_artifact_count=len(items),
        observation_packet_ready_for_review=not issues,
        issue_count=len(issues),
        issues=tuple(issues),
        required_schema_versions=required,
        observed_schema_versions=observed,
        missing_schema_versions=missing,
        observed_site_actions=observed_site_actions,
        stored_file_names=_collect_stored_names(items),
        stored_file_hashes=_collect_hashes(items),
    )


def capture_manual_live_smoke_observation_packet_verifier_report_to_json(
    report: CaptureManualLiveSmokeObservationPacketVerifierReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
