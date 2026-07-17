from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from capture_contracts import (
    ARTIFACT_TYPE_ARCHIVE_RESULT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_MEDIA_INVENTORY,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_RENDERED_RECORDING,
    ARTIFACT_TYPE_WACZ,
    ARTIFACT_TYPE_WARC,
    stable_capture_id,
)


LIVE_SMOKE_PLAN_SCHEMA_VERSION = "rev4.live-smoke-plan.v1"

APPROVAL_STATUS_NOT_APPROVED = "not_approved"
APPROVAL_STATUS_APPROVAL_REQUIRED = "approval_required"
APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY = "approved_for_manual_operator_only"

SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER = "APPROVAL_REQUIRED_SOURCE_URL"
SITE_LABEL_APPROVAL_REQUIRED_PLACEHOLDER = "APPROVAL_REQUIRED_SITE_LABEL"
APPROVER_METADATA_REQUIRED_PLACEHOLDER = "APPROVER_METADATA_REQUIRED"

_PLACEHOLDER_VALUES = {
    "",
    "approval_required",
    "approval_required_source_url",
    "approval_required_site_label",
    "approver_metadata_required",
    "placeholder",
    "source_url_placeholder",
    "tbd",
    "to_be_approved",
    "unknown",
}

MANUAL_ACTION_SCOPE_WEBPAGE = "webpage_manual_review"
MANUAL_ACTION_SCOPE_COMMENTS = "comments_manual_review"
MANUAL_ACTION_SCOPE_LIVECHAT = "livechat_manual_review"
MANUAL_ACTION_SCOPE_MEDIA = "media_manual_review"
MANUAL_ACTION_SCOPE_RENDERED_CITATION = "rendered_citation_manual_note"
MANUAL_ACTION_SCOPE_ARCHIVE = "archive_manual_note"
MANUAL_ACTION_SCOPE_WARC_WACZ = "warc_wacz_manual_note"
MANUAL_ACTION_SCOPE_EXPORT_QUEUE = "export_queue_metadata_review"

MANUAL_ACTION_SCOPE_IDS = (
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_LIVECHAT,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_RENDERED_CITATION,
    MANUAL_ACTION_SCOPE_ARCHIVE,
    MANUAL_ACTION_SCOPE_WARC_WACZ,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
)

LIVE_SMOKE_STATUS_DRAFT = "draft"
LIVE_SMOKE_STATUS_APPROVAL_REQUIRED = "approval_required"
LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY = "approved_for_manual_operator_only"
LIVE_SMOKE_STATUS_BLOCKED = "blocked"
LIVE_SMOKE_STATUS_COMPLETED_MANUALLY = "completed_manually"

LIVE_SMOKE_STATUSES = (
    LIVE_SMOKE_STATUS_DRAFT,
    LIVE_SMOKE_STATUS_APPROVAL_REQUIRED,
    LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
    LIVE_SMOKE_STATUS_BLOCKED,
    LIVE_SMOKE_STATUS_COMPLETED_MANUALLY,
)

LIVE_SMOKE_SCOPE = (
    "manual live-site smoke planning scaffold only; no live site access, browser, "
    "archive provider, download, screenshot, WARC/WACZ capture, ArchiveBox, "
    "credential, cookie, provider/network call, file move, broad scan, or "
    "automatic classification behavior"
)

SAFETY_PROHIBITIONS = (
    "no CAPTCHA solving",
    "no stealth/fingerprint evasion",
    "no proxy rotation",
    "no credential/cookie use",
    "no DRM/CDM/EME/HDCP/protected-buffer circumvention",
    "no broad folder scan",
    "no evidence file move",
    "no provider/network call without later approval",
)

DEFAULT_LIVE_SMOKE_SCOPES = (
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_LIVECHAT,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_RENDERED_CITATION,
    MANUAL_ACTION_SCOPE_ARCHIVE,
    MANUAL_ACTION_SCOPE_WARC_WACZ,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
)

