from __future__ import annotations

import argparse
import json
from typing import Sequence

from total_export_prepare import PreparedTotalExportResult
from total_export_prepare import prepare_total_export_with_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a local Total Export package shell with a summary file.",
    )
    parser.add_argument("--base-folder", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-label", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--package-id", default="")
    parser.add_argument("--capture-option", action="append", default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--summary-filename", default="TOTAL_EXPORT_SUMMARY.txt")
    parser.add_argument("--no-register-summary", action="store_true")
    parser.add_argument("--write-readme", action="store_true")
    parser.add_argument("--readme-filename", default="README_TOTAL_EXPORT.txt")
    parser.add_argument("--no-register-readme", action="store_true")
    parser.add_argument("--no-create-asset-folders", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def result_to_cli_dict(result: PreparedTotalExportResult) -> dict[str, object]:
    plan = result.workflow_result.plan
    package_result = result.workflow_result.package_result.package_result
    return {
        "duplicate_capture_options": list(plan.duplicate_capture_options),
        "manifest_path": result.workflow_result.package_result.manifest_path,
        "normalized_url": plan.normalized_url,
        "package_folder": package_result.package_folder,
        "plan_status": plan.status,
        "readme_path": result.readme_file_result.readme_path if result.readme_file_result else "",
        "registered_readme": bool(result.readme_file_result and result.readme_file_result.registered),
        "registered_summary": result.summary_file_result.registered,
        "selected_capture_options": list(plan.selected_capture_options),
        "source_url": plan.source_url,
        "summary_path": result.summary_file_result.summary_path,
        "unknown_capture_options": list(plan.unknown_capture_options),
        "warnings": list(result.warnings),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = prepare_total_export_with_summary(
        base_folder=args.base_folder,
        source_url=args.source_url,
        source_label=args.source_label,
        title=args.title,
        selected_capture_options=args.capture_option,
        user_terms=args.term,
        package_id=args.package_id,
        create_asset_folders=not args.no_create_asset_folders,
        summary_filename=args.summary_filename,
        register_summary_in_manifest=not args.no_register_summary,
        write_readme=args.write_readme,
        readme_filename=args.readme_filename,
        register_readme_in_manifest=not args.no_register_readme,
    )

    if args.json:
        print(json.dumps(result_to_cli_dict(result), indent=2, sort_keys=True))
        return 0

    package_result = result.workflow_result.package_result.package_result
    print(f"Package folder: {package_result.package_folder}")
    print(f"Manifest path: {result.workflow_result.package_result.manifest_path}")
    print(f"Summary path: {result.summary_file_result.summary_path}")
    print(f"Plan status: {result.workflow_result.plan.status}")
    print(f"Registered summary: {'yes' if result.summary_file_result.registered else 'no'}")
    if args.write_readme:
        readme_result = result.readme_file_result
        print(f"README path: {readme_result.readme_path if readme_result else ''}")
        print(f"Registered README: {'yes' if readme_result and readme_result.registered else 'no'}")
    print("Warnings:")
    if result.warnings:
        for warning in result.warnings:
            print(f"- {warning}")
    else:
        print("- (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
