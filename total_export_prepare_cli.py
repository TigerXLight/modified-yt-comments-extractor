from __future__ import annotations

import argparse
import json
from typing import Sequence

from capture_options import CaptureOptionMetadata, available_capture_options
from total_export_inventory import TotalExportPackageInventory, build_total_export_inventory
from total_export_prepare import PreparedTotalExportResult
from total_export_prepare import prepare_total_export_with_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a local Total Export package shell with a summary file.",
    )
    parser.add_argument("--base-folder")
    parser.add_argument("--source-url")
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
    parser.add_argument("--write-inventory-report", action="store_true")
    parser.add_argument("--inventory-report-filename", default="TOTAL_EXPORT_INVENTORY.txt")
    parser.add_argument("--no-register-inventory-report", action="store_true")
    parser.add_argument("--no-create-asset-folders", action="store_true")
    parser.add_argument("--no-final-validation", action="store_true")
    parser.add_argument("--include-inventory", action="store_true")
    parser.add_argument("--review-files", action="store_true")
    parser.add_argument("--list-capture-options", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def _capture_option_to_cli_dict(option: CaptureOptionMetadata) -> dict[str, object]:
    return {
        "access_mode_hint": option.access_mode_hint,
        "default_enabled_for_total_export": option.default_enabled_for_total_export,
        "description": option.description,
        "evidence_oriented": option.evidence_oriented,
        "id": option.option_id,
        "implementation_notes": option.implementation_notes,
        "label": option.display_name,
        "requires_user_confirmation": option.requires_user_confirmation,
        "safety_notes": option.safety_notes,
        "sends_data_to_external_service": option.sends_data_to_external_service,
        "stage": option.stage,
    }


def capture_options_to_cli_dict() -> dict[str, object]:
    return {
        "capture_options": [
            _capture_option_to_cli_dict(option)
            for option in available_capture_options()
        ]
    }


def print_capture_options() -> None:
    print("Capture options:")
    for option in available_capture_options():
        details = [option.display_name]
        if option.stage:
            details.append(f"stage={option.stage}")
        if option.description:
            details.append(option.description)
        print(f"- {option.option_id}: {'; '.join(details)}")


def _final_validation_issue_count(result: PreparedTotalExportResult) -> int:
    if not result.final_validation_result:
        return 0
    return len(result.final_validation_result.issues)


def _final_validation_messages(result: PreparedTotalExportResult, level: str) -> list[str]:
    if not result.final_validation_result:
        return []
    return [
        f"{issue.code}: {issue.message}"
        for issue in result.final_validation_result.issues
        if issue.level == level
    ]


def _inventory_cli_fields(inventory: TotalExportPackageInventory | None) -> dict[str, object]:
    if inventory is None:
        return {
            "inventory_local_file_count": 0,
            "inventory_missing_registered_assets": [],
            "inventory_ran": False,
            "inventory_registered_asset_count": 0,
            "inventory_unregistered_files": [],
        }
    return {
        "inventory_local_file_count": inventory.local_file_count,
        "inventory_missing_registered_assets": list(inventory.missing_registered_assets),
        "inventory_ran": True,
        "inventory_registered_asset_count": inventory.registered_asset_count,
        "inventory_unregistered_files": list(inventory.unregistered_files),
    }


def result_to_cli_dict(
    result: PreparedTotalExportResult,
    inventory: TotalExportPackageInventory | None = None,
) -> dict[str, object]:
    plan = result.workflow_result.plan
    package_result = result.workflow_result.package_result.package_result
    cli_dict = {
        "duplicate_capture_options": list(plan.duplicate_capture_options),
        "final_validation_errors": _final_validation_messages(result, "error"),
        "final_validation_issue_count": _final_validation_issue_count(result),
        "final_validation_ran": result.final_validation_result is not None,
        "final_validation_warnings": _final_validation_messages(result, "warning"),
        "manifest_path": result.workflow_result.package_result.manifest_path,
        "normalized_url": plan.normalized_url,
        "package_folder": package_result.package_folder,
        "plan_status": plan.status,
        "inventory_report_path": (
            result.inventory_report_file_result.report_path
            if result.inventory_report_file_result
            else ""
        ),
        "readme_path": result.readme_file_result.readme_path if result.readme_file_result else "",
        "registered_inventory_report": bool(
            result.inventory_report_file_result
            and result.inventory_report_file_result.registered
        ),
        "registered_readme": bool(result.readme_file_result and result.readme_file_result.registered),
        "registered_summary": result.summary_file_result.registered,
        "selected_capture_options": list(plan.selected_capture_options),
        "source_url": plan.source_url,
        "summary_path": result.summary_file_result.summary_path,
        "unknown_capture_options": list(plan.unknown_capture_options),
        "warnings": list(result.warnings),
    }
    cli_dict.update(_inventory_cli_fields(inventory))
    return cli_dict


def _build_inventory_if_requested(
    result: PreparedTotalExportResult,
    include_inventory: bool,
) -> TotalExportPackageInventory | None:
    if not include_inventory:
        return None
    package_result = result.workflow_result.package_result.package_result
    return build_total_export_inventory(
        package_folder=package_result.package_folder,
        manifest_path=result.workflow_result.package_result.manifest_path,
    )


def _print_inventory(inventory: TotalExportPackageInventory) -> None:
    print("Inventory:")
    print(f"Registered asset count: {inventory.registered_asset_count}")
    print(f"Local file count: {inventory.local_file_count}")
    print("Unregistered files:")
    if inventory.unregistered_files:
        for path in inventory.unregistered_files:
            print(f"- {path}")
    else:
        print("- (none)")
    print("Missing registered assets:")
    if inventory.missing_registered_assets:
        for path in inventory.missing_registered_assets:
            print(f"- {path}")
    else:
        print("- (none)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_capture_options:
        if args.json:
            print(json.dumps(capture_options_to_cli_dict(), indent=2, sort_keys=True))
        else:
            print_capture_options()
        return 0

    if not args.base_folder:
        parser.error("--base-folder is required unless --list-capture-options is used")
    if not args.source_url:
        parser.error("--source-url is required unless --list-capture-options is used")

    write_readme = args.write_readme or args.review_files
    write_inventory_report = args.write_inventory_report or args.review_files
    include_inventory = args.include_inventory or args.review_files
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
        write_readme=write_readme,
        readme_filename=args.readme_filename,
        register_readme_in_manifest=not args.no_register_readme,
        write_inventory_report=write_inventory_report,
        inventory_report_filename=args.inventory_report_filename,
        register_inventory_report_in_manifest=not args.no_register_inventory_report,
        validate_final_manifest=not args.no_final_validation,
    )
    inventory = _build_inventory_if_requested(result, include_inventory)

    if args.json:
        print(json.dumps(result_to_cli_dict(result, inventory), indent=2, sort_keys=True))
        return 0

    package_result = result.workflow_result.package_result.package_result
    print(f"Package folder: {package_result.package_folder}")
    print(f"Manifest path: {result.workflow_result.package_result.manifest_path}")
    print(f"Summary path: {result.summary_file_result.summary_path}")
    print(f"Plan status: {result.workflow_result.plan.status}")
    print(f"Registered summary: {'yes' if result.summary_file_result.registered else 'no'}")
    if write_readme:
        readme_result = result.readme_file_result
        print(f"README path: {readme_result.readme_path if readme_result else ''}")
        print(f"Registered README: {'yes' if readme_result and readme_result.registered else 'no'}")
    if write_inventory_report:
        inventory_report_result = result.inventory_report_file_result
        print(
            "Inventory report path: "
            f"{inventory_report_result.report_path if inventory_report_result else ''}"
        )
        print(
            "Registered inventory report: "
            f"{'yes' if inventory_report_result and inventory_report_result.registered else 'no'}"
        )
    if result.final_validation_result is None:
        print("Final validation: skipped")
    elif not result.final_validation_result.issues:
        print("Final validation: ok")
    else:
        print(f"Final validation: issues={len(result.final_validation_result.issues)}")
    print("Warnings:")
    if result.warnings:
        for warning in result.warnings:
            print(f"- {warning}")
    else:
        print("- (none)")
    if inventory:
        _print_inventory(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
