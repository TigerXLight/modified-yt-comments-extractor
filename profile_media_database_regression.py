"""Full integration regression for Profile/Media Database mode.

V76B is the large readiness pack that proves the V75/V76 Database-mode backend
pieces work together before GUI wiring begins.  It composes the case batch,
index, search, Database mode view, session, dashboard, navigation, review
report, saved views, workbench, guarded export planning, safety invariants, and
implementation readiness report.

The regression consumes only explicit batch JSON paths supplied by the caller.
It does not discover files by walking a database folder.  The default path does
not create folders, move folders, rename folders, copy media, download media,
auto-classify, or infer sensitive identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_case_batch import (
    apply_case_batch_plan,
    build_case_batch_plan,
    load_case_batch_json,
    result_payload as case_batch_result_payload,
)
from profile_media_database import utc_now_iso
from profile_media_database_dashboard import dashboard_payload, build_dashboard_from_batch_json_files
from profile_media_database_implementation_readiness import (
    ProfileMediaImplementationReadinessReport,
    build_implementation_readiness_report,
    render_implementation_readiness_text,
)
from profile_media_database_index import build_database_index_from_batch_json_files
from profile_media_database_mode import build_database_mode_view_from_batch_json_files, database_mode_payload
from profile_media_database_navigation import build_navigation_index_from_batch_json_files, navigation_payload
from profile_media_database_review_report import build_review_report_from_session, render_review_report_text
from profile_media_database_safety_invariants import (
    ProfileMediaSafetyAudit,
    audit_payload_safety,
    combine_safety_audits,
    render_safety_audit_text,
)
from profile_media_database_search import result_payload as search_result_payload, search_database_batch_json_files
from profile_media_database_session import ProfileMediaDatabaseSessionConfig, build_database_session_snapshot
from profile_media_database_workbench import (
    apply_workbench_export_plan,
    build_workbench_export_plan,
    build_workbench_state,
    render_workbench_text,
    workbench_payload,
)

PROFILE_MEDIA_DATABASE_REGRESSION_SCHEMA_VERSION = "profile-media-database-full-regression-v76b"


@dataclass(frozen=True)
class ProfileMediaRegressionStep:
    """One check in the full Database-mode integration regression."""

    step_id: str
    status: str
    summary: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = dict(self.evidence)
        return data


@dataclass(frozen=True)
class ProfileMediaFullRegressionResult:
    """Full V76B regression output."""

    database_root: str
    batch_json_files: tuple[str, ...]
    steps: tuple[ProfileMediaRegressionStep, ...]
    safety_audit: ProfileMediaSafetyAudit
    readiness_report: ProfileMediaImplementationReadinessReport
    payloads: Mapping[str, Any]
    schema_version: str = PROFILE_MEDIA_DATABASE_REGRESSION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    status: str = "success"
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self, *, include_text: bool = False, include_payloads: bool = True) -> dict[str, Any]:
        failed_steps = [step for step in self.steps if step.status != "success"]
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "database_root": self.database_root,
            "batch_json_files": list(self.batch_json_files),
            "batch_json_file_count": len(self.batch_json_files),
            "step_count": len(self.steps),
            "failed_step_count": len(failed_steps),
            "steps": [step.to_dict() for step in self.steps],
            "safety_audit": self.safety_audit.to_dict(),
            "readiness_report": self.readiness_report.to_dict(),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
        }
        if include_payloads:
            data["payloads"] = dict(self.payloads)
        if include_text:
            data["regression_text"] = render_full_regression_text(self)
            data["safety_text"] = render_safety_audit_text(self.safety_audit)
            data["readiness_text"] = render_implementation_readiness_text(self.readiness_report)
        return data


def _profile_text(name: str, source_title: str, source_page: str, bucket: str, role: str, claim: str, status: str, date: str, index: int) -> str:
    return "\n".join(
        [
            f"Name: {name}",
            f"Date: {date}",
            f"Text: V76B integration fixture row {index} links {name} to {source_title} through explicitly supplied batch JSON only.",
            "Identifiers:",
            "- identifier_type: source_relation",
            f"  value: explicitly linked to fixture source {index}",
            "  source_evidenced: true",
            f"Address: Cases/V76B Integration Demo Case/Sources/{bucket}/{source_title}",
            f"Source: {source_page}",
        ]
    )


def build_integration_batch_payload(*, database_root: str = "Demo Database", case_title: str = "V76B Integration Demo Case") -> dict[str, Any]:
    """Build a large deterministic explicit batch fixture for integration tests."""

    buckets = ("Articles", "Social Media/Online", "Social Media/Offline", "Internal Media")
    roles = ("PRIMARY_SELF_AUTHORED_SCOPE", "SECONDARY_WITNESS_SOURCE", "TERTIARY_PROPAGATED_SOURCE", "UNKNOWN_SOURCE_ROLE")
    claims = ("SELF_AUTHORED", "WITNESS_ACCOUNT", "AGENCY_OR_OUTSIDE_RETELLING", "UNKNOWN_CLAIM_BASIS")
    statuses = ("CURRENT", "HISTORICAL", "UNDATED", "UNKNOWN")
    sources: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    for i in range(1, 49):
        bucket = buckets[(i - 1) % len(buckets)]
        role = roles[(i - 1) % len(roles)]
        claim = claims[(i - 1) % len(claims)]
        status = statuses[(i - 1) % len(statuses)]
        source_title = f"V76B demo source record {i:02d}"
        source_page = f"V76B Source Page {i:02d}"
        source_chain_gap = i % 5 == 0 or role == "UNKNOWN_SOURCE_ROLE"
        disputed_framing = i % 7 == 0
        sources.append(
            {
                "source_page": source_page,
                "source_title": source_title,
                "source_bucket": bucket,
                "source_role": role,
                "claim_basis": claim,
                "currentness_status": status,
                "source_chain_gap": source_chain_gap,
                "disputed_framing": disputed_framing,
                "notes_on_context_dispute": f"Fixture dispute note for source {i}." if disputed_framing else "",
                "confidence_or_verification_notes": f"Fixture source-chain gap retained for manual review on source {i}." if source_chain_gap else "Explicit fixture source row; no automatic source discovery performed.",
                "family_or_authority_claim_basis": "fixture authority retelling field" if claim == "AGENCY_OR_OUTSIDE_RETELLING" else "",
                "identity_claim_basis": "fixture identity basis is batch-provided text only",
                "appearance_claim_basis": "",
                "collaboration_or_corroboration_notes": f"Fixture corroboration bucket {i % 6}; repeated claims are not automatically promoted.",
            }
        )
        # Create a predictable mix of unique and repeated names to exercise global indexing.
        person_name = f"V76B Person {(i % 18) + 1:02d}"
        profiles.append(
            {
                "profile_text": _profile_text(
                    person_name,
                    source_title,
                    source_page,
                    bucket,
                    role,
                    claim,
                    status,
                    f"2026-07-{(i % 28) + 1:02d}",
                    i,
                ),
                "source_bucket": bucket,
                "source_role": role,
                "claim_basis": claim,
                "currentness_status": status,
            }
        )
    # One intentionally incomplete profile row so parser-warning lanes are covered.
    profiles.append(
        {
            "profile_text": "Name: V76B Parser Warning Example\nText: This row intentionally omits Source and Address for regression coverage.",
            "source_bucket": "Articles",
            "source_role": "UNKNOWN_SOURCE_ROLE",
            "claim_basis": "UNKNOWN_CLAIM_BASIS",
            "currentness_status": "UNKNOWN",
        }
    )
    return {
        "schema_version": "profile-media-case-batch-v75v",
        "database_root": database_root,
        "case_title": case_title,
        "sources": sources,
        "profiles": profiles,
    }


def write_integration_batch_json(path: str | Path, *, database_root: str = "Demo Database", case_title: str = "V76B Integration Demo Case") -> str:
    """Write the large V76B explicit batch fixture."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_integration_batch_payload(database_root=database_root, case_title=case_title)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)