MSN_MANUAL_SMOKE_SITE_LABEL = "MSN"
MSN_MANUAL_SMOKE_SOURCE_URL = "https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?"
MSN_MANUAL_SMOKE_ADAPTER_FAMILY = "msn"
MSN_MANUAL_SMOKE_APPROVED_SCOPES = (
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
)

MANUAL_OBSERVATION_STATUS_OBSERVED = "observed"
MANUAL_OBSERVATION_STATUS_NOT_OBSERVED = "not_observed"
MANUAL_OBSERVATION_STATUS_BLOCKED = "blocked"
MANUAL_OBSERVATION_STATUS_SKIPPED = "skipped"
MANUAL_OBSERVATION_STATUS_NEEDS_FOLLOWUP = "needs_followup"

MANUAL_OBSERVATION_RESULT_STATUSES = (
    MANUAL_OBSERVATION_STATUS_OBSERVED,
    MANUAL_OBSERVATION_STATUS_NOT_OBSERVED,
    MANUAL_OBSERVATION_STATUS_BLOCKED,
    MANUAL_OBSERVATION_STATUS_SKIPPED,
    MANUAL_OBSERVATION_STATUS_NEEDS_FOLLOWUP,
)


def _sorted_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value[key] for key in sorted(value)}


def _is_placeholder_value(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in _PLACEHOLDER_VALUES


def _approval_failure_reasons(
    *,
    approval: "LiveSmokeSiteApproval",
    site_label: str,
    source_url: str,
    intended_scopes: Sequence[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    approved_actions = tuple(action.strip() for action in approval.approved_actions if action.strip())
    intended_scope_set = set(intended_scopes)
    if _is_placeholder_value(site_label) or _is_placeholder_value(approval.site_label):
        reasons.append("explicit named site label is required")
    if _is_placeholder_value(source_url) or _is_placeholder_value(approval.source_url):
        reasons.append("explicit named source URL is required")
    if not approval.approved_by.strip():
        reasons.append("approved_by is required")
    if not approval.approved_at_utc.strip():
        reasons.append("approved_at_utc is required")
    if approval.site_label != site_label:
        reasons.append("approval site label does not match candidate site")
    if approval.source_url != source_url:
        reasons.append("approval source URL does not match candidate source URL")
    if not approved_actions:
        reasons.append("at least one named manual action/scope is required")
    unknown_actions = tuple(action for action in approved_actions if action not in intended_scope_set)
    if unknown_actions:
        reasons.append(
            "unknown approved manual action/scope: " + ", ".join(sorted(unknown_actions))
        )
    return tuple(reasons)


@dataclass(frozen=True)
class LiveSmokeTemplateValidation:
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "is_valid": self.is_valid,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ManualLiveSmokeObservation:
    observed_at_local_text: str
    operator_label: str
    site_label: str
    source_url: str
    action_scope_id: str
    result_status: str
    notes: str = ""
    artifact_expectation: str = "metadata_only_no_files"
    claims_automated_capture: bool = False
    claims_archive_submission: bool = False
    claims_downloaded_files: bool = False
    claims_credentials_cookies_accounts: bool = False
    claims_completed_live_verification: bool = False
    schema_version: str = LIVE_SMOKE_PLAN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_scope_id": self.action_scope_id,
            "artifact_expectation": self.artifact_expectation,
            "automation_performed": False,
            "claims_archive_submission": self.claims_archive_submission,
            "claims_automated_capture": self.claims_automated_capture,
            "claims_completed_live_verification": self.claims_completed_live_verification,
            "claims_credentials_cookies_accounts": self.claims_credentials_cookies_accounts,
            "claims_downloaded_files": self.claims_downloaded_files,
            "execution_commands": [],
            "manual_operator_only": True,
            "notes": self.notes,
            "observed_at_local_text": self.observed_at_local_text,
            "operator_label": self.operator_label,
            "provider_or_network_action": "none",
            "result_status": self.result_status,
            "schema_version": self.schema_version,
            "site_label": self.site_label,
            "source_url": self.source_url,
            "user_review_required": True,
        }


@dataclass(frozen=True)
class ManualLiveSmokeObservationImport:
    is_accepted: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    observation: ManualLiveSmokeObservation | None = None
    user_review_required: bool = True
    manual_operator_only: bool = True
    execution_commands: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "execution_commands": list(self.execution_commands),
            "is_accepted": self.is_accepted,
            "manual_operator_only": self.manual_operator_only,
            "observation": self.observation.to_dict() if self.observation is not None else None,
            "user_review_required": self.user_review_required,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class LiveSmokeSiteApproval:
    site_label: str
    source_url: str
    approved_by: str
    approved_at_utc: str
    approved_actions: tuple[str, ...] = ()
    approval_note: str = ""

    def validation_failures_for(
        self,
        *,
        site_label: str,
        source_url: str,
        intended_scopes: Sequence[str],
    ) -> tuple[str, ...]:
        return _approval_failure_reasons(
            approval=self,
            site_label=site_label,
            source_url=source_url,
            intended_scopes=intended_scopes,
        )

    def is_valid_for(
        self,
        *,
        site_label: str,
        source_url: str,
        intended_scopes: Sequence[str],
    ) -> bool:
        return not self.validation_failures_for(
            site_label=site_label,
            source_url=source_url,
            intended_scopes=intended_scopes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_note": self.approval_note,
            "approved_actions": list(self.approved_actions),
            "approved_at_utc": self.approved_at_utc,
            "approved_by": self.approved_by,
            "site_label": self.site_label,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class LiveSmokePlanTemplate:
    site_label: str = SITE_LABEL_APPROVAL_REQUIRED_PLACEHOLDER
    source_url: str = SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER
    source_adapter_family: str = "site_adapter"
    manual_action_scope_ids: tuple[str, ...] = DEFAULT_LIVE_SMOKE_SCOPES
    approver_metadata: str = APPROVER_METADATA_REQUIRED_PLACEHOLDER
    safety_boundary_acknowledged: bool = False
    approval_status: str = APPROVAL_STATUS_NOT_APPROVED
    workflow_status: str = LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    execution_mode: str = "manual_operator_only"
    execution_commands: tuple[str, ...] = ()
    live_network_actions_performed: str = "none"
    artifact_files_created: str = "none"
    safety_prohibitions: tuple[str, ...] = SAFETY_PROHIBITIONS
    schema_version: str = LIVE_SMOKE_PLAN_SCHEMA_VERSION

    @property
    def executable_by_application(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_status": self.approval_status,
            "approver_metadata": self.approver_metadata,
            "artifact_files_created": self.artifact_files_created,
            "executable_by_application": self.executable_by_application,
            "execution_commands": list(self.execution_commands),
            "execution_mode": self.execution_mode,
            "live_network_actions_performed": self.live_network_actions_performed,
            "manual_action_scope_ids": list(self.manual_action_scope_ids),
            "safety_boundary_acknowledged": self.safety_boundary_acknowledged,
            "safety_prohibitions": list(self.safety_prohibitions),
            "schema_version": self.schema_version,
            "site_label": self.site_label,
            "source_adapter_family": self.source_adapter_family,
            "source_url": self.source_url,
            "workflow_status": self.workflow_status,
        }


@dataclass(frozen=True)
class LiveSmokeChecklistItem:
    scope: str
    manual_instruction: str
    expected_artifact_declaration_type: str
    safety_boundary: str
    result_placeholder: str = "not_run"

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_artifact_declaration_type": self.expected_artifact_declaration_type,
            "manual_instruction": self.manual_instruction,
            "result_placeholder": self.result_placeholder,
            "safety_boundary": self.safety_boundary,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class LiveSmokePlan:
    plan_id: str
    candidate_site_label: str
    source_url_placeholder: str
    source_adapter_family: str
    intended_scopes: tuple[str, ...]
    checklist_items: tuple[LiveSmokeChecklistItem, ...]
    safety_notes: tuple[str, ...]
    safety_prohibitions: tuple[str, ...] = SAFETY_PROHIBITIONS
    approval_status: str = APPROVAL_STATUS_NOT_APPROVED
    workflow_status: str = LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    approval: LiveSmokeSiteApproval | None = None
    imported_manual_result: Mapping[str, Any] | None = None
    execution_commands: tuple[str, ...] = ()
    live_network_actions_performed: str = "none"
    artifact_files_created: str = "none"
    scope: str = LIVE_SMOKE_SCOPE
    schema_version: str = LIVE_SMOKE_PLAN_SCHEMA_VERSION

    @property
    def executable_by_application(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval": self.approval.to_dict() if self.approval is not None else None,
            "approval_status": self.approval_status,
            "artifact_files_created": self.artifact_files_created,
            "candidate_site_label": self.candidate_site_label,
            "checklist_items": [item.to_dict() for item in self.checklist_items],
            "executable_by_application": self.executable_by_application,
            "execution_commands": list(self.execution_commands),
            "imported_manual_result": _sorted_dict(dict(self.imported_manual_result or {}))
            if self.imported_manual_result is not None
            else None,
            "intended_scopes": list(self.intended_scopes),
            "live_network_actions_performed": self.live_network_actions_performed,
            "plan_id": self.plan_id,
            "safety_notes": list(self.safety_notes),
            "safety_prohibitions": list(self.safety_prohibitions),
            "schema_version": self.schema_version,
            "scope": self.scope,
            "source_adapter_family": self.source_adapter_family,
            "source_url_placeholder": self.source_url_placeholder,
            "workflow_status": self.workflow_status,
        }


def build_default_live_smoke_checklist() -> tuple[LiveSmokeChecklistItem, ...]:
    return (
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_WEBPAGE,
            manual_instruction=(
                "If separately approved, a human operator reviews webpage snapshot evidence "
                "and records whether planned page artifacts match visible content."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_RAW_HTML,
            safety_boundary="manual review only; no automatic browser, screenshot, OCR, or network action",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_COMMENTS,
            manual_instruction=(
                "If separately approved, a human operator notes whether comments appear available "
                "and whether fixture-backed artifact declarations remain appropriate."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_COMMENTS_JSONL,
            safety_boundary="manual review only; no comment scraping, API call, login, or bypass",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_LIVECHAT,
            manual_instruction=(
                "If separately approved, a human operator notes livechat availability and boundedness; "
                "one image must not be treated as complete livechat evidence."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_LIVECHAT_JSONL,
            safety_boundary="manual review only; no live chat capture, scraping, API call, or bypass",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_MEDIA,
            manual_instruction=(
                "If separately approved, a human operator records discovered media candidates without "
                "triggering automatic download or mux execution."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_MEDIA_INVENTORY,
            safety_boundary="manual review only; no external download, yt-dlp, FFmpeg, or media copying",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_RENDERED_CITATION,
            manual_instruction=(
                "If separately approved, a human operator records whether rendered citation capture "
                "would require consent-mediated display capture."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_RENDERED_RECORDING,
            safety_boundary=(
                "manual operator note only; no real screen recording or protected-output circumvention"
            ),
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_ARCHIVE,
            manual_instruction=(
                "If separately approved, a human operator records archive availability notes without "
                "submitting URLs or executing ArchiveBox."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_ARCHIVE_RESULT,
            safety_boundary="manual note only; no Wayback/archive.today/ArchiveBox calls or submissions",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_WARC_WACZ,
            manual_instruction=(
                "If separately approved, a human operator records whether future WARC/WACZ capture "
                "would be relevant; no capture or packaging is performed."
            ),
            expected_artifact_declaration_type=f"{ARTIFACT_TYPE_WARC}/{ARTIFACT_TYPE_WACZ}",
            safety_boundary="manual note only; no real WARC capture or WACZ packaging",
        ),
        LiveSmokeChecklistItem(
            scope=MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
            manual_instruction=(
                "If separately approved, a human operator manually reviews whether metadata-only "
                "queue/export records remain USER_REVIEW_REQUIRED."
            ),
            expected_artifact_declaration_type="EXPORT_METADATA_ONLY/QUEUE_METADATA_ONLY",
            safety_boundary="metadata review only; no package writes, queue persistence, file moves, or scans",
        ),
    )


def manual_action_scope_catalog() -> tuple[LiveSmokeChecklistItem, ...]:
    return build_default_live_smoke_checklist()


def build_named_site_live_smoke_plan_template(
    *,
    site_label: str = SITE_LABEL_APPROVAL_REQUIRED_PLACEHOLDER,
    source_url: str = SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
    source_adapter_family: str = "site_adapter",
    manual_action_scope_ids: Sequence[str] = DEFAULT_LIVE_SMOKE_SCOPES,
    approver_metadata: str = APPROVER_METADATA_REQUIRED_PLACEHOLDER,
    safety_boundary_acknowledged: bool = False,
) -> LiveSmokePlanTemplate:
    return LiveSmokePlanTemplate(
        site_label=site_label.strip(),
        source_url=source_url.strip(),
        source_adapter_family=source_adapter_family.strip(),
        manual_action_scope_ids=tuple(
            scope.strip() for scope in manual_action_scope_ids if scope.strip()
        ),
        approver_metadata=approver_metadata.strip(),
        safety_boundary_acknowledged=bool(safety_boundary_acknowledged),
    )


def validate_live_smoke_plan_template(
    template: LiveSmokePlanTemplate,
) -> LiveSmokeTemplateValidation:
    errors: list[str] = []
    warnings: list[str] = []
    if not template.site_label.strip():
        errors.append("missing site label")
    elif _is_placeholder_value(template.site_label):
        errors.append("placeholder site label")
    if not template.source_url.strip():
        errors.append("missing source URL")
    elif _is_placeholder_value(template.source_url):
        errors.append("placeholder source URL")
    if not template.source_adapter_family.strip():
        errors.append("missing adapter family")
    if not template.manual_action_scope_ids:
        errors.append("missing manual action/scope IDs")
    known_scopes = set(MANUAL_ACTION_SCOPE_IDS)
    unknown_scopes = tuple(
        scope for scope in template.manual_action_scope_ids if scope not in known_scopes
    )
    if unknown_scopes:
        errors.append("unknown manual action/scope IDs: " + ", ".join(sorted(unknown_scopes)))
    if not template.approver_metadata.strip() or _is_placeholder_value(
        template.approver_metadata
    ):
        errors.append("missing approver metadata")
    if not template.safety_boundary_acknowledged:
        errors.append("missing safety acknowledgement")
    if template.execution_commands:
        errors.append("execution commands are not allowed")
    if template.approval_status != APPROVAL_STATUS_NOT_APPROVED:
        warnings.append("template approval status is metadata only and should remain not_approved")
    return LiveSmokeTemplateValidation(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_msn_manual_live_smoke_plan_template(
    *,
    approver_metadata: str = APPROVER_METADATA_REQUIRED_PLACEHOLDER,
    safety_boundary_acknowledged: bool = False,
    manual_action_scope_ids: Sequence[str] = MSN_MANUAL_SMOKE_APPROVED_SCOPES,
) -> LiveSmokePlanTemplate:
    return build_named_site_live_smoke_plan_template(
        site_label=MSN_MANUAL_SMOKE_SITE_LABEL,
        source_url=MSN_MANUAL_SMOKE_SOURCE_URL,
        source_adapter_family=MSN_MANUAL_SMOKE_ADAPTER_FAMILY,
        manual_action_scope_ids=manual_action_scope_ids,
        approver_metadata=approver_metadata,
        safety_boundary_acknowledged=safety_boundary_acknowledged,
    )


def validate_msn_manual_live_smoke_template(
    template: LiveSmokePlanTemplate,
) -> LiveSmokeTemplateValidation:
    base = validate_live_smoke_plan_template(template)
    errors = list(base.errors)
    warnings = list(base.warnings)
    if template.site_label != MSN_MANUAL_SMOKE_SITE_LABEL:
        errors.append("MSN manual smoke site label must be exactly MSN")
    if template.source_url != MSN_MANUAL_SMOKE_SOURCE_URL:
        errors.append("MSN manual smoke source URL must be exactly https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?")
    if template.source_adapter_family != MSN_MANUAL_SMOKE_ADAPTER_FAMILY:
        errors.append("MSN manual smoke adapter family must be msn")
    if tuple(template.manual_action_scope_ids) != MSN_MANUAL_SMOKE_APPROVED_SCOPES:
        errors.append(
            "MSN manual smoke action/scope IDs must be exactly: "
            + ", ".join(MSN_MANUAL_SMOKE_APPROVED_SCOPES)
        )
    return LiveSmokeTemplateValidation(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_msn_manual_live_smoke_plan(
    *, approval: LiveSmokeSiteApproval | None = None
) -> LiveSmokePlan:
    return build_live_smoke_plan(
        candidate_site_label=MSN_MANUAL_SMOKE_SITE_LABEL,
        source_url_placeholder=MSN_MANUAL_SMOKE_SOURCE_URL,
        source_adapter_family=MSN_MANUAL_SMOKE_ADAPTER_FAMILY,
        intended_scopes=MSN_MANUAL_SMOKE_APPROVED_SCOPES,
        approval=approval,
    )


def validate_msn_manual_operator_observation(
    observation: ManualLiveSmokeObservation,
) -> LiveSmokeTemplateValidation:
    errors: list[str] = []
    warnings: list[str] = []
    if observation.site_label != MSN_MANUAL_SMOKE_SITE_LABEL:
        errors.append("manual observation site label must be MSN")
    if observation.source_url != MSN_MANUAL_SMOKE_SOURCE_URL:
        errors.append("manual observation source URL must be https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?")
    if observation.action_scope_id not in MSN_MANUAL_SMOKE_APPROVED_SCOPES:
        errors.append("manual observation action/scope is not approved for MSN")
    if observation.result_status not in MANUAL_OBSERVATION_RESULT_STATUSES:
        errors.append("manual observation result_status is unknown")
    if not observation.observed_at_local_text.strip():
        errors.append("manual observation observed_at_local_text is required")
    if not observation.operator_label.strip():
        errors.append("manual observation operator_label is required")
    if observation.claims_automated_capture:
        errors.append("manual observation must not claim automated capture")
    if observation.claims_archive_submission:
        errors.append("manual observation must not claim archive submission")
    if observation.claims_downloaded_files:
        errors.append("manual observation must not claim downloaded files")
    if observation.claims_credentials_cookies_accounts:
        errors.append("manual observation must not claim credentials/cookies/accounts")
    if observation.claims_completed_live_verification:
        errors.append("manual observation must not claim completed live verification")
    if observation.artifact_expectation and observation.artifact_expectation != "metadata_only_no_files":
        warnings.append("artifact expectation is metadata only; no file existence is claimed")
    return LiveSmokeTemplateValidation(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def import_msn_manual_operator_observation(
    observation: ManualLiveSmokeObservation,
) -> ManualLiveSmokeObservationImport:
    validation = validate_msn_manual_operator_observation(observation)
    return ManualLiveSmokeObservationImport(
        is_accepted=validation.is_valid,
        errors=validation.errors,
        warnings=validation.warnings,
        observation=observation if validation.is_valid else None,
    )


def build_live_smoke_plan_from_template(
    template: LiveSmokePlanTemplate,
) -> LiveSmokePlan:
    validation = validate_live_smoke_plan_template(template)
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))
    return build_live_smoke_plan(
        candidate_site_label=template.site_label,
        source_url_placeholder=template.source_url,
        source_adapter_family=template.source_adapter_family,
        intended_scopes=template.manual_action_scope_ids,
    )


def _default_safety_notes() -> tuple[str, ...]:
    return (
        "MANUAL_LIVE_SITE_SMOKE_PENDING",
        "APPROVAL_REQUIRED",
        "MANUAL_OPERATOR_ONLY",
        "MODEL_ONLY",
        "USER_REVIEW_REQUIRED",
        "No live execution is available from this scaffold.",
    )


def build_live_smoke_plan(
    *,
    candidate_site_label: str,
    source_url_placeholder: str = SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
    source_adapter_family: str = "site_adapter",
    intended_scopes: Sequence[str] = DEFAULT_LIVE_SMOKE_SCOPES,
    approval: LiveSmokeSiteApproval | None = None,
    blocked_reason: str = "",
) -> LiveSmokePlan:
    label = candidate_site_label.strip()
    url_placeholder = source_url_placeholder.strip()
    adapter_family = source_adapter_family.strip()
    if not label:
        raise ValueError("candidate_site_label is required")
    if not url_placeholder:
        raise ValueError("source_url_placeholder is required")
    if not adapter_family:
        raise ValueError("source_adapter_family is required")

    intended_scopes_tuple = tuple(scope.strip() for scope in intended_scopes if scope.strip())
    workflow_status = LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    approval_status = APPROVAL_STATUS_NOT_APPROVED
    safety_notes = list(_default_safety_notes())
    if blocked_reason:
        workflow_status = LIVE_SMOKE_STATUS_BLOCKED
        safety_notes.append(f"Blocked: {blocked_reason}")
    elif approval is not None:
        failures = approval.validation_failures_for(
            site_label=label,
            source_url=url_placeholder,
            intended_scopes=intended_scopes_tuple,
        )
        if failures:
            safety_notes.append("Approval metadata is incomplete or invalid: " + "; ".join(failures))
        else:
            workflow_status = LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
            approval_status = APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
            safety_notes.append("Approved for manual operator notes only; no application execution.")

    return LiveSmokePlan(
        plan_id=stable_capture_id("live_smoke_plan", label, url_placeholder, adapter_family),
        candidate_site_label=label,
        source_url_placeholder=url_placeholder,
        source_adapter_family=adapter_family,
        intended_scopes=intended_scopes_tuple,
        checklist_items=build_default_live_smoke_checklist(),
        safety_notes=tuple(safety_notes),
        approval_status=approval_status,
        workflow_status=workflow_status,
        approval=approval,
    )


def build_imported_manual_live_smoke_plan(
    *,
    candidate_site_label: str,
    source_url_placeholder: str,
    source_adapter_family: str,
    workflow_status: str,
    imported_manual_result: Mapping[str, Any],
    intended_scopes: Sequence[str] = DEFAULT_LIVE_SMOKE_SCOPES,
) -> LiveSmokePlan:
    if workflow_status not in LIVE_SMOKE_STATUSES:
        raise ValueError(f"Unknown live-smoke workflow status: {workflow_status}")
    plan = build_live_smoke_plan(
        candidate_site_label=candidate_site_label,
        source_url_placeholder=source_url_placeholder,
        source_adapter_family=source_adapter_family,
        intended_scopes=intended_scopes,
    )
    return LiveSmokePlan(
        **{
            **plan.__dict__,
            "workflow_status": workflow_status,
            "approval_status": APPROVAL_STATUS_NOT_APPROVED
            if workflow_status != LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
            else APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
            "imported_manual_result": dict(imported_manual_result),
        }
    )


def live_smoke_plan_to_json(plan: LiveSmokePlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True)
