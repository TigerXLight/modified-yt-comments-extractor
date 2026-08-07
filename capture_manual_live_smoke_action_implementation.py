from __future__ import annotations

import hashlib
import json
import re
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


MANUAL_LIVE_SMOKE_ACTION_IMPLEMENTATION_SCHEMA_VERSION = "manual_live_smoke_action_implementation_v1"
MANUAL_LIVE_SMOKE_ACTION_PLAN_SCHEMA_VERSION = "manual_live_smoke_action_plan_v1"
MANUAL_LIVE_SMOKE_ACTION_RUN_SCHEMA_VERSION = "manual_live_smoke_action_run_v1"
MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN = "APPROVE_MANUAL_LIVE_SMOKE_ACTIONS"
MANUAL_LIVE_SMOKE_ACTION_VERDICT_READY = "MANUAL_LIVE_SMOKE_ACTION_READY_FOR_OPERATOR"
MANUAL_LIVE_SMOKE_ACTION_VERDICT_BLOCKED = "MANUAL_LIVE_SMOKE_ACTION_BLOCKED_PENDING_APPROVAL"
MANUAL_LIVE_SMOKE_ACTION_VERDICT_DRY_RUN = "MANUAL_LIVE_SMOKE_ACTION_DRY_RUN_ONLY"

_SECRET_KEY_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\\s\'\"])(?:[A-Za-z]:[\\\\/]|\\\\\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_ALLOWED_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
_SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,180}$")


@dataclass(frozen=True)
class ManualLiveSmokeArtifactContract:
    role: str
    required: bool
    allowed_extensions: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class ManualLiveSmokeActionStep:
    step_id: str
    title: str
    kind: str
    instruction: str
    external_effect: str
    requires_explicit_approval: bool = False
    expected_artifact_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManualLiveSmokeActionDefinition:
    site_id: str
    site_label: str
    action_id: str
    action_label: str
    target_url_required: bool
    summary: str
    steps: tuple[ManualLiveSmokeActionStep, ...]
    artifact_contracts: tuple[ManualLiveSmokeArtifactContract, ...]
    safety_flags: tuple[str, ...]


@dataclass(frozen=True)
class ManualLiveSmokeActionPlan:
    schema_version: str
    site_id: str
    site_label: str
    action_id: str
    action_label: str
    source_url: str
    operator_intent: str
    verdict: str
    approval_required: bool
    execution_allowed: bool
    dry_run: bool
    steps: tuple[ManualLiveSmokeActionStep, ...]
    artifact_contracts: tuple[ManualLiveSmokeArtifactContract, ...]
    safety_flags: tuple[str, ...]
    metadata_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManualLiveSmokeActionStepResult:
    step_id: str
    title: str
    status: str
    external_effect: str
    detail: str


@dataclass(frozen=True)
class ManualLiveSmokeActionRun:
    schema_version: str
    plan_sha256: str
    site_id: str
    action_id: str
    source_url_host_hint: str
    dry_run: bool
    execution_allowed: bool
    verdict: str
    step_results: tuple[ManualLiveSmokeActionStepResult, ...]
    safety_flags: tuple[str, ...]
    metadata_warnings: tuple[str, ...] = ()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _safe_text(value: Any, *, field_name: str = "value") -> str:
    text = str(value or "").strip()
    if _SECRET_KEY_RE.search(field_name):
        raise ValueError(f"secret-like field is not allowed: {field_name}")
    if _SECRET_KEY_RE.search(text):
        raise ValueError(f"secret-like value is not allowed for {field_name}")
    if _FULL_PATH_RE.search(text):
        raise ValueError(f"full local path is not allowed for {field_name}")
    return text


def _safe_id(value: str, *, field_name: str) -> str:
    text = _safe_text(value, field_name=field_name)
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"unsafe identifier for {field_name}: {value!r}")
    return text


def _safe_url(value: str) -> str:
    text = _safe_text(value, field_name="source_url")
    if not _ALLOWED_URL_RE.match(text):
        raise ValueError("source_url must be an http(s) URL")
    if _SECRET_KEY_RE.search(text):
        raise ValueError("source_url must not contain secret-like text")
    return text


def _host_hint(url: str) -> str:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/", 1)[0].lower()
    if not host:
        return "unknown-host"
    return host[:80]


