from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_VERIFIER_SCHEMA_VERSION = (
    "capture_manual_live_smoke_approval_packet_verifier_v1"
)
REQUIRED_APPROVAL_PACKET_SCHEMAS = (
    "capture_manual_live_smoke_approval_packet_v1",
    "capture_manual_live_smoke_approval_packet_store_cli_v1",
)


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacketVerifierIssue:
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


def _iter_mappings(items: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    if isinstance(items, Mapping):
        return (items,)
    return tuple(item for item in items if isinstance(item, Mapping))


def _collect_schema_versions(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    versions: set[str] = set()
    for item in items:
        schema_version = item.get("schema_version")
        if isinstance(schema_version, str) and schema_version:
            versions.add(schema_version)
        for file_item in item.get("files", ()) or ():
            if isinstance(file_item, Mapping):
                file_schema = file_item.get("schema_version")
                if isinstance(file_schema, str) and file_schema:
                    versions.add(file_schema)
    return tuple(sorted(versions))


def _flag_value(items: Sequence[Mapping[str, Any]], flag_name: str) -> bool:
    for item in items:
        if item.get(flag_name) is True:
            return True
        for target in item.get("targets", ()) or ():
            if isinstance(target, Mapping) and target.get(flag_name) is True:
                return True
    return False


def _stored_names(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    names: set[str] = set()
    for item in items:
        for key in ("stored_file_names", "file_names"):
            for name in item.get(key, ()) or ():
                if isinstance(name, str) and name:
                    names.add(name)
        for file_item in item.get("files", ()) or ():
            if isinstance(file_item, Mapping):
                name = file_item.get("filename")
                if isinstance(name, str) and name:
                    names.add(name)
    return tuple(sorted(names))


def _stored_hashes(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    hashes: set[str] = set()
    for item in items:
        for key in ("stored_file_hashes", "file_hashes"):
            for digest in item.get(key, ()) or ():
                if isinstance(digest, str) and digest:
                    hashes.add(digest)
        for file_item in item.get("files", ()) or ():
            if isinstance(file_item, Mapping):
                digest = file_item.get("sha256")
                if isinstance(digest, str) and digest:
                    hashes.add(digest)
    return tuple(sorted(hashes))


@dataclass(frozen=True)
class CaptureManualLiveSmokeApprovalPacketVerifierReport:
    source_artifact_count: int
    approval_packet_ready_for_user_review: bool
    issue_count: int
    issues: tuple[CaptureManualLiveSmokeApprovalPacketVerifierIssue, ...]
    required_schema_versions: tuple[str, ...]
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_VERIFIER_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_mode: str = "MANUAL_OPERATOR_ONLY"
    metadata_only: bool = True
    local_only: bool = True
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
                "Manual live smoke approval packet verifier",
                f"Ready for user review: {str(self.approval_packet_ready_for_user_review).lower()}",
                f"Issue count: {self.issue_count}",
                f"Missing schema versions: {', '.join(self.missing_schema_versions) or 'none'}",
                "Execution mode: MANUAL_OPERATOR_ONLY",
                "Live network request performed: false",
                "Completed capture claimed: false",
            )
        )


def verify_capture_manual_live_smoke_approval_packet(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    required_schema_versions: Sequence[str] = REQUIRED_APPROVAL_PACKET_SCHEMAS,
) -> CaptureManualLiveSmokeApprovalPacketVerifierReport:
    items = _iter_mappings(artifacts)
    if not items:
        raise ValueError("at least one approval packet artifact is required")
    observed = _collect_schema_versions(items)
    required = tuple(required_schema_versions)
    missing = tuple(schema for schema in required if schema not in observed)
    issues: list[CaptureManualLiveSmokeApprovalPacketVerifierIssue] = []
    for schema in missing:
        issues.append(
            CaptureManualLiveSmokeApprovalPacketVerifierIssue(
                code="missing_schema_version",
                message=f"Required schema version is missing: {schema}",
            )
        )
    dangerous_flags = (
        "runtime_execution_performed",
        "live_network_request_performed",
        "browser_automation_performed",
        "screenshot_capture_performed",
        "archive_submission_performed",
        "media_download_performed",
        "warc_or_wacz_capture_performed",
        "archivebox_execution_performed",
        "credential_value_read",
        "secret_value_recorded",
        "raw_media_payload_included",
        "full_local_path_serialized",
        "completed_capture_claimed",
        "verified_capture_claimed",
    )
    for flag in dangerous_flags:
        if _flag_value(items, flag):
            issues.append(
                CaptureManualLiveSmokeApprovalPacketVerifierIssue(
                    code=f"unsafe_{flag}",
                    message=f"Unsafe flag must remain false: {flag}",
                )
            )
    return CaptureManualLiveSmokeApprovalPacketVerifierReport(
        source_artifact_count=len(items),
        approval_packet_ready_for_user_review=not issues,
        issue_count=len(issues),
        issues=tuple(issues),
        required_schema_versions=required,
        observed_schema_versions=observed,
        missing_schema_versions=missing,
        stored_file_names=_stored_names(items),
        stored_file_hashes=_stored_hashes(items),
    )


def capture_manual_live_smoke_approval_packet_verifier_report_to_json(
    report: CaptureManualLiveSmokeApprovalPacketVerifierReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
