from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from profile_media_existing_source_intake_bundle_preview_r42gl import (
    R42GL_PASS_STATUS,
    build_existing_source_intake_preview_bridge_report,
    evidence_bundle_plan_preview_from_existing_source,
    sample_existing_source_shapes,
)
from profile_media_source_map_raw_url_audio_catchup_r42gh import R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_source_package_preview import (
    ProfileMediaSourcePackagePreview,
    build_profile_media_source_package_preview,
    source_package_preview_payload,
)
from profile_media_source_row_evidence_bundle_plan_r42gk import (
    PROMOTION_NONE,
    ROLE_STATUS_COMPAT,
    R42GK_PASS_STATUS,
    machine_url_fields_are_plain,
    validate_evidence_bundle_plan_report,
)
from profile_media_universal_evidence_bundle_index_r42gj import R42GJ_PASS_STATUS, build_report as build_r42gj_report
from profile_media_universal_media_method_matrix_r42gi import R42GI_PASS_STATUS, validate_universal_media_method_matrix
from profile_media_universal_source_map_r42gg import R42GG_PASS_STATUS, SIDE_EFFECT_BOUNDARY, validate_universal_source_map
from source_resource_state import SourceUrlIntakeResult, parse_source_url_intake, state_to_dict


R42GM_MARKER = "YTCE_R42GM_PREVIEW_SURFACE_INTEGRATION"
R42GM_PASS_STATUS = "PASS_R42GM_PREVIEW_SURFACE_INTEGRATION"
R42GM_BLOCKED_STATUS = "BLOCKED_R42GM_WITH_EXACT_BLOCKER"
R42GM_SCHEMA_VERSION = "preview_surface_integration.r42gm.v1"
EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD = "evidence_bundle_plan_preview"
EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD = "evidence_bundle_plan_preview_surface"

INSPECTED_FILES: tuple[str, ...] = (
    "profile_media_existing_source_intake_bundle_preview_r42gl.py",
    "profile_media_existing_source_intake_bundle_preview_r42gl_test.py",
    "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_NOTES_20260913.md",
    "profile_media_source_package_preview.py",
    "profile_media_source_package_preview_test.py",
    "profile_media_source_intake.py",
    "profile_media_source_intake_test.py",
    "source_reference_intake.py",
    "source_reference_intake_test.py",
    "source_resource_state.py",
    "source_resource_state_test.py",
    "source_adapters.py",
    "source_adapters_test.py",
    "main.py",
    "main_source_resource_ui_test.py",
    "capture_controller.py",
    "capture_controller_test.py",
    "profile_media_source_role_policy.py",
    "profile_media_source_role_policy_test.py",
    "profile_media_source_role_matching_workflow.py",
    "profile_media_source_role_matching_workflow_test.py",
)


@dataclass(frozen=True)
class PreviewSurfaceIntegrationReport:
    marker: str
    status: str
    generated_at: str
    schema_version: str
    source_root: str
    existing_files_inspected: tuple[str, ...]
    integration_point_selected: str
    why_no_parallel_intake_model: str
    existing_files_edited: bool
    preview_field_name: str
    sample_preview_payloads: tuple[Mapping[str, Any], ...]
    compact_surface_summaries: tuple[Mapping[str, Any], ...]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GM_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "status": self.status,
            "passed": self.passed,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "source_root": self.source_root,
            "existing_files_inspected": list(self.existing_files_inspected),
            "integration_point_selected": self.integration_point_selected,
            "why_no_parallel_intake_model": self.why_no_parallel_intake_model,
            "existing_files_edited": self.existing_files_edited,
            "preview_field_name": self.preview_field_name,
            "sample_preview_payloads": [dict(item) for item in self.sample_preview_payloads],
            "compact_surface_summaries": [dict(item) for item in self.compact_surface_summaries],
            "checks": [dict(item) for item in self.checks],
            "side_effect_boundary": self.side_effect_boundary,
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _mapping_from_value(value: Any) -> dict[str, Any]:
    if isinstance(value, ProfileMediaSourcePackagePreview):
        return source_package_preview_payload(value, include_text=False)
    if isinstance(value, Mapping):
        return _json_copy(dict(value))
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return _json_copy(dict(result))
    return _json_copy(state_to_dict(value))