def _artifact(role: str, required: bool, allowed: Sequence[str], description: str) -> ManualLiveSmokeArtifactContract:
    return ManualLiveSmokeArtifactContract(
        role=_safe_id(role, field_name="artifact_role"),
        required=bool(required),
        allowed_extensions=tuple(str(ext).lower().lstrip(".") for ext in allowed),
        description=_safe_text(description, field_name="artifact_description"),
    )


def _step(
    step_id: str,
    title: str,
    kind: str,
    instruction: str,
    external_effect: str,
    *,
    approval: bool = False,
    roles: Sequence[str] = (),
) -> ManualLiveSmokeActionStep:
    return ManualLiveSmokeActionStep(
        step_id=_safe_id(step_id, field_name="step_id"),
        title=_safe_text(title, field_name="step_title"),
        kind=_safe_id(kind, field_name="step_kind"),
        instruction=_safe_text(instruction, field_name="step_instruction"),
        external_effect=_safe_text(external_effect, field_name="external_effect"),
        requires_explicit_approval=bool(approval),
        expected_artifact_roles=tuple(_safe_id(role, field_name="expected_artifact_role") for role in roles),
    )


def _definition(
    site_id: str,
    site_label: str,
    action_id: str,
    action_label: str,
    summary: str,
    steps: Sequence[ManualLiveSmokeActionStep],
    artifacts: Sequence[ManualLiveSmokeArtifactContract],
) -> ManualLiveSmokeActionDefinition:
    return ManualLiveSmokeActionDefinition(
        site_id=_safe_id(site_id, field_name="site_id"),
        site_label=_safe_text(site_label, field_name="site_label"),
        action_id=_safe_id(action_id, field_name="action_id"),
        action_label=_safe_text(action_label, field_name="action_label"),
        target_url_required=True,
        summary=_safe_text(summary, field_name="action_summary"),
        steps=tuple(steps),
        artifact_contracts=tuple(artifacts),
        safety_flags=(
            "requires_named_site",
            "requires_named_action",
            "requires_explicit_operator_approval_before_launch",
            "no_automated_live_http_in_tests",
            "no_automatic_archive_submission",
            "no_automatic_media_download",
            "no_credential_reads",
            "metadata_only_reports",
            "no_completed_capture_claim",
        ),
    )


