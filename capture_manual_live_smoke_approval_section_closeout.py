from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from capture_manual_live_smoke_approval_packet_verifier import (
    CaptureManualLiveSmokeApprovalPacketVerifierIssue,
    verify_capture_manual_live_smoke_approval_packet,
)


CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_SECTION_CLOSEOUT_SCHEMA_VERSION = (
    "capture_manual_live_smoke_approval_section_closeout_v1"
)
CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_SECTION_NAME = (
    "REV4 manual live site-smoke approval boundary"
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
class CaptureManualLiveSmokeApprovalSectionCloseoutReport:
    roadmap_section: str
    source_artifact_count: int
    section_ready_for_manual_review: bool
    issue_count: int
    issues: tuple[CaptureManualLiveSmokeApprovalPacketVerifierIssue, ...]
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    next_actions: tuple[str, ...]
    schema_version: str = CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_SECTION_CLOSEOUT_SCHEMA_VERSION
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
                f"Roadmap section: {self.roadmap_section}",
                f"Ready for manual review: {str(self.section_ready_for_manual_review).lower()}",
                f"Issue count: {self.issue_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution mode: MANUAL_OPERATOR_ONLY",
                "No live site-smoke execution is claimed by this closeout.",
            )
        )


def build_capture_manual_live_smoke_approval_section_closeout_report(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> CaptureManualLiveSmokeApprovalSectionCloseoutReport:
    verifier_report = verify_capture_manual_live_smoke_approval_packet(artifacts)
    next_actions = (
        (
            "review_manual_packet_with_named_sites_and_actions",
            "request_separate_user_approval_before_any_live_or_manual_site_smoke",
            "keep all live execution outside automatic tests and default app startup",
        )
        if verifier_report.approval_packet_ready_for_user_review
        else (
            "fix_manual_approval_packet_issues",
            "rerun_local_metadata_only_verifier",
        )
    )
    return CaptureManualLiveSmokeApprovalSectionCloseoutReport(
        roadmap_section=CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_SECTION_NAME,
        source_artifact_count=verifier_report.source_artifact_count,
        section_ready_for_manual_review=verifier_report.approval_packet_ready_for_user_review,
        issue_count=verifier_report.issue_count,
        issues=verifier_report.issues,
        observed_schema_versions=verifier_report.observed_schema_versions,
        missing_schema_versions=verifier_report.missing_schema_versions,
        stored_file_names=verifier_report.stored_file_names,
        stored_file_hashes=verifier_report.stored_file_hashes,
        next_actions=next_actions,
    )


def capture_manual_live_smoke_approval_section_closeout_report_to_json(
    report: CaptureManualLiveSmokeApprovalSectionCloseoutReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
