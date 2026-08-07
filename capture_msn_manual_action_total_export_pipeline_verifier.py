from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERIFIER_SCHEMA_VERSION = "msn_manual_action_total_export_pipeline_verifier_v1"
MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERDICT_READY = "MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_READY_FOR_REVIEW"
MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERDICT_NEEDS_REVIEW = "MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_NEEDS_REVIEW"
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)


@dataclass(frozen=True)
class MSNManualActionTotalExportPipelineVerificationIssue:
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualActionTotalExportPipelineVerificationReport:
    schema_version: str
    verdict: str
    issues: tuple[MSNManualActionTotalExportPipelineVerificationIssue, ...]
    package_id: str
    action_kit_file_count: int
    total_export_file_count: int
    comment_count: int
    ready_for_total_export_review: bool
    full_local_path_serialized: bool = False
    secret_like_value_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _iter_string_values(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_string_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_string_values(item)


def _contains_path_or_secret(value: Any) -> tuple[bool, bool]:
    strings = list(_iter_string_values(value))
    return any(_FULL_PATH_RE.search(text) for text in strings), any(_SECRET_RE.search(text) for text in strings)


def verify_msn_manual_action_total_export_pipeline_payload(payload: Mapping[str, Any]) -> MSNManualActionTotalExportPipelineVerificationReport:
    issues: list[MSNManualActionTotalExportPipelineVerificationIssue] = []
    if payload.get("pipeline_implemented") is not True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("pipeline_not_implemented", "Pipeline implementation flag is not true."))
    if payload.get("generated_operator_action_kits") is not True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("missing_action_kits", "Operator action kits were not generated."))
    if payload.get("explicit_operator_artifact_files_read") is not True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("artifacts_not_read", "Explicit operator artifact files were not read."))
    if payload.get("total_export_package_written") is not True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("package_not_written", "Total Export package was not written."))
    if int(payload.get("action_kit_file_count") or 0) <= 0:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("empty_action_kit", "Action kit has no files."))
    if int(payload.get("total_export_file_count") or 0) < 4:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("too_few_total_export_files", "Total Export package file count is too low."))
    if payload.get("completed_capture_claimed") is True or payload.get("verified_capture_claimed") is True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("unsafe_capture_claim", "Pipeline must not claim completed or verified capture."))
    total_export_report = payload.get("total_export_verification_report") if isinstance(payload.get("total_export_verification_report"), Mapping) else {}
    if total_export_report.get("ready_for_total_export_review") is not True:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("total_export_not_ready", "Nested Total Export verifier is not review-ready."))
    has_path, has_secret = _contains_path_or_secret(payload)
    if has_path:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("full_path_serialized", "Pipeline payload serialized a full local path."))
    if has_secret:
        issues.append(MSNManualActionTotalExportPipelineVerificationIssue("secret_like_value", "Pipeline payload serialized a secret-like value."))
    verdict = MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERDICT_READY if not issues else MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERDICT_NEEDS_REVIEW
    return MSNManualActionTotalExportPipelineVerificationReport(
        schema_version=MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issues=tuple(issues),
        package_id=str(payload.get("package_id", "")),
        action_kit_file_count=int(payload.get("action_kit_file_count") or 0),
        total_export_file_count=int(payload.get("total_export_file_count") or 0),
        comment_count=int(payload.get("comment_count") or 0),
        ready_for_total_export_review=not issues,
        full_local_path_serialized=has_path,
        secret_like_value_serialized=has_secret,
    )


def msn_manual_action_total_export_pipeline_verification_report_to_json(report: MSNManualActionTotalExportPipelineVerificationReport) -> str:
    return json.dumps(report.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
