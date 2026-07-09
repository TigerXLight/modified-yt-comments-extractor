from __future__ import annotations

import argparse
import json
from typing import Sequence

from asr_provider_metadata import ASRProviderMetadata, available_asr_provider_metadata
from capture_options import CaptureOptionMetadata, available_capture_options
from source_adapters import AVAILABLE_SOURCE_ADAPTERS, SourceAdapter
from source_capture_plan import SourceCapturePlan, build_source_capture_plan
from total_export_inventory import TotalExportPackageInventory, build_total_export_inventory
from total_export_package_inspect import (
    build_total_export_package_inspection_text,
    inspect_total_export_package,
    package_inspection_to_dict,
)
from total_export_package_zip import (
    build_total_export_package_zip_text,
    create_total_export_package_zip,
    package_zip_result_to_dict,
)
from total_export_prepare import PreparedTotalExportResult
from total_export_prepare import prepare_total_export_with_summary
from total_export_review_bundle import (
    build_total_export_review_bundle,
    build_total_export_review_bundle_text,
    review_bundle_result_to_dict,
)
from total_export_zip_inspect import (
    build_total_export_zip_inspection_text,
    inspect_total_export_zip,
    total_export_zip_inspection_to_dict,
)
from total_export_zip_sidecar import (
    build_total_export_zip_sidecar_text,
    write_total_export_zip_sidecars,
    zip_sidecar_result_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a local Total Export package shell with a summary file.",
    )
    parser.add_argument("--base-folder")
    parser.add_argument("--source-url")
    parser.add_argument("--package-folder")
    parser.add_argument("--manifest-path", default="")
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
    parser.add_argument("--write-plan-report", action="store_true")
    parser.add_argument("--plan-report-filename", default="SOURCE_CAPTURE_PLAN.txt")
    parser.add_argument("--no-register-plan-report", action="store_true")
    parser.add_argument("--write-inventory-report", action="store_true")
    parser.add_argument("--inventory-report-filename", default="TOTAL_EXPORT_INVENTORY.txt")
    parser.add_argument("--no-register-inventory-report", action="store_true")
    parser.add_argument("--no-create-asset-folders", action="store_true")
    parser.add_argument("--no-final-validation", action="store_true")
    parser.add_argument("--include-inventory", action="store_true")
    parser.add_argument("--review-files", action="store_true")
    parser.add_argument("--full-review-files", action="store_true")
    parser.add_argument("--list-capture-options", action="store_true")
    parser.add_argument("--list-source-adapters", action="store_true")
    parser.add_argument("--list-asr-providers", action="store_true")
    parser.add_argument("--list-metadata", action="store_true")
    parser.add_argument("--explain-plan", action="store_true")
    parser.add_argument("--inspect-package", action="store_true")
    parser.add_argument("--zip-package", action="store_true")
    parser.add_argument("--zip-path", default="")
    parser.add_argument("--overwrite-zip", action="store_true")
    parser.add_argument("--allow-inspection-warnings", action="store_true")
    parser.add_argument("--inspect-zip", action="store_true")
    parser.add_argument("--include-zip-entries", action="store_true")
    parser.add_argument("--hash-zip-entries", action="store_true")
    parser.add_argument("--write-zip-sidecars", action="store_true")
    parser.add_argument("--zip-sha256-path", default="")
    parser.add_argument("--zip-inspection-json-path", default="")
    parser.add_argument("--overwrite-sidecars", action="store_true")
    parser.add_argument("--allow-non-ok-zip-sidecars", action="store_true")
    parser.add_argument("--build-review-bundle", action="store_true")
    parser.add_argument("--bundle-zip-path", default="")
    parser.add_argument("--overwrite-bundle-zip", action="store_true")
    parser.add_argument("--no-bundle-sidecars", action="store_true")
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


def _source_adapter_to_cli_dict(adapter: SourceAdapter) -> dict[str, object]:
    metadata = adapter.metadata
    capabilities = adapter.capabilities
    return {
        "access_limitations": metadata.access_limitations,
        "capabilities": {
            "supports_author_channel_ids": capabilities.supports_author_channel_ids,
            "supports_comments": capabilities.supports_comments,
            "supports_likes": capabilities.supports_likes,
            "supports_livechat": capabilities.supports_livechat,
            "supports_replies": capabilities.supports_replies,
            "supports_timestamps": capabilities.supports_timestamps,
            "supports_transcripts": capabilities.supports_transcripts,
        },
        "credential_type": metadata.credential_type,
        "credentials_optional": metadata.credentials_optional,
        "credentials_required": metadata.credentials_required,
        "display_name": metadata.display_name,
        "id": adapter.source_name,
        "platform_family": metadata.platform_family,
        "privacy_notes": metadata.privacy_notes,
        "setup_hint": metadata.setup_hint,
        "supports_browser_capture": metadata.supports_browser_capture,
        "supports_manual_import": metadata.supports_manual_import,
        "test_connection_supported": metadata.test_connection_supported,
    }


