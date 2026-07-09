from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from source_capture_plan import SourceCapturePlan
from total_export_assets import (
    asset_destination_path,
    export_asset_for_file,
    register_asset_in_manifest_file,
    safe_asset_filename,
)
from total_export_manifest import ASSET_TEXT_EXPORT
from total_export_manifest import TotalExportManifest
from total_export_validation import ManifestValidationResult
from total_export_workflow import TotalExportWorkflowResult


@dataclass(frozen=True)
class TotalExportSummaryFileResult:
    summary_path: str
    registered: bool = False
    manifest_path: str = ""
    asset_path: str = ""
    warnings: tuple[str, ...] = ()


def _format_sequence(values: object) -> str:
    sequence = tuple(values or ())
    if not sequence:
        return "(none)"
    return ", ".join(str(value) for value in sequence)


def _append_sequence_lines(lines: list[str], label: str, values: object) -> None:
    sequence = tuple(values or ())
    lines.append(f"{label}:")
    if not sequence:
        lines.append("- (none)")
        return
    for value in sequence:
        lines.append(f"- {value}")


def summarize_source_capture_plan(plan: SourceCapturePlan) -> str:
    lines = [
        "Source Capture Plan",
        f"Status: {plan.status}",
        f"Source URL: {plan.source_url or '(none)'}",
        f"Normalized URL: {plan.normalized_url or '(none)'}",
        f"Source ID: {plan.source_id or '(none)'}",
        f"Adapter: {plan.adapter_name or '(none)'}",
        f"Adapter display name: {plan.adapter_display_name or '(none)'}",
        f"Selected capture options: {_format_sequence(plan.selected_capture_options)}",
        f"Unknown capture options: {_format_sequence(plan.unknown_capture_options)}",
        f"Duplicate capture options: {_format_sequence(plan.duplicate_capture_options)}",
    ]
    _append_sequence_lines(lines, "Warnings", plan.warnings)

    context_result = plan.context_result
    if context_result:
        lines.extend(
            [
                "Context",
                f"Source label: {context_result.source_label or '(none)'}",
                f"Source URL: {context_result.source_url or '(none)'}",
            ]
        )
        lines.append("Context hints:")
        if context_result.context_hints:
            for hint in context_result.context_hints:
                hint_label = hint.label or hint.source or "hint"
                lines.append(f"- {hint_label}: {hint.value}")
        else:
            lines.append("- (none)")

        lines.append("Glossary terms:")
        if context_result.glossary_terms:
            for term in context_result.glossary_terms:
                aliases = _format_sequence(term.aliases)
                lines.append(f"- {term.text} [{term.category}; aliases: {aliases}]")
        else:
            lines.append("- (none)")
    else:
        lines.extend(["Context", "- (none)"])

    return "\n".join(lines)


def summarize_manifest_validation(result: ManifestValidationResult) -> str:
    lines = [
        "Manifest Validation",
        f"Manifest path: {result.manifest_path or '(none)'}",
        f"Package folder: {result.package_folder or '(none)'}",
        f"Issue count: {len(result.issues)}",
        f"Errors: {len(result.errors)}",
        f"Warnings: {len(result.warnings)}",
        f"Info: {len([issue for issue in result.issues if issue.level == 'info'])}",
        "Issues:",
    ]
    if not result.issues:
        lines.append("- (none)")
    else:
        for issue in result.issues:
            path = f" [{issue.path}]" if issue.path else ""
            lines.append(f"- {issue.level.upper()} {issue.code}: {issue.message}{path}")
    return "\n".join(lines)


def summarize_total_export_manifest(manifest: TotalExportManifest) -> str:
    lines = [
        "Total Export Manifest",
        f"Package ID: {manifest.package_id or '(none)'}",
        f"Output folder: {manifest.output_folder or '(none)'}",
        f"Asset count: {len(manifest.assets)}",
        f"Provenance count: {len(manifest.provenance_records)}",
        f"Claim note count: {len(manifest.claim_notes)}",
        f"Media source-chain note count: {len(manifest.media_source_chain_notes)}",
        f"Notes: {manifest.notes or '(none)'}",
    ]
    _append_sequence_lines(lines, "Source URLs", manifest.source_urls)
    _append_sequence_lines(lines, "Capture options", manifest.capture_options)
    return "\n".join(lines)


def summarize_total_export_workflow(result: TotalExportWorkflowResult) -> str:
    package_result = result.package_result.package_result
    lines = [
        "Total Export Workflow",
        f"Package folder: {package_result.package_folder or '(none)'}",
        f"Manifest path: {result.package_result.manifest_path or '(none)'}",
        f"Plan status: {result.plan.status}",
        "Workflow warnings:",
    ]
    if result.warnings:
        for warning in result.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            summarize_source_capture_plan(result.plan),
            "",
            summarize_manifest_validation(result.validation_result),
        ]
    )
    return "\n".join(lines)


def write_text_summary(text: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def write_workflow_summary_file(
    *,
    workflow_result: TotalExportWorkflowResult,
    filename: str = "TOTAL_EXPORT_SUMMARY.txt",
    register_in_manifest: bool = True,
) -> TotalExportSummaryFileResult:
    package_result = workflow_result.package_result.package_result
    package_folder = package_result.package_folder
    if not package_folder:
        raise ValueError("Workflow result does not include a package folder.")

    safe_filename = safe_asset_filename(filename)
    summary_path = asset_destination_path(
        package_folder=package_folder,
        asset_type=ASSET_TEXT_EXPORT,
        filename=safe_filename,
    )
    write_text_summary(summarize_total_export_workflow(workflow_result), summary_path)

    if not register_in_manifest:
        return TotalExportSummaryFileResult(
            summary_path=summary_path,
            registered=False,
            manifest_path=workflow_result.package_result.manifest_path,
        )

    asset = export_asset_for_file(
        file_path=summary_path,
        asset_type=ASSET_TEXT_EXPORT,
        package_folder=package_folder,
    )
    register_asset_in_manifest_file(
        manifest_path=workflow_result.package_result.manifest_path,
        asset=asset,
    )
    return TotalExportSummaryFileResult(
        summary_path=summary_path,
        registered=True,
        manifest_path=workflow_result.package_result.manifest_path,
        asset_path=asset.path,
    )
