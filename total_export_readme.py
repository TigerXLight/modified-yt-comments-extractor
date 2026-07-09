from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from total_export_assets import (
    export_asset_for_file,
    register_asset_in_manifest_file,
    safe_asset_filename,
)
from total_export_manifest import ASSET_TEXT_EXPORT
from total_export_workflow import TotalExportWorkflowResult


@dataclass(frozen=True)
class TotalExportReadmeFileResult:
    readme_path: str
    registered: bool = False
    manifest_path: str = ""
    asset_path: str = ""
    warnings: tuple[str, ...] = ()


def _format_sequence(values: object) -> str:
    sequence = tuple(values or ())
    if not sequence:
        return "(none)"
    return ", ".join(str(value) for value in sequence)


def build_total_export_readme_text(workflow_result: TotalExportWorkflowResult) -> str:
    plan = workflow_result.plan
    package_result = workflow_result.package_result.package_result
    lines = [
        "Total Export Package",
        "",
        f"Package ID: {package_result.package_id or '(none)'}",
        f"Source URL: {plan.source_url or '(none)'}",
        f"Normalized URL: {plan.normalized_url or '(none)'}",
        f"Plan status: {plan.status}",
        f"Selected capture options: {_format_sequence(plan.selected_capture_options)}",
        "",
        "This package is a local preparation shell. This helper did not fetch comments, live chat, media, screenshots, archive captures, or other network content.",
        "Detailed machine-readable metadata is in the manifest JSON file.",
        "Detailed human-readable review text is expected in TOTAL_EXPORT_SUMMARY.txt when generated.",
        "",
        "Warnings:",
    ]
    if workflow_result.warnings:
        for warning in workflow_result.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def write_total_export_readme_file(
    *,
    workflow_result: TotalExportWorkflowResult,
    filename: str = "README_TOTAL_EXPORT.txt",
    register_in_manifest: bool = True,
) -> TotalExportReadmeFileResult:
    package_result = workflow_result.package_result.package_result
    package_folder = package_result.package_folder
    if not package_folder:
        raise ValueError("Workflow result does not include a package folder.")

    readme_path = Path(package_folder) / safe_asset_filename(filename)
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(build_total_export_readme_text(workflow_result), encoding="utf-8")

    if not register_in_manifest:
        return TotalExportReadmeFileResult(
            readme_path=str(readme_path),
            registered=False,
            manifest_path=workflow_result.package_result.manifest_path,
        )

    asset = export_asset_for_file(
        file_path=str(readme_path),
        asset_type=ASSET_TEXT_EXPORT,
        package_folder=package_folder,
    )
    register_asset_in_manifest_file(
        manifest_path=workflow_result.package_result.manifest_path,
        asset=asset,
        dedupe=True,
    )
    return TotalExportReadmeFileResult(
        readme_path=str(readme_path),
        registered=True,
        manifest_path=workflow_result.package_result.manifest_path,
        asset_path=asset.path,
    )