def source_adapters_to_cli_dict() -> dict[str, object]:
    return {
        "source_adapters": [
            _source_adapter_to_cli_dict(adapter)
            for adapter in AVAILABLE_SOURCE_ADAPTERS
        ]
    }


def print_source_adapters() -> None:
    print("Source adapters:")
    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        metadata = adapter.metadata
        details = [
            metadata.display_name or adapter.source_name,
            f"platform={metadata.platform_family}",
            f"credential={metadata.credential_type}",
        ]
        print(f"- {adapter.source_name}: {'; '.join(details)}")


def _asr_provider_to_cli_dict(provider: ASRProviderMetadata) -> dict[str, object]:
    return {
        "access_limitations": provider.access_limitations,
        "best_known_accuracy_percent": provider.best_known_accuracy_percent,
        "credential_type": provider.credential_type,
        "credentials_required": provider.credentials_required,
        "display_name": provider.display_name,
        "id": provider.provider_id,
        "local_runtime": provider.local_runtime,
        "notes": provider.notes,
        "privacy_notes": provider.privacy_notes,
        "provider_family": provider.provider_family,
        "recommended_role": provider.recommended_role,
        "setup_hint": provider.setup_hint,
        "status": provider.status,
        "test_connection_supported": provider.test_connection_supported,
    }


def asr_providers_to_cli_dict() -> dict[str, object]:
    return {
        "asr_providers": [
            _asr_provider_to_cli_dict(provider)
            for provider in available_asr_provider_metadata()
        ]
    }


def print_asr_providers() -> None:
    print("ASR providers:")
    print("Metadata only; no provider calls or transcription are performed.")
    for provider in available_asr_provider_metadata():
        details = [
            provider.display_name,
            f"status={provider.status}",
            f"credential={provider.credential_type}",
        ]
        if provider.recommended_role:
            details.append(provider.recommended_role)
        print(f"- {provider.provider_id}: {'; '.join(details)}")


def metadata_to_cli_dict() -> dict[str, object]:
    combined = {}
    combined.update(capture_options_to_cli_dict())
    combined.update(source_adapters_to_cli_dict())
    combined.update(asr_providers_to_cli_dict())
    return combined


def print_metadata() -> None:
    print_capture_options()
    print()
    print_source_adapters()
    print()
    print_asr_providers()


def _context_hints_to_cli_list(plan: SourceCapturePlan) -> list[dict[str, object]]:
    if not plan.context_result:
        return []
    return [
        {
            "confidence": hint.confidence,
            "label": hint.label,
            "notes": hint.notes,
            "source": hint.source,
            "value": hint.value,
        }
        for hint in plan.context_result.context_hints
    ]


def _glossary_terms_to_cli_list(plan: SourceCapturePlan) -> list[dict[str, object]]:
    if not plan.context_result:
        return []
    return [
        {
            "aliases": list(term.aliases),
            "case_sensitive": term.case_sensitive,
            "category": term.category,
            "notes": term.notes,
            "source": term.source,
            "text": term.text,
        }
        for term in plan.context_result.glossary_terms
    ]


def explain_plan_to_cli_dict(plan: SourceCapturePlan) -> dict[str, object]:
    context_result = plan.context_result
    context_hints = _context_hints_to_cli_list(plan)
    glossary_terms = _glossary_terms_to_cli_list(plan)
    return {
        "adapter_display_name": plan.adapter_display_name,
        "adapter_name": plan.adapter_name,
        "context_hints": context_hints,
        "duplicate_capture_options": list(plan.duplicate_capture_options),
        "glossary_terms": glossary_terms,
        "normalized_url": plan.normalized_url,
        "plan_status": plan.status,
        "selected_capture_options": list(plan.selected_capture_options),
        "source_id": plan.source_id,
        "source_label": context_result.source_label if context_result else "",
        "source_url": plan.source_url,
        "title": next(
            (
                str(hint.get("value", ""))
                for hint in context_hints
                if hint.get("label") == "title"
            ),
            "",
        ),
        "unknown_capture_options": list(plan.unknown_capture_options),
        "user_terms": [
            term["text"]
            for term in glossary_terms
            if term.get("source") == "user"
        ],
        "warnings": list(plan.warnings),
    }