def build_manual_live_smoke_action_registry() -> dict[str, ManualLiveSmokeActionDefinition]:
    """Return concrete manual smoke actions that can be planned and run under approval."""

    article_artifacts = (
        _artifact("article_text", True, ("txt", "md", "json"), "Operator-supplied extracted article text or structured text."),
        _artifact("article_html_snapshot", False, ("html", "htm", "mhtml"), "Operator-supplied saved page or snapshot, if available."),
        _artifact("article_screenshot", False, ("png", "jpg", "jpeg", "webp"), "Operator-supplied screenshot file metadata, not raw image bytes."),
    )
    comments_artifacts = article_artifacts + (
        _artifact("comments_text", True, ("txt", "md", "json"), "Operator-supplied comments transcript or extracted comments text."),
        _artifact("comments_shadow_root_notes", False, ("txt", "md", "json"), "Notes about the selected frame, shadow-root host, scroll strategy, and limits."),
    )
    archive_artifacts = (
        _artifact("archive_result_metadata", True, ("json", "txt", "md"), "Operator-supplied archive URL/result metadata from archive.ph, Wayback, Ghostarchive, or perms.cc."),
        _artifact("source_url_notes", False, ("txt", "md", "json"), "Notes about failures, redirects, paywalls, or dynamic loading."),
    )

    definitions = [
        _definition(
            "msn",
            "MSN article/comments",
            "msn_article_capture",
            "MSN article manual capture",
            "Open a named MSN URL and collect article text/snapshot artifacts for later review.",
            (
                _step("confirm_target", "Confirm named site/action", "manual_confirm", "Confirm the URL is the named MSN target requested by the user.", "none"),
                _step("open_browser", "Open target URL", "browser_open", "Open the source URL in the operator browser.", "browser_launch", approval=True),
                _step("capture_article", "Capture article evidence", "manual_capture", "Save article text and optional HTML/screenshot artifacts using the operator-approved method.", "operator_manual_capture", roles=("article_text", "article_html_snapshot", "article_screenshot")),
                _step("prepare_observation", "Prepare observation intake", "manual_prepare", "Submit only safe artifact names, SHA-256 hashes, byte counts, and summary into the observation intake boundary.", "metadata_only", roles=("article_text",)),
            ),
            article_artifacts,
        ),
        _definition(
            "msn",
            "MSN article/comments",
            "msn_comments_shadow_root_capture",
            "MSN comments shadow-root manual capture",
            "Open a named MSN URL and collect comments from the comments web-component frame/shadow-root workflow.",
            (
                _step("confirm_target", "Confirm named site/action", "manual_confirm", "Confirm the URL is the named MSN target requested by the user and the requested action is comments capture.", "none"),
                _step("open_browser", "Open target URL", "browser_open", "Open the source URL in Firefox or the approved operator browser.", "browser_launch", approval=True),
                _step("select_comments_frame", "Select comments frame", "manual_browser", "In DevTools, select the MSN comments frame/web component and inspect the shadow-root host such as social-comment-wc.", "operator_manual_browser"),
                _step("expand_scroll_container", "Expand scroll container", "manual_browser", "Apply the approved manual CSS/scroll method to the comments overlay/container and capture only operator-visible content.", "operator_manual_browser"),
                _step("capture_comments", "Capture comments evidence", "manual_capture", "Save comments transcript/JSON and optional notes about frame, scroll limits, and any unavailable content.", "operator_manual_capture", roles=("comments_text", "comments_shadow_root_notes", "article_screenshot")),
                _step("prepare_observation", "Prepare observation intake", "manual_prepare", "Submit only safe artifact names, SHA-256 hashes, byte counts, and summary into the observation intake boundary.", "metadata_only", roles=("comments_text", "comments_shadow_root_notes")),
            ),
            comments_artifacts,
        ),
        _definition(
            "generic_web",
            "Generic web source",
            "archive_submission_prepare",
            "Archive submission preparation",
            "Prepare a named URL for operator-run archive submission while keeping automation disabled.",
            (
                _step("confirm_target", "Confirm named source URL", "manual_confirm", "Confirm the exact source URL and archive service requested by the user.", "none"),
                _step("open_source", "Open source URL", "browser_open", "Open the source URL in the operator browser for inspection before archiving.", "browser_launch", approval=True),
                _step("operator_archive", "Run archive manually", "manual_archive", "Use the user-approved archive service manually; do not submit from automated tests or unattended code.", "operator_manual_archive"),
                _step("record_archive", "Record archive result", "manual_prepare", "Record archive URL/result metadata as safe text, not sign-in or browser-session data.", "metadata_only", roles=("archive_result_metadata", "source_url_notes")),
            ),
            archive_artifacts,
        ),
    ]
    return {f"{definition.site_id}:{definition.action_id}": definition for definition in definitions}


def get_manual_live_smoke_action_definition(site_id: str, action_id: str) -> ManualLiveSmokeActionDefinition:
    key = f"{_safe_id(site_id, field_name='site_id')}:{_safe_id(action_id, field_name='action_id')}"
    registry = build_manual_live_smoke_action_registry()
    if key not in registry:
        raise ValueError(f"unknown manual live smoke action: {key}")
    return registry[key]


def list_manual_live_smoke_actions() -> list[dict[str, Any]]:
    actions = []
    for key, definition in sorted(build_manual_live_smoke_action_registry().items()):
        actions.append(
            {
                "key": key,
                "site_id": definition.site_id,
                "site_label": definition.site_label,
                "action_id": definition.action_id,
                "action_label": definition.action_label,
                "summary": definition.summary,
                "required_artifact_roles": [artifact.role for artifact in definition.artifact_contracts if artifact.required],
            }
        )
    return actions


def build_manual_live_smoke_action_plan(
    *,
    site_id: str,
    action_id: str,
    source_url: str,
    operator_intent: str,
    approval_token: str | None = None,
    dry_run: bool = True,
) -> ManualLiveSmokeActionPlan:
    definition = get_manual_live_smoke_action_definition(site_id, action_id)
    url = _safe_url(source_url)
    intent = _safe_text(operator_intent, field_name="operator_intent")
    has_launch_step = any(step.requires_explicit_approval for step in definition.steps)
    approved = bool(approval_token == MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN)
    execution_allowed = bool(approved and not dry_run)
    if dry_run:
        verdict = MANUAL_LIVE_SMOKE_ACTION_VERDICT_DRY_RUN
    elif has_launch_step and not approved:
        verdict = MANUAL_LIVE_SMOKE_ACTION_VERDICT_BLOCKED
    else:
        verdict = MANUAL_LIVE_SMOKE_ACTION_VERDICT_READY
    warnings: list[str] = []
    if dry_run:
        warnings.append("dry_run_selected_no_external_action")
    if has_launch_step and not approved:
        warnings.append("explicit_approval_token_required_for_browser_launch")
    return ManualLiveSmokeActionPlan(
        schema_version=MANUAL_LIVE_SMOKE_ACTION_PLAN_SCHEMA_VERSION,
        site_id=definition.site_id,
        site_label=definition.site_label,
        action_id=definition.action_id,
        action_label=definition.action_label,
        source_url=url,
        operator_intent=intent,
        verdict=verdict,
        approval_required=has_launch_step,
        execution_allowed=execution_allowed,
        dry_run=bool(dry_run),
        steps=definition.steps,
        artifact_contracts=definition.artifact_contracts,
        safety_flags=definition.safety_flags,
        metadata_warnings=tuple(warnings),
    )


