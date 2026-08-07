from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from online_asr_keys_accounts_review_release_gate import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW,
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY,
    OnlineASRKeysAccountsReviewReleaseGateIssue,
    build_online_asr_keys_accounts_review_release_gate_report,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_release_section_closeout_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_NAME = (
    "Online ASR KEYS/ACCOUNTS review release gate"
)
REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS = (
    "online_asr_keys_accounts_review_closeout_cli_v1",
    "online_asr_keys_accounts_review_verifier_store_cli_v1",
    "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
    "online_asr_keys_accounts_review_safety_audit_store_cli_v1",
    "online_asr_keys_accounts_review_release_gate_store_cli_v1",
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
class OnlineASRKeysAccountsReviewReleaseSectionCloseoutReport:
    roadmap_section: str
    source_artifact_count: int
    review_verdict: str
    section_ready: bool
    issue_count: int
    issues: tuple[OnlineASRKeysAccountsReviewReleaseGateIssue, ...]
    required_schema_versions: tuple[str, ...]
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    coverage_component_count: int
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    next_actions: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_CLOSEOUT_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_shows_added_providers_only: bool = True
    add_provider_searches_full_catalog: bool = True
    online_asr_requires_explicit_provider_call_approval: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    raw_media_serialized: bool = False
    full_local_path_included: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                f"Roadmap section: {self.roadmap_section}",
                f"Review verdict: {self.review_verdict}",
                f"Section ready: {str(self.section_ready).lower()}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Component coverage: {self.coverage_component_count}/{len(self.required_schema_versions)}",
                f"Issue count: {self.issue_count}",
                f"Missing schema versions: {', '.join(self.missing_schema_versions) or 'none'}",
                f"Packages: {', '.join(self.package_ids) or 'none'}",
                f"Selected providers: {', '.join(self.selected_provider_ids) or 'none'}",
                "Next actions: " + ("; ".join(self.next_actions) or "none"),
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_release_section_closeout_report(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    required_schema_versions: Sequence[str] = REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_SCHEMAS,
) -> OnlineASRKeysAccountsReviewReleaseSectionCloseoutReport:
    """Build one metadata-only closeout report for the release-gate roadmap section.

    This is the larger section-level wrapper around the Online ASR KEYS/ACCOUNTS
    release-gate chain. It validates safe JSON artifacts only; it never reads
    credentials, calls providers, processes media, exposes full local paths, or
    claims completed/verified transcription.
    """
    release_gate_report = build_online_asr_keys_accounts_review_release_gate_report(
        artifacts,
        required_schema_versions=required_schema_versions,
    )
    section_ready = release_gate_report.release_gate_ready
    next_actions = (
        (
            "commit_and_push_release_section_closeout_metadata",
            "continue_with_next_roadmap_section_as_a_single_mega_patch",
        )
        if section_ready
        else (
            "review_release_section_issues_before_progressing",
            "rerun_metadata_only_safety_audit_after_corrections",
        )
    )
    return OnlineASRKeysAccountsReviewReleaseSectionCloseoutReport(
        roadmap_section=ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_SECTION_NAME,
        source_artifact_count=release_gate_report.source_artifact_count,
        review_verdict=(
            ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
            if section_ready
            else ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW
        ),
        section_ready=section_ready,
        issue_count=release_gate_report.issue_count,
        issues=release_gate_report.issues,
        required_schema_versions=tuple(required_schema_versions),
        observed_schema_versions=release_gate_report.observed_schema_versions,
        missing_schema_versions=release_gate_report.missing_schema_versions,
        coverage_component_count=release_gate_report.coverage_component_count,
        package_ids=release_gate_report.package_ids,
        selected_provider_ids=release_gate_report.selected_provider_ids,
        stored_file_names=release_gate_report.stored_file_names,
        stored_file_hashes=release_gate_report.stored_file_hashes,
        next_actions=next_actions,
    )


def online_asr_keys_accounts_review_release_section_closeout_report_to_json(
    report: OnlineASRKeysAccountsReviewReleaseSectionCloseoutReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
