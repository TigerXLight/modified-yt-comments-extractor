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
    "webpage_snapshot_manual_review",
    "comments_presence_manual_review",
    "livechat_availability_manual_review",
    "media_discovery_manual_review",
    "rendered_citation_manual_operator_note",
    "archive_availability_manual_note",
    "warc_wacz_future_manual_note",
    "export_queue_metadata_review",
)


def _sorted_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value[key] for key in sorted(value)}


@dataclass(frozen=True)
class LiveSmokeSiteApproval:
    site_label: str
    source_url: str
    approved_by: str
    approved_at_utc: str
    approved_actions: tuple[str, ...] = ()
    approval_note: str = ""

    def is_valid_for(self, *, site_label: str, source_url: str) -> bool:
        return (
            bool(self.site_label.strip())
            and bool(self.source_url.strip())
            and bool(self.approved_by.strip())
            and bool(self.approved_at_utc.strip())
            and self.site_label == site_label
            and self.source_url == source_url
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
            scope="webpage_snapshot_manual_review",
            manual_instruction=(
                "If separately approved, a human operator reviews webpage snapshot evidence "
                "and records whether planned page artifacts match visible content."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_RAW_HTML,
            safety_boundary="manual review only; no automatic browser, screenshot, OCR, or network action",
        ),
        LiveSmokeChecklistItem(
            scope="comments_presence_manual_review",
            manual_instruction=(
                "If separately approved, a human operator notes whether comments appear available "
                "and whether fixture-backed artifact declarations remain appropriate."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_COMMENTS_JSONL,
            safety_boundary="manual review only; no comment scraping, API call, login, or bypass",
        ),
        LiveSmokeChecklistItem(
            scope="livechat_availability_manual_review",
            manual_instruction=(
                "If separately approved, a human operator notes livechat availability and boundedness; "
                "one image must not be treated as complete livechat evidence."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_LIVECHAT_JSONL,
            safety_boundary="manual review only; no live chat capture, scraping, API call, or bypass",
        ),
        LiveSmokeChecklistItem(
            scope="media_discovery_manual_review",
            manual_instruction=(
                "If separately approved, a human operator records discovered media candidates without "
                "triggering automatic download or mux execution."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_MEDIA_INVENTORY,
            safety_boundary="manual review only; no external download, yt-dlp, FFmpeg, or media copying",
        ),
        LiveSmokeChecklistItem(
            scope="rendered_citation_manual_operator_note",
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
            scope="archive_availability_manual_note",
            manual_instruction=(
                "If separately approved, a human operator records archive availability notes without "
                "submitting URLs or executing ArchiveBox."
            ),
            expected_artifact_declaration_type=ARTIFACT_TYPE_ARCHIVE_RESULT,
            safety_boundary="manual note only; no Wayback/archive.today/ArchiveBox calls or submissions",
        ),
        LiveSmokeChecklistItem(
            scope="warc_wacz_future_manual_note",
            manual_instruction=(
                "If separately approved, a human operator records whether future WARC/WACZ capture "
                "would be relevant; no capture or packaging is performed."
            ),
            expected_artifact_declaration_type=f"{ARTIFACT_TYPE_WARC}/{ARTIFACT_TYPE_WACZ}",
            safety_boundary="manual note only; no real WARC capture or WACZ packaging",
        ),
        LiveSmokeChecklistItem(
            scope="export_queue_metadata_review",
            manual_instruction=(
                "If separately approved, a human operator manually reviews whether metadata-only "
                "queue/export records remain USER_REVIEW_REQUIRED."
            ),
            expected_artifact_declaration_type="EXPORT_METADATA_ONLY/QUEUE_METADATA_ONLY",
            safety_boundary="metadata review only; no package writes, queue persistence, file moves, or scans",
        ),
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
    source_url_placeholder: str = "APPROVAL_REQUIRED_SOURCE_URL",
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

    workflow_status = LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    approval_status = APPROVAL_STATUS_NOT_APPROVED
    safety_notes = list(_default_safety_notes())
    if blocked_reason:
        workflow_status = LIVE_SMOKE_STATUS_BLOCKED
        safety_notes.append(f"Blocked: {blocked_reason}")
    elif approval is not None and approval.is_valid_for(
        site_label=label,
        source_url=url_placeholder,
    ):
        workflow_status = LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
        approval_status = APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
        safety_notes.append("Approved for manual operator notes only; no application execution.")
    elif approval is not None:
        safety_notes.append("Approval metadata did not match the candidate site/source URL.")

    return LiveSmokePlan(
        plan_id=stable_capture_id("live_smoke_plan", label, url_placeholder, adapter_family),
        candidate_site_label=label,
        source_url_placeholder=url_placeholder,
        source_adapter_family=adapter_family,
        intended_scopes=tuple(intended_scopes),
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
