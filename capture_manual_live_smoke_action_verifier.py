from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


MANUAL_LIVE_SMOKE_ACTION_VERIFIER_SCHEMA_VERSION = "manual_live_smoke_action_verifier_v1"
MANUAL_LIVE_SMOKE_ACTION_VERIFIER_READY = "MANUAL_LIVE_SMOKE_ACTION_CHAIN_READY"
MANUAL_LIVE_SMOKE_ACTION_VERIFIER_NEEDS_REVIEW = "MANUAL_LIVE_SMOKE_ACTION_CHAIN_NEEDS_REVIEW"


@dataclass(frozen=True)
class ManualLiveSmokeActionVerifierIssue:
    code: str
    detail: str


@dataclass(frozen=True)
class ManualLiveSmokeActionVerifierReport:
    schema_version: str
    verdict: str
    issue_count: int
    issues: tuple[ManualLiveSmokeActionVerifierIssue, ...]
    safety_flags: tuple[str, ...]


def verify_manual_live_smoke_action_payload(payload: Mapping[str, Any]) -> ManualLiveSmokeActionVerifierReport:
    issues: list[ManualLiveSmokeActionVerifierIssue] = []
    plan = payload.get("plan")
    run = payload.get("run")
    if not isinstance(plan, Mapping):
        issues.append(ManualLiveSmokeActionVerifierIssue("missing_plan", "Payload must include a plan object."))
        plan = {}
    if not isinstance(run, Mapping):
        issues.append(ManualLiveSmokeActionVerifierIssue("missing_run", "Payload must include a run object."))
        run = {}

    for key in ("site_id", "action_id", "source_url", "steps", "artifact_contracts", "safety_flags"):
        if key not in plan:
            issues.append(ManualLiveSmokeActionVerifierIssue("missing_plan_field", f"Plan is missing {key}."))
    for key in ("site_id", "action_id", "step_results", "safety_flags"):
        if key not in run:
            issues.append(ManualLiveSmokeActionVerifierIssue("missing_run_field", f"Run is missing {key}."))

    required_flags = {
        "requires_named_site",
        "requires_named_action",
        "requires_explicit_operator_approval_before_launch",
        "no_automated_live_http_in_tests",
        "no_automatic_archive_submission",
        "no_automatic_media_download",
        "no_credential_reads",
        "metadata_only_reports",
        "no_completed_capture_claim",
    }
    plan_flags = set(plan.get("safety_flags", []) if isinstance(plan, Mapping) else [])
    missing_flags = sorted(required_flags - plan_flags)
    if missing_flags:
        issues.append(ManualLiveSmokeActionVerifierIssue("missing_safety_flags", ", ".join(missing_flags)))

    if run.get("execution_allowed") and run.get("dry_run"):
        issues.append(ManualLiveSmokeActionVerifierIssue("inconsistent_execution_state", "Dry-run payload cannot also be execution_allowed."))
    payload_text = str(payload).lower()
    forbidden_claims = (
        "verified capture",
        "capture completed",
        "completed capture",
        "status': 'completed",
        "status\": \"completed",
    )
    if any(claim in payload_text for claim in forbidden_claims):
        issues.append(ManualLiveSmokeActionVerifierIssue("forbidden_completion_claim", "Action payload must not claim completed or verified capture."))

    verdict = MANUAL_LIVE_SMOKE_ACTION_VERIFIER_READY if not issues else MANUAL_LIVE_SMOKE_ACTION_VERIFIER_NEEDS_REVIEW
    return ManualLiveSmokeActionVerifierReport(
        schema_version=MANUAL_LIVE_SMOKE_ACTION_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issue_count=len(issues),
        issues=tuple(issues),
        safety_flags=tuple(sorted(required_flags)),
    )


def manual_live_smoke_action_verifier_report_to_dict(report: ManualLiveSmokeActionVerifierReport) -> dict[str, Any]:
    return asdict(report)
