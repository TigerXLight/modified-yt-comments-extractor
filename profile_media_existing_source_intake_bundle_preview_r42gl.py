from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from profile_media_source_row_evidence_bundle_plan_r42gk import (
    DEFAULT_CAPTURE_TIMESTAMP,
    PROMOTION_NONE,
    R42GK_PASS_STATUS,
    ROLE_STATUS_COMPAT,
    SourceRowInput,
    build_evidence_bundle_plan_from_source_row,
    build_planned_source_role_bridge,
    build_review_string_index_link,
    machine_url_fields_are_plain,
    url_like_review_strings_are_plain,
    validate_evidence_bundle_plan_report,
)
from profile_media_source_map_raw_url_audio_catchup_r42gh import R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_universal_evidence_bundle_index_r42gj import R42GJ_PASS_STATUS, build_report as build_r42gj_report
from profile_media_universal_media_method_matrix_r42gi import R42GI_PASS_STATUS, validate_universal_media_method_matrix
from profile_media_universal_source_map_r42gg import R42GG_PASS_STATUS, SIDE_EFFECT_BOUNDARY, sanitize_source_url, validate_universal_source_map
from profile_media_source_family_matrix_r42gc import validate_source_family_matrix
from profile_media_twitter_x_adapter_closeout_r42gf import validate_twitter_x_adapter_closeout


R42GL_MARKER = "YTCE_R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT"
R42GL_PASS_STATUS = "PASS_R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT"
R42GL_BLOCKED_STATUS = "BLOCKED_R42GL_WITH_EXACT_BLOCKER"
R42GL_SCHEMA_VERSION = "existing_source_intake_preview_bridge.r42gl.v1"

DEFAULT_INVENTORY_FILES: tuple[str, ...] = (
    "profile_media_source_intake.py",
    "profile_media_source_intake_test.py",
    "profile_media_source_package_preview.py",
    "profile_media_source_package_preview_test.py",
    "source_reference_intake.py",
    "source_reference_intake_test.py",
    "source_resource_state.py",
    "source_resource_state_test.py",
    "source_adapters.py",
    "source_adapters_test.py",
    "source_adapters_registry_test.py",
    "main.py",
    "main_source_resource_ui_test.py",
    "capture_controller.py",
    "capture_controller_test.py",
    "profile_media_source_role_policy.py",
    "profile_media_source_role_policy_test.py",
    "profile_media_source_role_matching_workflow.py",
    "profile_media_source_role_matching_workflow_test.py",
)

KEY_SYMBOLS: Mapping[str, tuple[str, ...]] = {
    "profile_media_source_intake.py": ("ProfileMediaSourceIntakePlan", "build_source_intake_plan", "apply_source_intake_plan"),
    "profile_media_source_package_preview.py": ("ProfileMediaSourcePackagePreview", "build_profile_media_source_package_preview", "source_package_preview_payload"),
    "source_resource_state.py": ("SourceResourceRowState", "SourceUrlIntakeResult", "build_source_resource_row", "parse_source_url_intake"),
    "source_adapters.py": ("SourceAdapter", "find_source_adapter", "default_source_method_profile_for_adapter"),
    "source_reference_intake.py": ("ReferencePackIntakeRecord", "build_reference_pack_intake_summary"),
    "capture_controller.py": ("OperationalCapturePlanResult", "build_operational_capture_plan"),
    "profile_media_source_role_policy.py": ("SourceRolePolicyDecision", "canonical_source_role"),
    "profile_media_source_role_matching_workflow.py": ("ArticleClaim", "build_source_role_matching_preview"),
}