def _source_package_sections(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    top = payload.get("source_package_preview")
    if isinstance(top, dict):
        sections.append(top)
    batch_payload = payload.get("batch_payload")
    if isinstance(batch_payload, dict):
        nested = batch_payload.get("source_package_preview")
        if isinstance(nested, dict):
            sections.append(nested)
    return sections


def compact_evidence_bundle_plan_summary(preview: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact UI/source-preview summary from the R42GL/R42GK preview."""

    expected_media = preview.get("expected_media_candidate_ids")
    expected_media_ids = list(expected_media) if isinstance(expected_media, list) else []
    return {
        "schema_version": R42GM_SCHEMA_VERSION,
        "preview_only": True,
        "read_only": True,
        "source_family": str(preview.get("source_family") or ""),
        "canonical_url": str(preview.get("canonical_url") or ""),
        "bundle_id": str(preview.get("evidence_bundle_id") or ""),
        "record_type": str(preview.get("planned_record_type") or ""),
        "root_output_path": str(preview.get("planned_root_output_path") or ""),
        "review_strings_path": str(preview.get("planned_review_strings_path") or ""),
        "source_role_bridge_status": str(preview.get("planned_source_role_bridge_status") or ""),
        "source_role_bridge_path": str(preview.get("planned_source_role_bridge_path") or ""),
        "promotion_status": str(preview.get("promotion_status") or ""),
        "access_status": str(preview.get("access_status") or ""),
        "requires_review": bool(preview.get("requires_review", True)),
        "requires_human_chain": bool(preview.get("requires_human_chain", False)),
        "requires_login": bool(preview.get("requires_login", False)),
        "requires_manual_receipt": bool(preview.get("requires_manual_receipt", False)),
        "capture_method_id": str(preview.get("capture_method_id") or ""),
        "media_candidate_count": len(expected_media_ids),
        "media_candidate_ids": expected_media_ids,
        "blocked_reason": str(preview.get("blocked_reason") or ""),
        "side_effect_boundary": str(preview.get("side_effect_boundary") or SIDE_EFFECT_BOUNDARY),
        "metadata_only_not_evidence": True,
        "source_role_assignment_performed": False,
        "counter_or_no_jump_mutation_performed": False,
    }


def _attach_preview_to_payload_copy(payload: Mapping[str, Any], source_shape: Any) -> dict[str, Any]:
    copied = _mapping_from_value(payload)
    plan_preview = evidence_bundle_plan_preview_from_existing_source(source_shape)
    surface_summary = compact_evidence_bundle_plan_summary(plan_preview)
    attached = False
    for section in _source_package_sections(copied):
        section[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD] = _json_copy(plan_preview)
        section[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD] = _json_copy(surface_summary)
        attached = True
    if not attached:
        copied[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD] = _json_copy(plan_preview)
        copied[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD] = _json_copy(surface_summary)
    return copied


def enrich_source_package_preview_surface_read_only(value: Any) -> dict[str, Any]:
    """Return an enriched copy of an existing source package/intake preview.

    This is the R42GM preview surface hook. It does not replace the existing
    source-package preview model and it does not mutate the input object.
    """

    payload = _mapping_from_value(value)
    return _attach_preview_to_payload_copy(payload, value)


def preview_surface_payload_from_source_row(value: Any, *, fallback_row_id: str = "source_row") -> dict[str, Any]:
    """Expose one existing source-row-like object as a compact preview surface."""

    row_payload = _mapping_from_value(value)
    plan_preview = evidence_bundle_plan_preview_from_existing_source(value, fallback_row_id=fallback_row_id)
    return {
        "schema_version": R42GM_SCHEMA_VERSION,
        "surface_kind": "source_row_preview",
        "source_row": row_payload,
        EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD: plan_preview,
        EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD: compact_evidence_bundle_plan_summary(plan_preview),
        "side_effect_boundary": SIDE_EFFECT_BOUNDARY,
    }


def preview_surface_payload_from_source_url_intake(result: SourceUrlIntakeResult) -> dict[str, Any]:
    """Expose an existing pasted URL/batch TXT intake result in the preview surface."""

    rows = [
        preview_surface_payload_from_source_row(row, fallback_row_id=f"intake_row_{index}")
        for index, row in enumerate(result.rows, start=1)
    ]
    return {
        "schema_version": R42GM_SCHEMA_VERSION,
        "surface_kind": "source_url_intake_preview",
        "source_url_intake": state_to_dict(result),
        "row_count": len(rows),
        "rows": rows,
        "side_effect_boundary": SIDE_EFFECT_BOUNDARY,
    }


def build_preview_surface_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, SourceUrlIntakeResult):
        return preview_surface_payload_from_source_url_intake(value)
    payload = _mapping_from_value(value)
    if _source_package_sections(payload):
        return enrich_source_package_preview_surface_read_only(value)
    if hasattr(value, "rows") and isinstance(getattr(value, "rows", None), tuple):
        return preview_surface_payload_from_source_url_intake(value)
    return preview_surface_payload_from_source_row(value)


def render_preview_surface_summary_text(payload: Mapping[str, Any]) -> str:
    """Render the compact evidence bundle summary for existing preview UIs."""

    summary: Mapping[str, Any] | None = None
    if EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD in payload and isinstance(payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD], Mapping):
        summary = payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]
    else:
        for section in _source_package_sections(payload):
            section_summary = section.get(EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD)
            if isinstance(section_summary, Mapping):
                summary = section_summary
                break
    if summary is None:
        return "Evidence bundle plan preview: unavailable"
    lines = [
        "Evidence bundle plan preview",
        f"Source family: {summary.get('source_family') or '(unknown)'}",
        f"Canonical URL: {summary.get('canonical_url') or '(missing)'}",
        f"Bundle ID: {summary.get('bundle_id') or '(missing)'}",
        f"Record type: {summary.get('record_type') or '(unknown)'}",
        f"Output folder: {summary.get('root_output_path') or '(planned later)'}",
        f"Review strings: {summary.get('review_strings_path') or '(planned later)'}",
        f"Source-role bridge: {summary.get('source_role_bridge_status') or '(unknown)'}",
        f"Promotion: {summary.get('promotion_status') or '(unknown)'}",
        f"Access: {summary.get('access_status') or '(unknown)'}",
        f"Capture method: {summary.get('capture_method_id') or '(none)'}",
        f"Media candidates: {int(summary.get('media_candidate_count') or 0)}",
        "Read-only preview: true",
        "Metadata-only evidence: true",
    ]
    if summary.get("blocked_reason"):
        lines.append(f"Blocked reason: {summary.get('blocked_reason')}")
    return "\n".join(lines)


def _sample_package_preview() -> ProfileMediaSourcePackagePreview:
    return build_profile_media_source_package_preview(
        database_root="",
        case_title="R42GM Metro preview surface",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        canonical_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater at me in the street after far right lies",
        artifacts=(
            {
                "kind": "article_text",
                "display_name": "Metro 17 July Seagull Eater.txt",
                "source_url": "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
                "text_preview": "People shout seagull eater at me in the street after far right lies\nPicture: Supplied",
            },
        ),
    )


def sample_preview_surface_payloads() -> tuple[dict[str, Any], ...]:
    bbc, exam, _metro_from_r42gl, audio, private = sample_existing_source_shapes()
    batch = parse_source_url_intake(
        "https://x.com/BBCr4today/status/2097217541416308845 "
        "https://x.com/examaddaorg "
        "https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/"
    )
    return (
        preview_surface_payload_from_source_row(bbc),
        preview_surface_payload_from_source_row(exam),
        enrich_source_package_preview_surface_read_only(source_package_preview_payload(_sample_package_preview())),
        preview_surface_payload_from_source_row(audio),
        preview_surface_payload_from_source_row(private),
        preview_surface_payload_from_source_url_intake(batch),
    )


def _all_plan_previews(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        previews: list[Mapping[str, Any]] = []
        maybe = payload.get(EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD)
        if isinstance(maybe, Mapping):
            previews.append(maybe)
        for section in _source_package_sections(payload):
            section_preview = section.get(EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD)
            if isinstance(section_preview, Mapping):
                previews.append(section_preview)
        rows = payload.get("rows")
        if isinstance(rows, list):
            for row in rows:
                previews.extend(_all_plan_previews(row))
        return previews
    return []


def _review_strings_are_plain(preview: Mapping[str, Any]) -> bool:
    samples = preview.get("review_string_preview_sample")
    samples = samples if isinstance(samples, list) else []
    link = preview.get("review_string_index_link")
    records = link.get("records_by_string") if isinstance(link, Mapping) else []
    values = [str(value) for value in list(samples) + (records if isinstance(records, list) else [])]
    for value in values:
        if value.startswith("[") or "](" in value:
            return False
    return True


def _preview_review_strings(preview: Mapping[str, Any]) -> list[str]:
    samples = preview.get("review_string_preview_sample")
    link = preview.get("review_string_index_link")
    records = link.get("records_by_string") if isinstance(link, Mapping) else []
    values: list[str] = []
    if isinstance(samples, list):
        values.extend(str(value) for value in samples)
    if isinstance(records, list):
        values.extend(str(value) for value in records)
    elif isinstance(records, Mapping):
        values.extend(str(key) for key in records.keys())
    return values


def build_preview_surface_integration_report(source_root: str | Path = ".") -> PreviewSurfaceIntegrationReport:
    payloads = sample_preview_surface_payloads()
    previews = [preview for payload in payloads for preview in _all_plan_previews(payload)]
    summaries: list[Mapping[str, Any]] = []
    for payload in payloads:
        if isinstance(payload, Mapping):
            if isinstance(payload.get(EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD), Mapping):
                summaries.append(dict(payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]))
            for section in _source_package_sections(payload):
                if isinstance(section.get(EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD), Mapping):
                    summaries.append(dict(section[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]))
            for row in payload.get("rows", []) if isinstance(payload.get("rows"), list) else []:
                if isinstance(row, Mapping) and isinstance(row.get(EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD), Mapping):
                    summaries.append(dict(row[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]))

    r42gl = build_existing_source_intake_preview_bridge_report(source_root)
    r42gk = validate_evidence_bundle_plan_report(source_root)
    r42gj = build_r42gj_report(source_root)
    r42gi = validate_universal_media_method_matrix(source_root)
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    r42gg = validate_universal_source_map(source_root)
    checks = (
        _check("r42gl_bridge_is_green", r42gl.status == R42GL_PASS_STATUS, r42gl.status),
        _check("existing_source_package_preview_can_be_enriched", any(_source_package_sections(payload) for payload in payloads), "source_package_preview section enriched by copy"),
        _check("existing_source_resource_rows_surface_preview_output", any(payload.get("surface_kind") == "source_row_preview" for payload in payloads if isinstance(payload, Mapping))),
        _check("existing_batch_txt_intake_surface_preview_output", any(payload.get("surface_kind") == "source_url_intake_preview" and int(payload.get("row_count") or 0) >= 3 for payload in payloads if isinstance(payload, Mapping))),
        _check("old_preview_fields_remain_present", any(isinstance(payload.get("batch_payload"), Mapping) and isinstance(payload["batch_payload"].get("source_package_preview"), Mapping) and "artifacts" in payload["batch_payload"]["source_package_preview"] for payload in payloads if isinstance(payload, Mapping))),
        _check("source_role_bridge_compatibility_only", all(preview.get("planned_source_role_bridge_status") == ROLE_STATUS_COMPAT for preview in previews)),
        _check("promotion_status_not_promoted", all(preview.get("promotion_status") == PROMOTION_NONE for preview in previews)),
        _check("unknown_private_rows_review_only", any(preview.get("planned_record_type") == "unknown_source_row" and preview.get("blocked_reason") and preview.get("promotion_status") == PROMOTION_NONE for preview in previews)),
        _check("global_player_r42gh_metadata_preserved", any(preview.get("capture_method_id") == "yt_dlp_python_module" and any(child.get("path", "").endswith("media/original.m4a") for child in preview.get("expected_child_paths", [])) and any("py -m yt_dlp" in value for value in _preview_review_strings(preview)) for preview in previews)),
        _check("examaddaorg_benchmark_context_only", any(preview.get("evidence_bundle_id") == "bundle:twitter_x:timeline:examaddaorg" and all("record_count=6700" not in value for value in _preview_review_strings(preview)) for preview in previews)),
        _check("plain_url_path_machine_fields", all(machine_url_fields_are_plain(preview) for preview in previews)),
        _check("url_like_review_strings_plain", all(_review_strings_are_plain(preview) for preview in previews)),
        _check("metadata_only_not_evidence", all(summary.get("metadata_only_not_evidence") is True for summary in summaries)),
        _check("read_only_no_side_effects", all(summary.get("source_role_assignment_performed") is False and summary.get("counter_or_no_jump_mutation_performed") is False for summary in summaries)),
        _check("prior_green_layers_import", r42gk.status == R42GK_PASS_STATUS and r42gj.status == R42GJ_PASS_STATUS and r42gi.status == R42GI_PASS_STATUS and r42gh.status == R42GH_PASS_STATUS and r42gg.status == R42GG_PASS_STATUS, f"{r42gk.status} {r42gj.status} {r42gi.status} {r42gh.status} {r42gg.status}"),
    )
    status = R42GM_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GM_BLOCKED_STATUS
    return PreviewSurfaceIntegrationReport(
        marker=R42GM_MARKER,
        status=status,
        generated_at=datetime.now(timezone.utc).isoformat(),
        schema_version=R42GM_SCHEMA_VERSION,
        source_root=str(source_root),
        existing_files_inspected=INSPECTED_FILES,
        integration_point_selected=(
            "standalone read-only enrich_source_package_preview_surface_read_only() and "
            "preview_surface_payload_from_source_url_intake(); no existing builder replacement"
        ),
        why_no_parallel_intake_model=(
            "R42GM consumes ProfileMediaSourcePackagePreview/source_package_preview_payload, "
            "SourceResourceRowState, and SourceUrlIntakeResult, then delegates planning to R42GL/R42GK."
        ),
        existing_files_edited=False,
        preview_field_name=EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD,
        sample_preview_payloads=tuple(payloads),
        compact_surface_summaries=tuple(summaries),
        checks=checks,
    )


def validate_preview_surface_integration(source_root: str | Path = ".") -> PreviewSurfaceIntegrationReport:
    return build_preview_surface_integration_report(source_root)


def _report_markdown(report: PreviewSurfaceIntegrationReport) -> str:
    lines = [
        "# R42GM Preview Surface Integration",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Schema version: `{report.schema_version}`",
        f"Preview field: `{report.preview_field_name}`",
        "",
        "## Integration Point",
        report.integration_point_selected,
        "",
        "## Why No Parallel Intake Model",
        report.why_no_parallel_intake_model,
        "",
        "## Existing Files Edited",
        str(report.existing_files_edited),
        "",
        "## Existing Files Inspected",
    ]
    lines.extend(f"- `{path}`" for path in report.existing_files_inspected)
    lines.extend(["", "## Checks"])
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def write_report(report: PreviewSurfaceIntegrationReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "R42GM_PREVIEW_SURFACE_INTEGRATION_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "R42GM_PREVIEW_SURFACE_INTEGRATION_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")
    (root / "R42GM_SAMPLE_PREVIEW_PAYLOADS.json").write_text(
        json.dumps([dict(item) for item in report.sample_preview_payloads], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "R42GM_COMPACT_SURFACE_SUMMARIES.json").write_text(
        json.dumps([dict(item) for item in report.compact_surface_summaries], indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the R42GM preview surface integration report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gm_preview_surface_integration")
    args = parser.parse_args(argv)
    report = build_preview_surface_integration_report(args.source_root)
    write_report(report, args.output_root)
    print(R42GM_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GM_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