def _load_batch_payloads(paths: Iterable[str | Path]) -> tuple[dict[str, Any], ...]:
    return tuple(load_case_batch_json(path) for path in paths)


def _step(step_id: str, status: str, summary: str, **evidence: Any) -> ProfileMediaRegressionStep:
    return ProfileMediaRegressionStep(step_id=step_id, status=status, summary=summary, evidence=evidence)


def run_full_profile_media_regression(
    batch_json_files: Iterable[str | Path],
    *,
    database_root: str = "Demo Database",
    include_text: bool = False,
) -> ProfileMediaFullRegressionResult:
    """Run the large V76B integration/readiness regression from explicit batch JSON."""

    batch_paths = tuple(str(Path(path)) for path in batch_json_files if str(path).strip())
    if not batch_paths:
        raise ValueError("at least one explicit --batch-json path is required")
    payloads = _load_batch_payloads(batch_paths)
    steps: list[ProfileMediaRegressionStep] = []
    output_payloads: dict[str, Any] = {}

    batch_results: list[dict[str, Any]] = []
    for payload in payloads:
        plan = build_case_batch_plan(payload=payload, database_root=database_root or str(payload.get("database_root", "")))
        result = apply_case_batch_plan(plan)
        batch_results.append(case_batch_result_payload(result, plan=plan))
    output_payloads["case_batch_dry_runs"] = batch_results
    steps.append(_step("case_batch_dry_run", "success" if all(item.get("status") == "planned_dry_run" for item in batch_results) else "failed", "Case batch materialization stayed dry-run only.", batch_count=len(batch_results)))

    index = build_database_index_from_batch_json_files(batch_paths)
    index_payload = index.to_dict()
    output_payloads["index"] = index_payload
    steps.append(_step("database_index", "success", "Database index built from explicit batch JSON files.", case_count=len(index.cases), source_count=len(index.sources), profile_row_count=len(index.profiles)))

    search_gap = search_database_batch_json_files(batch_paths, source_chain_gap=True)
    search_disputed = search_database_batch_json_files(batch_paths, disputed_framing=True)
    search_unknown = search_database_batch_json_files(batch_paths, source_role="UNKNOWN")
    search_parser = search_database_batch_json_files(batch_paths, has_parser_warnings=True)
    output_payloads["search_source_chain_gap"] = search_result_payload(search_gap, include_text=include_text)
    output_payloads["search_disputed_framing"] = search_result_payload(search_disputed, include_text=include_text)
    output_payloads["search_unknown_source_role"] = search_result_payload(search_unknown, include_text=include_text)
    output_payloads["search_parser_warnings"] = search_result_payload(search_parser, include_text=include_text)
    steps.append(_step("database_search", "success", "Search covered source-chain gaps, disputed framing, unknown roles, and parser warnings.", source_chain_gap_matches=len(search_gap.matched_sources), disputed_matches=len(search_disputed.matched_sources), unknown_role_matches=len(search_unknown.matched_sources), parser_warning_matches=len(search_parser.matched_profiles)))

    mode_view = build_database_mode_view_from_batch_json_files(batch_paths, source_chain_gap=True)
    output_payloads["mode_view"] = database_mode_payload(mode_view, include_text=include_text)
    steps.append(_step("database_mode_view", "success" if mode_view.status == "success" else "failed", "Database mode view produced main-panel sections.", section_count=len(mode_view.sections), row_count=sum(len(section.rows) for section in mode_view.sections)))

    config = ProfileMediaDatabaseSessionConfig(
        database_root=database_root,
        batch_json_files=batch_paths,
        mode="DATABASE",
        source_chain_gap=True,
    )
    session = build_database_session_snapshot(config)
    output_payloads["session"] = session.to_dict(include_view_text=include_text)
    steps.append(_step("database_session", "success" if session.status == "success" else "failed", "Database session snapshot created with persistent DATABASE runtime state.", matched_sources=session.to_dict().get("matched_source_count", 0)))

    dashboard = build_dashboard_from_batch_json_files(batch_paths)
    output_payloads["dashboard"] = dashboard_payload(dashboard, include_text=include_text)
    steps.append(_step("dashboard", "success" if dashboard.status == "success" else "failed", "Dashboard metrics and review lanes built.", metric_count=len(dashboard.metrics), review_lane_count=len(dashboard.review_lanes)))

    navigation = build_navigation_index_from_batch_json_files(batch_paths)
    output_payloads["navigation"] = navigation_payload(navigation, include_text=include_text)
    steps.append(_step("navigation", "success" if navigation.status == "success" else "failed", "Navigation targets built for cases, sources, and profiles.", target_count=len(navigation.targets)))

    review_report = build_review_report_from_session(session)
    output_payloads["review_report"] = review_report.to_dict()
    output_payloads["review_report_text"] = render_review_report_text(review_report) if include_text else ""
    steps.append(_step("review_report", "success" if review_report.status == "success" else "failed", "Review report gathered source-chain gaps, disputed framing, unknown roles, and parser warnings.", review_item_count=len(review_report.items)))

    workbench = build_workbench_state(config)
    workbench_export_plan = build_workbench_export_plan("v76b_dry_run_exports", execute=False)
    workbench_export_result = apply_workbench_export_plan(workbench_export_plan, workbench)
    blocked_export_result = apply_workbench_export_plan(build_workbench_export_plan("v76b_blocked_exports", execute=True, confirmation_phrase="WRONG_CONFIRMATION"), workbench)
    output_payloads["workbench"] = workbench_payload(workbench, include_text=include_text, export_plan=workbench_export_plan, export_result=workbench_export_result)
    output_payloads["workbench_blocked_export_result"] = blocked_export_result.to_dict()
    if include_text:
        output_payloads["workbench_text"] = render_workbench_text(workbench)
    steps.append(_step("workbench", "success" if workbench.status == "success" else "failed", "Full workbench state combined session, dashboard, navigation, review report, and saved views.", saved_view_count=len(workbench.saved_views.views), navigation_target_count=len(workbench.navigation.targets)))
    steps.append(_step("guarded_export_planning", "success" if workbench_export_result.status == "planned_dry_run" and blocked_export_result.status == "blocked_confirmation_required" else "failed", "Workbench export stayed dry-run by default and blocked a wrong confirmation phrase.", dry_run_status=workbench_export_result.status, blocked_status=blocked_export_result.status))

    audits = [audit_payload_safety("case_batch_dry_runs", batch_results)]
    audits.extend(audit_payload_safety(name, payload) for name, payload in output_payloads.items() if name not in {"review_report_text", "workbench_text"})
    safety = combine_safety_audits(audits)
    output_payloads["safety_audit"] = safety.to_dict()
    steps.append(_step("safety_invariants", "success" if safety.status == "passed" else "failed", "All read-only/default safety flags remained false.", failed_observations=len(safety.failed_observations)))

    provisional = {
        "status": "success" if all(step.status == "success" for step in steps) and safety.status == "passed" else "failed",
        "workbench": output_payloads.get("workbench", {}),
        "safety_audit": safety.to_dict(),
    }
    readiness = build_implementation_readiness_report(provisional)
    output_payloads["readiness_report"] = readiness.to_dict()
    steps.append(_step("implementation_readiness", "success" if readiness.status == "ready_for_gui_panel_integration" else "failed", "Readiness report generated for the next GUI integration phase.", readiness_status=readiness.status))

    warnings: list[str] = []
    if safety.status != "passed":
        warnings.append("safety_invariants_failed")
    if readiness.warnings:
        warnings.extend(readiness.warnings)
    final_status = "success" if all(step.status == "success" for step in steps) and not warnings else "failed"
    return ProfileMediaFullRegressionResult(
        database_root=database_root,
        batch_json_files=batch_paths,
        steps=tuple(steps),
        safety_audit=safety,
        readiness_report=readiness,
        payloads=output_payloads,
        status=final_status,
        warnings=tuple(sorted(set(warnings))),
    )


def render_full_regression_text(result: ProfileMediaFullRegressionResult) -> str:
    """Render the integration regression for terminal proof."""

    data = result.to_dict(include_text=False, include_payloads=False)
    lines = [
        "Profile/Media Database Full Regression",
        f"Status: {result.status}",
        f"Database root: {result.database_root}",
        f"Batch JSON files: {len(result.batch_json_files)}",
        f"Steps: {data['step_count']}",
        f"Failed steps: {data['failed_step_count']}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        "Steps:",
    ]
    for step in result.steps:
        lines.append(f"- {step.step_id}: {step.status} — {step.summary}")
    lines.extend(["", render_safety_audit_text(result.safety_audit), "", render_implementation_readiness_text(result.readiness_report)])
    return "\n".join(lines)