def print_explain_plan(plan: SourceCapturePlan) -> None:
    context_hints = _context_hints_to_cli_list(plan)
    glossary_terms = _glossary_terms_to_cli_list(plan)
    print("Plan:")
    print(f"Source URL: {plan.source_url or '(none)'}")
    print(f"Normalized URL: {plan.normalized_url or '(none)'}")
    print(f"Plan status: {plan.status}")
    print(f"Source ID: {plan.source_id or '(none)'}")
    print(f"Adapter: {plan.adapter_name or '(none)'}")
    print(f"Adapter display name: {plan.adapter_display_name or '(none)'}")
    print(f"Selected capture options: {', '.join(plan.selected_capture_options) or '(none)'}")
    print(f"Unknown capture options: {', '.join(plan.unknown_capture_options) or '(none)'}")
    print(f"Duplicate capture options: {', '.join(plan.duplicate_capture_options) or '(none)'}")
    print("Warnings:")
    if plan.warnings:
        for warning in plan.warnings:
            print(f"- {warning}")
    else:
        print("- (none)")
    print("Context hints:")
    for hint in context_hints:
        print(f"- {hint['label'] or hint['source']}: {hint['value']}")
    if not context_hints:
        print("- (none)")
    print("User terms:")
    user_terms = [
        term["text"]
        for term in glossary_terms
        if term.get("source") == "user"
    ]
    if user_terms:
        for term in user_terms:
            print(f"- {term}")
    else:
        print("- (none)")


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
        "plan_report_path": (
            result.plan_report_file_result.report_path
            if result.plan_report_file_result
            else ""
        ),
        "inventory_report_path": (
            result.inventory_report_file_result.report_path
            if result.inventory_report_file_result
            else ""
        ),
        "readme_path": result.readme_file_result.readme_path if result.readme_file_result else "",
        "registered_plan_report": bool(
            result.plan_report_file_result
            and result.plan_report_file_result.registered
        ),
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
    list_mode_count = sum(
        bool(value)
        for value in (
            args.list_capture_options,
            args.list_source_adapters,
            args.list_asr_providers,
            args.explain_plan,
            args.inspect_package,
            args.zip_package,
            args.inspect_zip,
            args.write_zip_sidecars,
            args.build_review_bundle,
        )
    )
    if args.list_metadata and list_mode_count:
        parser.error("--list-metadata cannot be combined with other list/explain modes")
    if list_mode_count > 1:
        parser.error("Use only one list/explain mode at a time")

    if args.build_review_bundle:
        if not args.base_folder:
            parser.error("--base-folder is required when --build-review-bundle is used")
        if not args.source_url:
            parser.error("--source-url is required when --build-review-bundle is used")
        if (
            args.write_readme
            or args.write_plan_report
            or args.write_inventory_report
            or args.review_files
            or args.full_review_files
        ):
            parser.error(
                "--build-review-bundle implies full review files and cannot be "
                "combined with manual prepare/write/review flags"
            )
        bundle_result = build_total_export_review_bundle(
            base_folder=args.base_folder,
            source_url=args.source_url,
            source_label=args.source_label,
            title=args.title,
            package_id=args.package_id,
            selected_capture_options=args.capture_option,
            user_terms=args.term,
            create_asset_folders=not args.no_create_asset_folders,
            zip_path=args.bundle_zip_path,
            overwrite_zip=args.overwrite_bundle_zip,
            write_sidecars=not args.no_bundle_sidecars,
            overwrite_sidecars=args.overwrite_sidecars,
            include_zip_entries=args.include_zip_entries,
            hash_zip_entries=args.hash_zip_entries,
        )
        if args.json:
            print(json.dumps(review_bundle_result_to_dict(bundle_result), indent=2, sort_keys=True))
        else:
            print(build_total_export_review_bundle_text(bundle_result))
        return 0

    if args.inspect_package:
        if not args.package_folder:
            parser.error("--package-folder is required when --inspect-package is used")
        if (
            args.write_readme
            or args.write_plan_report
            or args.write_inventory_report
            or args.review_files
            or args.full_review_files
        ):
            parser.error("--inspect-package is read-only and cannot be combined with write/review flags")
        inspection = inspect_total_export_package(
            package_folder=args.package_folder,
            manifest_path=args.manifest_path,
        )
        if args.json:
            print(json.dumps(package_inspection_to_dict(inspection), indent=2, sort_keys=True))
        else:
            print(build_total_export_package_inspection_text(inspection))
        return 0

    if args.zip_package:
        if not args.package_folder:
            parser.error("--package-folder is required when --zip-package is used")
        if (
            args.write_readme
            or args.write_plan_report
            or args.write_inventory_report
            or args.review_files
            or args.full_review_files
        ):
            parser.error(
                "--zip-package packages existing local packages and cannot be "
                "combined with prepare/write/review flags"
            )
        zip_result = create_total_export_package_zip(
            package_folder=args.package_folder,
            manifest_path=args.manifest_path,
            zip_path=args.zip_path,
            overwrite=args.overwrite_zip,
            allow_inspection_warnings=args.allow_inspection_warnings,
        )
        if args.json:
            print(json.dumps(package_zip_result_to_dict(zip_result), indent=2, sort_keys=True))
        else:
            print(build_total_export_package_zip_text(zip_result))
        return 0

    if args.inspect_zip:
        if not args.zip_path:
            parser.error("--zip-path is required when --inspect-zip is used")
        if (
            args.write_readme
            or args.write_plan_report
            or args.write_inventory_report
            or args.review_files
            or args.full_review_files
        ):
            parser.error("--inspect-zip is read-only and cannot be combined with write/review flags")
        zip_inspection = inspect_total_export_zip(
            args.zip_path,
            include_entries=args.include_zip_entries,
            hash_entries=args.hash_zip_entries,
        )
        if args.json:
            print(
                json.dumps(
                    total_export_zip_inspection_to_dict(zip_inspection),
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(build_total_export_zip_inspection_text(zip_inspection))
        return 0

    if args.write_zip_sidecars:
        if not args.zip_path:
            parser.error("--zip-path is required when --write-zip-sidecars is used")
        if (
            args.write_readme
            or args.write_plan_report
            or args.write_inventory_report
            or args.review_files
            or args.full_review_files
        ):
            parser.error(
                "--write-zip-sidecars works on existing local ZIPs and cannot be "
                "combined with prepare/write/review flags"
            )
        sidecar_result = write_total_export_zip_sidecars(
            args.zip_path,
            sha256_path=args.zip_sha256_path,
            json_path=args.zip_inspection_json_path,
            overwrite=args.overwrite_sidecars,
            require_zip_status_ok=not args.allow_non_ok_zip_sidecars,
            include_entries=args.include_zip_entries,
            hash_entries=args.hash_zip_entries,
        )
        if args.json:
            print(json.dumps(zip_sidecar_result_to_dict(sidecar_result), indent=2, sort_keys=True))
        else:
            print(build_total_export_zip_sidecar_text(sidecar_result))
        return 0

    if args.list_metadata:
        if args.json:
            print(json.dumps(metadata_to_cli_dict(), indent=2, sort_keys=True))
        else:
            print_metadata()
        return 0
    if args.list_capture_options:
        if args.json:
            print(json.dumps(capture_options_to_cli_dict(), indent=2, sort_keys=True))
        else:
            print_capture_options()
        return 0
    if args.list_source_adapters:
        if args.json:
            print(json.dumps(source_adapters_to_cli_dict(), indent=2, sort_keys=True))
        else:
            print_source_adapters()
        return 0
    if args.list_asr_providers:
        if args.json:
            print(json.dumps(asr_providers_to_cli_dict(), indent=2, sort_keys=True))
        else:
            print_asr_providers()
        return 0
    if args.explain_plan:
        if not args.source_url:
            parser.error("--source-url is required when --explain-plan is used")
        plan = build_source_capture_plan(
            source_url=args.source_url,
            source_label=args.source_label,
            title=args.title,
            selected_capture_options=args.capture_option,
            user_terms=args.term,
        )
        if args.json:
            print(json.dumps(explain_plan_to_cli_dict(plan), indent=2, sort_keys=True))
        else:
            print_explain_plan(plan)
        return 0

    if not args.base_folder:
        parser.error("--base-folder is required unless a list/explain mode is used")
    if not args.source_url:
        parser.error("--source-url is required unless a list mode is used")

    write_readme = args.write_readme or args.review_files or args.full_review_files
    write_plan_report = args.write_plan_report or args.full_review_files
    write_inventory_report = (
        args.write_inventory_report or args.review_files or args.full_review_files
    )
    include_inventory = args.include_inventory or args.review_files or args.full_review_files
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
        write_plan_report=write_plan_report,
        plan_report_filename=args.plan_report_filename,
        register_plan_report_in_manifest=not args.no_register_plan_report,
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
    if write_plan_report:
        plan_report_result = result.plan_report_file_result
        print(f"Plan report path: {plan_report_result.report_path if plan_report_result else ''}")
        print(
            "Registered plan report: "
            f"{'yes' if plan_report_result and plan_report_result.registered else 'no'}"
        )
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