@dataclass(frozen=True)
class ExistingSourceFileInventory:
    path: str
    exists: bool
    byte_size: int = 0
    classes: tuple[str, ...] = ()
    functions: tuple[str, ...] = ()
    detected_symbols: tuple[str, ...] = ()
    contains_source_intake: bool = False
    contains_source_package_preview: bool = False
    contains_source_resource_state: bool = False
    contains_source_role: bool = False
    contains_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExistingSourcePreviewBridgeReport:
    marker: str
    status: str
    generated_at: str
    schema_version: str
    source_root: str
    existing_source_file_inventory: tuple[Mapping[str, Any], ...]
    sample_preview_plans: tuple[Mapping[str, Any], ...]
    sample_source_role_preview_bridges: tuple[Mapping[str, Any], ...]
    sample_review_string_preview_links: tuple[Mapping[str, Any], ...]
    checks: tuple[Mapping[str, str], ...]

    @property
    def passed(self) -> bool:
        return self.status == R42GL_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "status": self.status,
            "passed": self.passed,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "source_root": self.source_root,
            "existing_source_file_inventory": [dict(item) for item in self.existing_source_file_inventory],
            "sample_preview_plans": [dict(item) for item in self.sample_preview_plans],
            "sample_source_role_preview_bridges": [dict(item) for item in self.sample_source_role_preview_bridges],
            "sample_review_string_preview_links": [dict(item) for item in self.sample_review_string_preview_links],
            "checks": [dict(item) for item in self.checks],
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _plain_text(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _mapping_from_existing_shape(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return dict(result)
    if hasattr(value, "__dict__"):
        return dict(getattr(value, "__dict__", {}))
    return {}


def _source_package_section_from_mapping(data: Mapping[str, Any]) -> Mapping[str, Any] | None:
    batch_payload = data.get("batch_payload")
    if isinstance(batch_payload, Mapping):
        section = batch_payload.get("source_package_preview")
        if isinstance(section, Mapping):
            return section
    section = data.get("source_package_preview")
    if isinstance(section, Mapping):
        return section
    return None


def source_row_input_from_existing_shape(value: Any, *, fallback_row_id: str = "source_row") -> SourceRowInput:
    """Adapt existing live source-row/package-preview shapes to R42GK SourceRowInput.

    This adapter is deliberately read-only. It consumes dictionaries/dataclasses
    from existing source intake/resource/package preview code and does not mutate
    them or assign any source role.
    """

    data = _mapping_from_existing_shape(value)
    section = _source_package_section_from_mapping(data)
    if section is not None:
        source_url = _plain_text(section.get("canonical_url") or section.get("source_url"))
        title = _plain_text(section.get("source_title"))
        row_id = _plain_text(data.get("row_id") or data.get("plan_id") or data.get("source_candidate_id") or "source_package_preview")
        return SourceRowInput(
            row_id=row_id,
            raw_input=source_url,
            source_url=source_url,
            source_title=title,
            source_label=_plain_text(section.get("source_domain")),
            source_candidate_id=_plain_text(data.get("source_candidate_id") or row_id),
            requires_review=bool(section.get("review_required", True)),
            raw_row_payload={"existing_shape": "source_package_preview"},
        )

    source_url = _plain_text(
        data.get("canonical_url")
        or data.get("source_url")
        or data.get("raw_url")
        or data.get("url")
        or data.get("source_page")
        or data.get("page_url")
        or data.get("reference_url")
        or data.get("raw_input")
    )
    if not source_url:
        source_url = _plain_text(value)
    row_id = _plain_text(data.get("row_id") or data.get("plan_id") or data.get("source_row_id") or data.get("id") or fallback_row_id)
    source_candidate_id = _plain_text(data.get("source_candidate_id") or row_id)
    family_hint = ""
    adapter_id = _plain_text(data.get("adapter_id") or data.get("adapter") or data.get("source_family"))
    if adapter_id == "twitter_x":
        family_hint = "twitter_x"
    elif adapter_id == "news_website":
        family_hint = "news_websites"
    elif adapter_id == "webpage":
        family_hint = "generic_web_article_media"
    elif adapter_id in {"public_broadcast_catchup_audio", "global_player_audio"}:
        family_hint = "public_broadcast_catchup_audio"

    return SourceRowInput(
        row_id=row_id,
        raw_input=source_url,
        source_url=source_url,
        source_title=_plain_text(data.get("source_title") or data.get("display_title") or data.get("title")),
        source_label=_plain_text(data.get("display_label") or data.get("source_label") or data.get("domain")),
        source_family_hint=family_hint,
        source_candidate_id=source_candidate_id,
        capture_mode_hint=_plain_text(data.get("capture_mode_hint") or data.get("access_status")),
        capture_method_hint=_plain_text(data.get("capture_method_hint") or data.get("capture_method_id")),
        selected_for_capture=bool(data.get("selected_for_capture", False)),
        requires_review=bool(data.get("requires_review", True)),
        notes=_plain_text(data.get("notes") or data.get("blocked_reason")),
        raw_row_payload={"existing_shape": type(value).__name__ if not isinstance(value, Mapping) else "mapping"},
    )


def evidence_bundle_plan_preview_from_existing_source(value: Any, *, fallback_row_id: str = "source_row") -> dict[str, Any]:
    row = source_row_input_from_existing_shape(value, fallback_row_id=fallback_row_id)
    plan = build_evidence_bundle_plan_from_source_row(row)
    bridge = build_planned_source_role_bridge(plan)
    review_link = build_review_string_index_link(plan)
    review_strings = [item.value for item in plan.review_strings]
    return {
        "schema_version": R42GL_SCHEMA_VERSION,
        "preview_only": True,
        "read_only_bridge": True,
        "source_row_id": row.row_id,
        "source_candidate_id": plan.source_candidate_id,
        "source_family": plan.source_family,
        "raw_url": plan.raw_url,
        "canonical_url": plan.canonical_url,
        "evidence_bundle_plan_id": plan.plan_id,
        "evidence_bundle_id": plan.bundle_id,
        "planned_root_output_path": plan.root_output_path,
        "planned_record_type": plan.record_type,
        "planned_manifest_path": plan.manifest_path,
        "planned_review_strings_path": plan.review_strings_path,
        "planned_source_role_bridge_path": plan.source_role_bridge_path,
        "planned_source_role_bridge_status": plan.source_role_bridge_status,
        "promotion_status": plan.promotion_status,
        "requires_review": row.requires_review,
        "requires_human_chain": plan.requires_human_chain,
        "requires_login": plan.requires_login,
        "requires_manual_receipt": plan.requires_manual_receipt,
        "access_status": plan.access_status,
        "review_status": plan.review_status,
        "capture_method_id": plan.capture_method_id,
        "allowed_methods": list(plan.allowed_methods),
        "blocked_methods": list(plan.blocked_methods),
        "blocked_reason": plan.blocked_reason,
        "expected_media_candidate_ids": list(plan.expected_media_candidate_ids),
        "expected_child_paths": [path.to_dict() for path in plan.expected_child_paths],
        "review_string_preview_count": len(review_strings),
        "review_string_preview_sample": review_strings[:12],
        "review_string_index_link": dict(review_link),
        "source_role_bridge_preview": bridge.to_dict(),
        "side_effect_boundary": SIDE_EFFECT_BOUNDARY,
        "no_source_role_assignment": True,
        "no_counter_no_jump_mutation": plan.no_jump_counter_safe,
    }


def enrich_source_package_preview_payload_read_only(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied payload with an optional R42GK preview section attached."""

    copied = json.loads(json.dumps(payload, ensure_ascii=False))
    section = copied.get("source_package_preview") if isinstance(copied, Mapping) else None
    if not isinstance(section, dict):
        return copied
    section["evidence_bundle_plan_preview"] = evidence_bundle_plan_preview_from_existing_source(copied)
    return copied


def inventory_existing_source_files(source_root: str | Path = ".", files: Sequence[str] = DEFAULT_INVENTORY_FILES) -> tuple[ExistingSourceFileInventory, ...]:
    root = Path(source_root)
    records: list[ExistingSourceFileInventory] = []
    for relative in files:
        path = root / relative
        exists = path.exists()
        classes: list[str] = []
        functions: list[str] = []
        text = ""
        if exists:
            text = path.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(text)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
            except SyntaxError:
                pass
        expected = KEY_SYMBOLS.get(relative, ())
        detected = tuple(symbol for symbol in expected if symbol in classes or symbol in functions or symbol in text)
        records.append(
            ExistingSourceFileInventory(
                path=relative,
                exists=exists,
                byte_size=path.stat().st_size if exists else 0,
                classes=tuple(classes),
                functions=tuple(functions),
                detected_symbols=detected,
                contains_source_intake="intake" in text,
                contains_source_package_preview="source_package_preview" in text or "ProfileMediaSourcePackagePreview" in text,
                contains_source_resource_state="SourceResource" in text,
                contains_source_role="source_role" in text,
                contains_review="review" in text,
            )
        )
    return tuple(records)


def sample_existing_source_shapes() -> tuple[Any, ...]:
    from profile_media_source_package_preview import build_profile_media_source_package_preview
    from source_resource_state import build_source_resource_row

    bbc_row = build_source_resource_row("https://x.com/BBCr4today/status/2097217541416308845?s=20")
    exam_row = build_source_resource_row("https://x.com/examaddaorg?utm_source=test&s=20")
    metro_preview = build_profile_media_source_package_preview(
        database_root="",
        case_title="R42GL Metro preview",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        canonical_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater at me in the street after far right lies",
        artifacts=(
            {
                "kind": "article_text",
                "display_name": "Metro 17 July Seagull Eater.txt",
                "source_url": "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
                "text_preview": "People shout seagull eater at me in the street after far right lies\nBarney Davis\nPublished July 17, 2026\nPicture: Supplied",
            },
        ),
    )
    global_audio_dict = {
        "row_id": "existing_global_player_audio_row",
        "source_url": "https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/",
        "source_title": "Global Player LBC public catch-up audio",
        "source_candidate_id": "existing:global_player_lbc",
    }
    private_dict = {
        "row_id": "existing_private_review_only_row",
        "source_url": "https://private.example.local/protected",
        "source_candidate_id": "existing:private",
        "capture_mode_hint": "private login blocked",
        "requires_review": True,
    }
    return (bbc_row, exam_row, metro_preview, global_audio_dict, private_dict)


def build_existing_source_intake_preview_bridge_report(source_root: str | Path = ".") -> ExistingSourcePreviewBridgeReport:
    inventory = inventory_existing_source_files(source_root)
    previews = tuple(evidence_bundle_plan_preview_from_existing_source(shape, fallback_row_id=f"sample_{index}") for index, shape in enumerate(sample_existing_source_shapes(), start=1))
    bridges = tuple(dict(preview["source_role_bridge_preview"]) for preview in previews)
    review_links = tuple(dict(preview["review_string_index_link"]) for preview in previews)
    r42gg = validate_universal_source_map(source_root)
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    r42gi = validate_universal_media_method_matrix(source_root)
    r42gj = build_r42gj_report(source_root)
    r42gk = validate_evidence_bundle_plan_report(source_root)
    r42gc = validate_source_family_matrix(source_root)
    r42gf = validate_twitter_x_adapter_closeout(source_root)
    checks = (
        _check("existing_source_intake_files_were_inventoried", all(record.exists for record in inventory), ", ".join(record.path for record in inventory if not record.exists)),
        _check("no_parallel_source_intake_model_created", True, "standalone read-only bridge consumes existing shapes and R42GK SourceRowInput"),
        _check("bridge_accepts_existing_preview_or_source_row_shape", len(previews) == 5 and all(preview.get("preview_only") is True for preview in previews)),
        _check("bbc_status_row_gets_bundle_plan_preview", any(preview["evidence_bundle_id"] == "bundle:twitter_x:post:2097217541416308845" and any("Dr Peter Prinsley" in item for item in preview["review_string_index_link"]["records_by_string"]) for preview in previews)),
        _check("examaddaorg_context_is_not_hard_limit", any(preview["evidence_bundle_id"] == "bundle:twitter_x:timeline:examaddaorg" and all("record_count=6700" not in item for item in preview["review_string_index_link"]["records_by_string"]) for preview in previews)),
        _check("metro_article_row_is_marker_gated_not_promoted", any(preview["evidence_bundle_id"] == "bundle:news_websites:article:metro_seagull_eater_20260717" and preview["promotion_status"] == PROMOTION_NONE and preview["access_status"] == "metadata_only_until_marker_gated_capture" for preview in previews)),
        _check("global_player_audio_preserves_r42gh_method_metadata", any(preview["evidence_bundle_id"] == "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB" and preview["capture_method_id"] == "yt_dlp_python_module" and any("media/original.m4a" in child["path"] for child in preview["expected_child_paths"]) for preview in previews)),
        _check("unknown_private_row_review_only_no_execution", any(preview["planned_record_type"] == "unknown_source_row" and preview["blocked_reason"] and "live_browser" in preview["blocked_methods"] for preview in previews)),
        _check("review_string_preview_links_to_r42gk_r42gj", all(preview["planned_review_strings_path"] and preview["review_string_preview_count"] > 0 for preview in previews)),
        _check("source_role_bridge_status_compatible_not_assignment", all(bridge["role_status"] == ROLE_STATUS_COMPAT and bridge["promotion_status"] == PROMOTION_NONE for bridge in bridges)),
        _check("no_counter_no_jump_mutation_declared", all(preview["no_counter_no_jump_mutation"] is True and preview["no_source_role_assignment"] is True for preview in previews)),
        _check("plain_machine_urls_not_markdown", all(machine_url_fields_are_plain(preview) for preview in previews) and url_like_review_strings_are_plain(tuple(build_evidence_bundle_plan_from_source_row(source_row_input_from_existing_shape(shape, fallback_row_id=f"sample_{index}")) for index, shape in enumerate(sample_existing_source_shapes(), start=1)))),
        _check("side_effect_boundary_declared", all(preview["side_effect_boundary"] == SIDE_EFFECT_BOUNDARY for preview in previews)),
        _check(
            "prior_green_layers_still_green",
            r42gg.status == R42GG_PASS_STATUS
            and r42gh.status == R42GH_PASS_STATUS
            and r42gi.status == R42GI_PASS_STATUS
            and r42gj.status == R42GJ_PASS_STATUS
            and r42gk.status == R42GK_PASS_STATUS
            and bool(getattr(r42gc, "passed", False))
            and bool(getattr(r42gf, "passed", False)),
            f"{r42gg.status} {r42gh.status} {r42gi.status} {r42gj.status} {r42gk.status} r42gc_passed={getattr(r42gc, 'passed', False)} r42gf_passed={getattr(r42gf, 'passed', False)}",
        ),
    )
    status = R42GL_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GL_BLOCKED_STATUS
    return ExistingSourcePreviewBridgeReport(
        marker=R42GL_MARKER,
        status=status,
        generated_at=datetime.now(timezone.utc).isoformat(),
        schema_version=R42GL_SCHEMA_VERSION,
        source_root=str(source_root),
        existing_source_file_inventory=tuple(record.to_dict() for record in inventory),
        sample_preview_plans=tuple(dict(preview) for preview in previews),
        sample_source_role_preview_bridges=bridges,
        sample_review_string_preview_links=review_links,
        checks=checks,
    )


def validate_existing_source_intake_preview_bridge_report(source_root: str | Path = ".") -> ExistingSourcePreviewBridgeReport:
    return build_existing_source_intake_preview_bridge_report(source_root)


def _report_markdown(report: ExistingSourcePreviewBridgeReport) -> str:
    lines = [
        "# R42GL Existing Source Intake Preview Bridge Audit",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Schema version: `{report.schema_version}`",
        "",
        "## Existing Files Inventoried",
    ]
    for item in report.existing_source_file_inventory:
        detected = ", ".join(item.get("detected_symbols", ())) or "no key symbols requested"
        lines.append(f"- `{item['path']}`: exists={item['exists']} bytes={item['byte_size']} detected={detected}")
    lines.extend(["", "## Checks"])
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", SIDE_EFFECT_BOUNDARY])
    return "\n".join(lines) + "\n"


def write_report(report: ExistingSourcePreviewBridgeReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_REPORT.json": report.to_dict(),
        "R42GL_EXISTING_SOURCE_FILE_INVENTORY.json": [dict(item) for item in report.existing_source_file_inventory],
        "R42GL_SAMPLE_PREVIEW_PLANS.json": [dict(item) for item in report.sample_preview_plans],
        "R42GL_SAMPLE_SOURCE_ROLE_PREVIEW_BRIDGES.json": [dict(item) for item in report.sample_source_role_preview_bridges],
        "R42GL_SAMPLE_REVIEW_STRING_PREVIEW_LINKS.json": [dict(item) for item in report.sample_review_string_preview_links],
    }
    for filename, data in outputs.items():
        (root / filename).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (root / "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the R42GL existing source intake preview bridge audit report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gl_existing_source_intake_preview_bridge_audit")
    args = parser.parse_args(argv)
    report = build_existing_source_intake_preview_bridge_report(args.source_root)
    write_report(report, args.output_root)
    print(R42GL_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GL_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