def manual_live_smoke_action_plan_to_dict(plan: ManualLiveSmokeActionPlan) -> dict[str, Any]:
    return asdict(plan)


def manual_live_smoke_action_plan_to_json(plan: ManualLiveSmokeActionPlan) -> str:
    return _json_bytes(manual_live_smoke_action_plan_to_dict(plan)).decode("utf-8")


class ManualLiveSmokeActionAdapter:
    """Adapter boundary for actual side effects. Tests use fake/dry-run adapters."""

    def open_browser(self, url: str) -> str:
        opened = webbrowser.open(url)
        return "browser_open_requested" if opened else "browser_open_returned_false"


def execute_manual_live_smoke_action_plan(
    plan: ManualLiveSmokeActionPlan,
    *,
    adapter: ManualLiveSmokeActionAdapter | None = None,
) -> ManualLiveSmokeActionRun:
    plan_dict = manual_live_smoke_action_plan_to_dict(plan)
    plan_hash = _sha256_json(plan_dict)
    adapter = adapter or ManualLiveSmokeActionAdapter()
    results: list[ManualLiveSmokeActionStepResult] = []

    for step in plan.steps:
        if step.kind == "browser_open":
            if plan.dry_run:
                results.append(ManualLiveSmokeActionStepResult(step.step_id, step.title, "DRY_RUN_SKIPPED", step.external_effect, "Browser launch skipped by dry-run."))
            elif not plan.execution_allowed:
                results.append(ManualLiveSmokeActionStepResult(step.step_id, step.title, "BLOCKED_PENDING_APPROVAL", step.external_effect, "Browser launch requires explicit approval token and non-dry-run mode."))
            else:
                detail = _safe_text(adapter.open_browser(plan.source_url), field_name="adapter_result")
                results.append(ManualLiveSmokeActionStepResult(step.step_id, step.title, "EXECUTED_OPERATOR_BROWSER_OPEN", step.external_effect, detail))
        elif step.kind.startswith("manual"):
            results.append(ManualLiveSmokeActionStepResult(step.step_id, step.title, "OPERATOR_ACTION_REQUIRED", step.external_effect, "Manual operator step; no automated side effect performed."))
        else:
            results.append(ManualLiveSmokeActionStepResult(step.step_id, step.title, "READY", step.external_effect, "Step ready for operator workflow."))

    run_verdict = plan.verdict
    if plan.execution_allowed and any(result.status == "EXECUTED_OPERATOR_BROWSER_OPEN" for result in results):
        run_verdict = MANUAL_LIVE_SMOKE_ACTION_VERDICT_READY

    return ManualLiveSmokeActionRun(
        schema_version=MANUAL_LIVE_SMOKE_ACTION_RUN_SCHEMA_VERSION,
        plan_sha256=plan_hash,
        site_id=plan.site_id,
        action_id=plan.action_id,
        source_url_host_hint=_host_hint(plan.source_url),
        dry_run=plan.dry_run,
        execution_allowed=plan.execution_allowed,
        verdict=run_verdict,
        step_results=tuple(results),
        safety_flags=plan.safety_flags,
        metadata_warnings=plan.metadata_warnings,
    )


def manual_live_smoke_action_run_to_dict(run: ManualLiveSmokeActionRun) -> dict[str, Any]:
    return asdict(run)


def manual_live_smoke_action_run_to_json(run: ManualLiveSmokeActionRun) -> str:
    return _json_bytes(manual_live_smoke_action_run_to_dict(run)).decode("utf-8")
